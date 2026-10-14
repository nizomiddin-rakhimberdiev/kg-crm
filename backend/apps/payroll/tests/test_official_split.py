"""
Rasmiy va norasmiy oylik (ADR-18).

Bog'chada odatiy hol: bir xodimning bir qismi rasman, bankka, soliq
ushlab qolingan holda ketadi; qolgani naqd. VA bu ikkisi bitta odamda
bo'lishi mumkin — shuning uchun bo'linish xodimda emas, oylik
SATRIDA.

Eng muhim tekshiruv oxirida: mavjud ma'lumot siljimasligi. Rasmiy
qism sukut bo'yicha 0, ya'ni eski hisoblashlar aynan o'sha raqamda
qoladi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.utils import timezone

from apps.cash import selectors as cash_selectors
from apps.cash.models import CashMovement
from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context
from apps.hr.models import Employee
from apps.payroll import services
from apps.payroll.models import PayoutPart, PayrollPayout, PayrollStatus
from apps.settings_app.services import set_setting

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _rates(tenant_a: Any):
    """
    Stavkalarni ATAYLAB o'rnatadi.

    Q10 dan keyin sukut qiymatlar 0 — ya'ni sozlamaga tegmagan bog'cha
    hech narsa ushlab qolmaydi. Bu testlar esa ushlanma MEXANIZMINI
    sinaydi, shuning uchun ular stavkani o'zlari qo'yadi: default
    o'zgarsa test yiqilmasligi kerak, u boshqa narsani tekshiryapti.
    """
    with organization_context(tenant_a.organization.id):
        set_setting(organization=tenant_a.organization, key="payroll.income_tax_rate", value=12)
        set_setting(organization=tenant_a.organization, key="payroll.pension_rate", value=0.1)
    yield


def _employee(tenant: Any, *, base: str, official: str = "0", name: str = "Nilufar") -> Employee:
    # Bogʻchada pul avval tushadi, keyin chiqadi (ADR-29): boʻsh
    # qopdan oylik va avans ataylab toʻxtaydi. Qoʻriqchining oʻzi
    # `apps/cash/tests/test_cash_ledger.py` da sinaladi.
    tenant.fund(kind="all")
    with organization_context(tenant.organization.id):
        return Employee.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name=name,
            last_name="Sodiqova",
            hire_date=date(2026, 1, 10),
            base_salary=Decimal(base),
            official_salary=Decimal(official),
        )


def _run(tenant: Any, month: int = 9):
    return services.create_run(
        organization=tenant.organization,
        branch=tenant.branch,
        period_year=2026,
        period_month=month,
    )


#: `_employee()` har bir qopga qo'yadigan boshlang'ich qoldiq (ADR-29).
#: Tekshiruvlar unga NISBATAN yoziladi — "qancha chiqdi", "qancha qoldi"
#: emas, chunki bo'sh qopdan chiqim endi to'xtaydi.
FUND = Decimal("100000000")


def _balances(tenant: Any) -> dict[str, Decimal]:
    rows = cash_selectors.account_balances(organization_id=tenant.organization.id)
    return {row["kind"]: Decimal(row["balance"]) for row in rows}


def test_withholdings_apply_only_to_the_official_part(tenant_a: Any):
    """
    5 000 000 maosh, shundan 3 000 000 rasmiy.

    Soliq 3 000 000 dan ushlanadi: 12% = 360 000, INPS 0.1% = 3 000.
    Qolgan 2 000 000 naqd — undan hech narsa ushlanmaydi.
    """
    employee = _employee(tenant_a, base="5000000", official="3000000")
    with organization_context(tenant_a.organization.id):
        run = _run(tenant_a)
        item = run.items.get(employee=employee)

    assert item.official_base == Decimal("3000000.00")
    assert item.tax_income == Decimal("360000.00")
    assert item.tax_pension == Decimal("3000.00")
    assert item.official_net == Decimal("2637000.00")
    assert item.cash_net == Decimal("2000000.00")
    assert item.net == Decimal("4637000.00")
    assert item.gross == Decimal("5000000.00")


def test_a_cash_bonus_never_becomes_taxable(tenant_a: Any):
    """Naqd bonus rasmiy qismga qoʻshilmaydi — soliq oʻzgarmaydi."""
    employee = _employee(tenant_a, base="4000000", official="4000000")
    with organization_context(tenant_a.organization.id):
        run = _run(tenant_a)
        item = run.items.get(employee=employee)
        services.update_item(item=item, bonus=Decimal("500000"))
        item.refresh_from_db()

    assert item.tax_income == Decimal("480000.00")  # 4 000 000 dan, bonussiz
    assert item.cash_net == Decimal("500000.00")
    assert item.net == Decimal("4016000.00")


def test_rates_come_from_settings_not_from_code(tenant_a: Any):
    """Stavka qaror bilan oʻzgaradi — reliz talab qilmasligi kerak."""
    employee = _employee(tenant_a, base="1000000", official="1000000")
    with organization_context(tenant_a.organization.id):
        set_setting(organization=tenant_a.organization, key="payroll.income_tax_rate", value=15)
        run = _run(tenant_a)
        item = run.items.get(employee=employee)

    assert item.tax_income == Decimal("150000.00")


def test_the_snapshot_survives_a_later_rate_change(tenant_a: Any):
    """Martda oʻzgargan stavka fevralning payslipini qayta yozmaydi."""
    employee = _employee(tenant_a, base="1000000", official="1000000")
    with organization_context(tenant_a.organization.id):
        run = _run(tenant_a, month=8)
        services.finalize_run(run=run)
        set_setting(organization=tenant_a.organization, key="payroll.income_tax_rate", value=25)

        item = run.items.get(employee=employee)

    assert item.tax_income == Decimal("120000.00")


def test_existing_data_does_not_move(tenant_a: Any):
    """
    `official_salary` sukut 0 — hammasi naqd, ya'ni eski hisoblashning
    yalpi va sof summasi AYNAN o'sha raqamda qoladi.
    """
    employee = _employee(tenant_a, base="3000000")
    with organization_context(tenant_a.organization.id):
        run = _run(tenant_a)
        item = run.items.get(employee=employee)

    assert item.official_base == Decimal("0.00")
    assert item.tax_income == Decimal("0.00")
    assert item.net == item.gross == Decimal("3000000.00")
    assert item.cash_net == Decimal("3000000.00")


def test_an_advance_larger_than_the_cash_part_is_refused(tenant_a: Any):
    """
    Butunlay rasmiy maoshdagi xodimga katta avans — buxgalter qarori.

    Tizim taxmin qilmaydi: rasmiy sof maosh bankka to'liq ketadi, naqd
    qism esa avansni ko'tara olmasa, payslip ma'nosiz raqam berardi.
    """
    employee = _employee(tenant_a, base="2000000", official="2000000")
    with organization_context(tenant_a.organization.id), pytest.raises(BusinessRuleViolation):
        services.record_advance(
            employee=employee, amount=Decimal("500000"), paid_on=date(2026, 9, 15)
        )
        _run(tenant_a)


def test_paying_a_run_moves_money_out_of_the_right_pots(tenant_a: Any):
    """
    Rasmiy qism bank hisobidan, naqd qism kassadan. Soliq esa HECH
    QAYERDAN chiqmaydi — u bankda qolib, davlatga alohida to'lanadi.
    """
    _employee(tenant_a, base="5000000", official="3000000")
    with organization_context(tenant_a.organization.id):
        run = _run(tenant_a)
        services.finalize_run(run=run)
        services.pay_run(run=run)
        run.refresh_from_db()
        balances = _balances(tenant_a)
        payouts = list(PayrollPayout.objects.filter(payroll_run=run).order_by("part"))

    assert run.status == PayrollStatus.PAID
    assert {(p.part, p.amount) for p in payouts} == {
        (PayoutPart.CASH, Decimal("2000000.00")),
        (PayoutPart.OFFICIAL, Decimal("2637000.00")),
    }
    assert balances["bank"] == FUND - Decimal("2637000.00")
    assert balances["cash"] == FUND - Decimal("2000000.00")
    # Ushlab qolingan 363 000 hech qayerdan chiqmadi.
    # Ikki qop toʻldirilgan — naqd va bank (2026-10-14).
    assert sum(balances.values()) == FUND * 2 - Decimal("4637000.00")


def test_reopening_a_paid_run_returns_the_money(tenant_a: Any):
    """
    To'langan hisoblashni ochish — pulni kassaga qaytarish.

    To'lov qatorlari o'chiriladi (ular hujjat), lekin kassa yozuvlari
    qoladi: asl chiqim ham, qarshi kirim ham. Pul izi yo'qolmaydi.
    """
    _employee(tenant_a, base="4000000", official="0")
    with organization_context(tenant_a.organization.id):
        run = _run(tenant_a)
        services.finalize_run(run=run)
        services.pay_run(run=run)
        assert _balances(tenant_a)["cash"] == FUND - Decimal("4000000.00")

        services.reopen_run(run=run, reason="Xato toʻlangan")
        run.refresh_from_db()

        assert run.status == PayrollStatus.DRAFT
        assert PayrollPayout.objects.filter(payroll_run=run).count() == 0
        assert _balances(tenant_a)["cash"] == FUND


def test_a_payout_cannot_exceed_what_was_calculated(tenant_a: Any):
    employee = _employee(tenant_a, base="1000000")
    with organization_context(tenant_a.organization.id):
        run = _run(tenant_a)
        services.finalize_run(run=run)
        item = run.items.get(employee=employee)
        account = cash_selectors.account_balances(organization_id=tenant_a.organization.id)[0]

        with pytest.raises(BusinessRuleViolation):
            services.pay_run(
                run=run,
                payouts=[
                    {
                        "payroll_item_id": item.id,
                        "part": PayoutPart.CASH,
                        "amount": Decimal("9000000"),
                        "cash_account_id": account["id"],
                    }
                ],
                paid_on=timezone.localdate(),
            )


def test_recalculating_picks_up_a_newly_official_employee(tenant_a: Any):
    """
    Buxgalter xodimni oy o'rtasida rasmiylashtirsa, "qayta hisoblash"
    aynan shu o'zgarishni tortib olishi kerak.

    Ilgari tugma bosilardi, raqam esa o'zgarmasdi: `recalculate_run`
    faqat yangi xodim va avansni yangilardi.
    """
    employee = _employee(tenant_a, base="5000000", official="0")
    with organization_context(tenant_a.organization.id):
        run = _run(tenant_a)
        assert run.items.get(employee=employee).official_base == Decimal("0.00")

        employee.official_salary = Decimal("3000000")
        employee.save(update_fields=["official_salary"])
        services.recalculate_run(run)

        item = run.items.get(employee=employee)

    assert item.official_base == Decimal("3000000.00")
    assert item.tax_income == Decimal("360000.00")
    assert item.official_net == Decimal("2637000.00")
    assert item.cash_net == Decimal("2000000.00")


def test_a_paid_run_reaches_the_cash_ledger(tenant_a: Any):
    """
    To'langan oylik kassa jurnalida BO'LISHI shart.

    Yangilanishda aynan shu qolib ketgan edi: to'lov, chiqim va avans
    ko'chirilgan, oylik esa yo'q — natijada kassa qoldig'i to'langan
    oylik summasiga yuqori ko'rinardi (mijozda 118,5 mln).
    `payroll.0005_backfill_payouts` uni tuzatadi; bu test esa YANGI
    to'lovlar uchun o'sha bog'lanishni qotirib qo'yadi.
    """
    _employee(tenant_a, base="4000000")
    with organization_context(tenant_a.organization.id):
        run = _run(tenant_a)
        services.finalize_run(run=run)

        before = cash_selectors.total_balance(organization_id=tenant_a.organization.id)
        services.pay_run(run=run)
        after = cash_selectors.total_balance(organization_id=tenant_a.organization.id)

        moved = list(
            CashMovement.objects.filter(source_type="payroll", organization=tenant_a.organization)
        )

    assert before - after == Decimal("4000000.00")
    assert len(moved) == 1
    assert moved[0].direction == "out"
