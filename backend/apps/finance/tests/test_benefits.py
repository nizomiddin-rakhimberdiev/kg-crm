"""
Imtiyozlar va oilalar (Bosqich 12.2, owner's brief 2026-10-14 §1).

Excel'dagi muammolar: toifa faqat rang bilan belgilanardi, sababi
yozilmasdi; aka-ukalik familiyaga qarab taxmin qilinardi va chegirma bir
xil qo'llanmasdi. Endi:

* imtiyoz — TURI bor yozuv (aka-uka, xodim farzandi, kam ta'minlangan,
  to'liq, boshqa), sababi MAJBURIY, kim kiritgani va sanalari bilan;
* turlarning qiymati — sozlama (filial bo'yicha);
* aka-uka — UMUMIY VASIY orqali (oila), familiya orqali emas, va
  hisoblagich uni o'zi qo'llaydi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from apps.attendance.models_absence import Holiday
from apps.children.models import Child, ChildGuardian, Guardian
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.finance.charges import credit_for_days, plan_month
from apps.finance.models import Discount, TariffPlan
from apps.settings_app.services import set_setting

pytestmark = pytest.mark.django_db

FEE = Decimal("3050000")


@pytest.fixture
def sept(tenant_a: Any) -> Any:
    with organization_context(tenant_a.organization.id):
        Holiday.objects.create(
            organization=tenant_a.organization, holiday_date=date(2026, 9, 1), name="Mustaqillik"
        )
        TariffPlan.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Asosiy", amount=FEE
        )
    return tenant_a


def _child(tenant: Any, first: str, last: str = "Valiyev", **extra: Any) -> Child:
    with organization_context(tenant.organization.id):
        fields: dict[str, Any] = {
            "organization": tenant.organization,
            "branch": tenant.branch,
            "first_name": first,
            "last_name": last,
            "date_of_birth": date(2021, 3, 14),
            "gender": "male",
            "tariff": TariffPlan.objects.get(name="Asosiy"),
            "is_existing_client": True,
            "enrolled_on": date(2025, 9, 1),
        }
        fields.update(extra)
        return Child.objects.create(**fields)


def _parent(tenant: Any, phone: str, *children: Child) -> Guardian:
    with organization_context(tenant.organization.id):
        guardian = Guardian.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Ota",
            last_name="Valiyev",
            phone=phone,
        )
        for child in children:
            ChildGuardian.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                child=child,
                guardian=guardian,
                relation="father",
            )
        return guardian


def _due(tenant: Any, child: Child) -> Decimal:
    with organization_context(tenant.organization.id):
        return plan_month(child, 2026, 9).amount_due


def _benefit(tenant: Any, child: Child, kind: str, **extra: Any) -> Any:
    client = tenant.client()
    payload = {
        "child_id": str(child.id),
        "kind": kind,
        "reason": extra.pop("reason", "Hujjat bor"),
        "valid_from": extra.pop("valid_from", "2026-09-01"),
        **extra,
    }
    return client.post("/api/v1/discounts", payload, format="json")


# --- 5: aka-uka — oila orqali ---


def test_5_two_children_of_one_family_both_pay_2950000(sept: Any):
    ali, vali = _child(sept, "Ali"), _child(sept, "Vali")
    _parent(sept, "+998901111111", ali, vali)
    assert _due(sept, ali) == Decimal("2950000")
    assert _due(sept, vali) == Decimal("2950000")


def test_5b_a_third_child_joins_and_pays_2950000_too(sept: Any):
    ali, vali, soli = _child(sept, "Ali"), _child(sept, "Vali"), _child(sept, "Soli")
    _parent(sept, "+998901111111", ali, vali)
    _parent(sept, "+998902222222", vali, soli)  # ona ham bog'langan — bitta oila
    assert [_due(sept, c) for c in (ali, vali, soli)] == [Decimal("2950000")] * 3


def test_a_shared_surname_is_not_a_family(sept: Any):
    ali, vali = _child(sept, "Ali"), _child(sept, "Vali")
    _parent(sept, "+998901111111", ali)
    _parent(sept, "+998903333333", vali)
    assert _due(sept, ali) == FEE
    assert _due(sept, vali) == FEE


def test_the_first_child_can_pay_in_full_by_setting(sept: Any):
    with organization_context(sept.organization.id):
        set_setting(
            organization=sept.organization,
            key="benefits.sibling_rule",
            value="after_first",
            branch=sept.branch,
        )
    older = _child(sept, "Ali", enrolled_on=date(2024, 9, 1))
    younger = _child(sept, "Vali")
    _parent(sept, "+998901111111", older, younger)
    assert _due(sept, older) == FEE
    assert _due(sept, younger) == Decimal("2950000")


def test_the_sibling_amount_is_a_setting(sept: Any):
    with organization_context(sept.organization.id):
        set_setting(
            organization=sept.organization,
            key="benefits.sibling_amount",
            value=150000,
            branch=sept.branch,
        )
    ali, vali = _child(sept, "Ali"), _child(sept, "Vali")
    _parent(sept, "+998901111111", ali, vali)
    assert _due(sept, ali) == Decimal("2900000")


# --- 8: xodim farzandi va boshqa turlar ---


def test_8_a_staff_child_pays_1525000(sept: Any):
    child = _child(sept, "Ali")
    assert _benefit(sept, child, "staff_child").status_code == 201
    assert _due(sept, child) == Decimal("1525000")


def test_8b_a_staff_childs_three_sick_days_credit_218000(sept: Any):
    child = _child(sept, "Ali")
    _benefit(sept, child, "staff_child")
    with organization_context(sept.organization.id):
        credit, _rate, days = credit_for_days(child=child, on_date=date(2026, 9, 7), days=3)
    assert days == 21
    assert credit == Decimal("218000")


def test_low_income_pays_nothing(sept: Any):
    child = _child(sept, "Ali")
    _benefit(sept, child, "low_income")
    assert _due(sept, child) == Decimal("0")


def test_an_explicit_benefit_wins_over_the_sibling_discount(sept: Any):
    """Xodim farzandi (50%) — aka-uka chegirmasi ustiga qo'shilmaydi."""
    ali, vali = _child(sept, "Ali"), _child(sept, "Vali")
    _parent(sept, "+998901111111", ali, vali)
    _benefit(sept, ali, "staff_child")
    assert _due(sept, ali) == Decimal("1525000")
    assert _due(sept, vali) == Decimal("2950000")


