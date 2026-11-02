"""
To'lov — bitta sana, toʻlovchi, aniq usul (Bosqich 12.4, brif §4, testlar 11–12).

Excel'dagi muammolar: bitta katakda ikki sana, xato yillar (2025, 2027,
2029), sanasiz to'lovlar; avans keyingi oyga qo'lda qayta yozilardi va
usul o'zgarib, summa ikki marta sanalardi. Endi:

* kelajakdagi sana rad etiladi; 60 kundan (sozlama) eski sana — faqat
  sabab bilan;
* to'lovchi — bolaning vasiysi, boshqa odam emas;
* Click va Payme — alohida usullar; "oylikdan ushlash" — xodimga
  bog'langan va oylikda ushlanadi, kassaga pul tushmaydi;
* kassir eng eski qarzni chetlab o'tib boshqa oyni tanlasa — sabab yozadi;
* avans keyingi oy fakturasini o'zi yopadi, usul va sana o'zgarmaydi.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

import pytest
from django.utils import timezone

from apps.cash.models import CashMovement
from apps.children.models import Child, ChildGuardian, Guardian
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.finance.models import Invoice, Payment, PaymentAllocation, TariffPlan
from apps.hr.models import Employee

pytestmark = pytest.mark.django_db

URL = "/api/v1/payments"
FEE = Decimal("3050000")


def _child(tenant: Any, first: str = "Ali") -> Child:
    with organization_context(tenant.organization.id):
        tariff, _ = TariffPlan.objects.get_or_create(
            organization=tenant.organization,
            branch=tenant.branch,
            name="Asosiy",
            defaults={"amount": FEE},
        )
        return Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name=first,
            last_name="Valiyev",
            date_of_birth=date(2021, 3, 14),
            gender="male",
            tariff=tariff,
            is_existing_client=True,
            enrolled_on=date(2025, 9, 1),
        )


def _guardian(tenant: Any, child: Child | None, phone: str = "+998901111111") -> Guardian:
    with organization_context(tenant.organization.id):
        guardian = Guardian.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Vali",
            last_name="Valiyev",
            phone=phone,
        )
        if child is not None:
            ChildGuardian.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                child=child,
                guardian=guardian,
                relation="father",
            )
        return guardian


def _at(day: date) -> str:
    return timezone.make_aware(datetime.combine(day, time(10, 0))).isoformat()


def _pay(tenant: Any, child: Child, **extra: Any) -> Any:
    payload = {"child_id": str(child.id), "amount": "1000000", "method": "cash", **extra}
    return tenant.client().post(URL, payload, format="json")


def _invoice(tenant: Any, child: Child, year: int, month: int) -> Invoice:
    with organization_context(tenant.organization.id):
        return finance.issue_invoice(child=child, period_year=year, period_month=month)


# --- 12: sana ---


def test_12_a_payment_dated_2029_is_refused(tenant_a: Any):
    response = _pay(tenant_a, _child(tenant_a), paid_at="2029-09-05T10:00:00+05:00")
    assert response.status_code == 422
    with organization_context(tenant_a.organization.id):
        assert not Payment.objects.exists()


def test_12_tomorrow_is_refused_too(tenant_a: Any):
    tomorrow = timezone.localdate() + timedelta(days=1)
    assert _pay(tenant_a, _child(tenant_a), paid_at=_at(tomorrow)).status_code == 422


def test_an_old_date_needs_a_reason(tenant_a: Any):
    child = _child(tenant_a)
    old = timezone.localdate() - timedelta(days=61)

    assert _pay(tenant_a, child, paid_at=_at(old)).status_code == 422

    response = _pay(
        tenant_a, child, paid_at=_at(old), backdate_reason="Excel'dan koʻchirildi, kvitansiya 41"
    )
    assert response.status_code == 201, response.json()
    assert response.json()["data"]["backdate_reason"].startswith("Excel")


def test_sixty_days_back_needs_no_reason(tenant_a: Any):
    day = timezone.localdate() - timedelta(days=60)
    assert _pay(tenant_a, _child(tenant_a), paid_at=_at(day)).status_code == 201


def test_the_batch_follows_the_same_date_rules(tenant_a: Any):
    child = _child(tenant_a)
    response = tenant_a.client().post(
        f"{URL}/batch",
        {
            "child_id": str(child.id),
            "paid_at": "2027-01-10T10:00:00+05:00",
            "lines": [{"method": "cash", "amount": "100000"}],
        },
        format="json",
    )
    assert response.status_code == 422


# --- To'lovchi vasiy ---


def test_the_payer_is_one_of_the_childs_guardians(tenant_a: Any):
    child = _child(tenant_a)
    father = _guardian(tenant_a, child)

    response = _pay(tenant_a, child, payer_id=str(father.id))

    assert response.status_code == 201, response.json()
    assert response.json()["data"]["payer_name"] == father.full_name


def test_a_stranger_cannot_be_the_payer(tenant_a: Any):
    child = _child(tenant_a)
    stranger = _guardian(tenant_a, _child(tenant_a, "Soli"), phone="+998902222222")
    assert _pay(tenant_a, child, payer_id=str(stranger.id)).status_code == 422


def test_the_balance_lists_who_can_pay(tenant_a: Any):
    child = _child(tenant_a)
    father = _guardian(tenant_a, child)
    data = tenant_a.client().get("/api/v1/ledger/balance", {"child": str(child.id)}).json()["data"]
    assert [row["id"] for row in data["guardians"]] == [str(father.id)]


@pytest.mark.tenancy
def test_another_tenants_guardian_is_not_a_payer(tenant_a: Any, tenant_b: Any):
    child = _child(tenant_a)
    foreign = _guardian(tenant_b, None)
    assert _pay(tenant_a, child, payer_id=str(foreign.id)).status_code == 400


# --- Click va Payme alohida ---


@pytest.mark.parametrize("method", ["click", "payme"])
def test_click_and_payme_are_separate_methods_into_the_bank(tenant_a: Any, method: str):
    child = _child(tenant_a)
    response = _pay(tenant_a, child, method=method)
    assert response.status_code == 201, response.json()
    with organization_context(tenant_a.organization.id):
        movement = CashMovement.objects.select_related("cash_account").get(
            source_id=response.json()["data"]["id"]
        )
    assert movement.cash_account.kind != "cash"


def test_the_old_combined_method_is_not_offered_for_new_payments(tenant_a: Any):
    assert _pay(tenant_a, _child(tenant_a), method="online").status_code == 400


# --- Oylikdan ushlash ---


@pytest.fixture
def staff_parent(tenant_a: Any) -> Employee:
    with organization_context(tenant_a.organization.id):
        return Employee.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Nilufar",
            last_name="Sodiqova",
            hire_date=date(2025, 1, 10),
            base_salary=Decimal("4000000"),
        )


def test_a_payroll_deduction_names_the_employee(tenant_a: Any):
    assert _pay(tenant_a, _child(tenant_a), method="payroll").status_code == 422


def test_a_payroll_deduction_puts_no_money_in_a_pot(tenant_a: Any, staff_parent: Employee):
    response = _pay(tenant_a, _child(tenant_a), method="payroll", employee_id=str(staff_parent.id))
    assert response.status_code == 201, response.json()
    assert response.json()["data"]["employee_name"] == staff_parent.full_name
    with organization_context(tenant_a.organization.id):
        assert not CashMovement.objects.filter(source_id=response.json()["data"]["id"]).exists()


def test_a_payroll_deduction_is_withheld_from_that_months_salary(
    tenant_a: Any, staff_parent: Employee
):
    from apps.payroll import services as payroll

    today = timezone.localdate()
    with organization_context(tenant_a.organization.id):
        run = payroll.create_run(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            period_year=today.year,
            period_month=today.month,
        )
    response = _pay(
        tenant_a,
        _child(tenant_a),
        method="payroll",
        employee_id=str(staff_parent.id),
        amount="1525000",
    )
    assert response.status_code == 201, response.json()

    with organization_context(tenant_a.organization.id):
        item = run.items.get(employee=staff_parent)
        assert item.tuition == Decimal("1525000")
        assert item.net == item.gross - item.tax_income - item.tax_pension - item.deduction - (
            item.advance + item.tuition
        )

        finance.reverse_payment(payment=Payment.objects.get(), reason="Kassir xato kiritdi")
        item.refresh_from_db()
    assert item.tuition == Decimal("0")


def test_a_closed_payroll_month_takes_no_deduction(tenant_a: Any, staff_parent: Employee):
    from apps.payroll import services as payroll

    today = timezone.localdate()
    with organization_context(tenant_a.organization.id):
        run = payroll.create_run(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            period_year=today.year,
            period_month=today.month,
        )
        payroll.finalize_run(run=run)
    response = _pay(tenant_a, _child(tenant_a), method="payroll", employee_id=str(staff_parent.id))
    assert response.status_code == 422


# --- Qo'lda taqsimlash — sabab bilan ---


def _two_open_months(tenant: Any) -> tuple[Child, Invoice, Invoice]:
    child = _child(tenant)
    return child, _invoice(tenant, child, 2026, 8), _invoice(tenant, child, 2026, 9)


def test_skipping_the_oldest_debt_needs_a_reason(tenant_a: Any):
    child, _august, september = _two_open_months(tenant_a)
    response = _pay(tenant_a, child, invoice_id=str(september.id))
    assert response.status_code == 422


def test_with_a_reason_the_chosen_month_is_paid_first(tenant_a: Any):
    child, august, september = _two_open_months(tenant_a)
    response = _pay(
        tenant_a,
        child,
        invoice_id=str(september.id),
        allocation_reason="Ota-ona sentabr uchun deb berdi",
    )
    assert response.status_code == 201, response.json()
    assert response.json()["data"]["allocation_reason"] == "Ota-ona sentabr uchun deb berdi"
    with organization_context(tenant_a.organization.id):
        assert PaymentAllocation.objects.get().invoice_id == september.id
        august.refresh_from_db()
    assert august.amount_paid == 0


def test_choosing_the_oldest_month_is_no_choice_at_all(tenant_a: Any):
    child, august, _september = _two_open_months(tenant_a)
    assert _pay(tenant_a, child, invoice_id=str(august.id)).status_code == 201


def test_the_payment_shows_where_its_money_went(tenant_a: Any):
    child, _august, _september = _two_open_months(tenant_a)
    payment_id = _pay(tenant_a, child, amount="4000000").json()["data"]["id"]
    data = tenant_a.client().get(f"{URL}/{payment_id}").json()["data"]
    assert [(row["period"], Decimal(row["amount"])) for row in data["allocations"]] == [
        ("2026-08", FEE),
        ("2026-09", Decimal("950000")),
    ]


# --- 11: avans keyingi oyni o'zi yopadi ---


def test_11_an_advance_closes_next_months_invoice_once(tenant_a: Any):
    """
    Oldingi oyda perechisleniye bilan to'langan pul — avans. Keyingi oy
    fakturasi chiqarilganda u o'zi yopiladi; usul o'zgarmaydi, pul bitta
    marta (to'langan oyda) bankka tushgan.
    """
    child = _child(tenant_a)
    paid_on = timezone.localdate() - timedelta(days=30)
    response = _pay(tenant_a, child, amount=str(FEE), method="bank_transfer", paid_at=_at(paid_on))
    assert response.status_code == 201, response.json()

    next_month = paid_on.replace(day=1) + timedelta(days=32)
    invoice = _invoice(tenant_a, child, next_month.year, next_month.month)

    with organization_context(tenant_a.organization.id):
        invoice.refresh_from_db()
        payment = Payment.objects.get()
        allocation = PaymentAllocation.objects.get()
        movements = CashMovement.objects.filter(source_id=payment.id)
        assert invoice.status == "paid"
        assert allocation.invoice_id == invoice.id
        assert payment.method == "bank_transfer"
        assert Payment.objects.count() == 1
        assert movements.count() == 1
        assert timezone.localtime(movements.get().occurred_at).date() == paid_on