def test_a_custom_benefit_keeps_its_own_value(sept: Any):
    child = _child(sept, "Ali")
    response = _benefit(sept, child, "custom", discount_type="fixed", value="550000")
    assert response.status_code == 201, response.json()
    assert _due(sept, child) == Decimal("2500000")


# --- Yozuv: sabab, kim, tarix ---


def test_a_benefit_needs_a_reason(sept: Any):
    response = _benefit(sept, _child(sept, "Ali"), "low_income", reason="  ")
    assert response.status_code == 400


def test_a_benefit_records_who_entered_it(sept: Any):
    child = _child(sept, "Ali")
    _benefit(sept, child, "low_income", reason="Ma'lumotnoma № 15")
    with organization_context(sept.organization.id):
        row = Discount.objects.get(child=child)
    assert row.kind == "low_income"
    assert row.created_by_id == sept.owner.id
    assert row.reason == "Ma'lumotnoma № 15"


def test_ending_a_benefit_keeps_it_in_history(sept: Any):
    child = _child(sept, "Ali")
    benefit_id = _benefit(sept, child, "low_income", valid_from="2026-08-01").json()["data"]["id"]

    ended = sept.client().post(
        f"/api/v1/discounts/{benefit_id}/end", {"valid_to": "2026-08-31"}, format="json"
    )

    assert ended.status_code == 200, ended.json()
    history = sept.client().get("/api/v1/discounts", {"child": str(child.id)}).json()["data"]
    rows = history["results"] if isinstance(history, dict) else history
    assert [row["valid_to"] for row in rows] == ["2026-08-31"]
    assert _due(sept, child) == FEE


def test_two_benefits_cannot_overlap(sept: Any):
    child = _child(sept, "Ali")
    _benefit(sept, child, "low_income")
    assert _benefit(sept, child, "staff_child").status_code == 422


def test_a_benefit_cannot_be_edited_in_place(sept: Any):
    benefit_id = _benefit(sept, _child(sept, "Ali"), "low_income").json()["data"]["id"]
    response = sept.client().patch(
        f"/api/v1/discounts/{benefit_id}", {"reason": "boshqa"}, format="json"
    )
    assert response.status_code == 405


# --- Hisobot ---


def test_the_benefits_report_sums_what_the_invoices_gave(sept: Any):
    ali, vali, soli = _child(sept, "Ali"), _child(sept, "Vali"), _child(sept, "Soli")
    _parent(sept, "+998901111111", ali, vali)
    _benefit(sept, soli, "staff_child", reason="Oshpaz farzandi")
    with organization_context(sept.organization.id):
        for child in (ali, vali, soli):
            finance.issue_invoice(child=child, period_year=2026, period_month=9)

    report = sept.client().get(
        "/api/v1/reports/benefits", {"from": "2026-09-01", "to": "2026-09-30"}
    )

    assert report.status_code == 200, report.json()
    data = report.json()["data"]
    assert Decimal(data["total"]) == Decimal("1725000")  # 100 000 + 100 000 + 1 525 000
    by_kind = {row["kind"]: Decimal(row["total"]) for row in data["by_kind"]}
    assert by_kind == {"sibling": Decimal("200000"), "staff_child": Decimal("1525000")}
    staff = next(row for row in data["rows"] if row["kind"] == "staff_child")
    assert staff["reason"] == "Oshpaz farzandi"
    assert staff["created_by"] == sept.owner.full_name


@pytest.mark.tenancy
def test_another_tenants_benefit_is_404(sept: Any, tenant_b: Any):
    benefit_id = _benefit(sept, _child(sept, "Ali"), "low_income").json()["data"]["id"]
    stranger = tenant_b.client()
    assert stranger.get(f"/api/v1/discounts/{benefit_id}").status_code == 404
    assert (
        stranger.post(
            f"/api/v1/discounts/{benefit_id}/end", {"valid_to": "2026-09-30"}, format="json"
        ).status_code
        == 404
    )


# --- Oila — bola kartasi uchun ---


def test_the_child_card_shows_the_family(sept: Any):
    ali, vali = _child(sept, "Ali"), _child(sept, "Vali")
    _parent(sept, "+998901111111", ali, vali)
    response = sept.client().get(f"/api/v1/children/{ali.id}/family")
    assert response.status_code == 200
    names = sorted(row["full_name"] for row in response.json()["data"])
    assert names == ["Valiyev Ali", "Valiyev Vali"] or names == ["Ali Valiyev", "Vali Valiyev"]


@pytest.mark.tenancy
def test_another_tenants_family_is_404(sept: Any, tenant_b: Any):
    ali = _child(sept, "Ali")
    assert tenant_b.client().get(f"/api/v1/children/{ali.id}/family").status_code == 404
