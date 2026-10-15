"""
Oylik yig'ma va oyni yopish (Bosqich 12.6, brif §6, test 15 va 11).

Excel'da oy yig'masi qo'lda sanalardi va xato chiqardi; "kassa tushumi"
va "oy uchun yig'ilgan" aralashib, avans ikki marta sanalardi. Endi:

* yig'ma o'zi chiqadi: toifalar bo'yicha bolalar va kutilgan summa,
  imtiyozlar, qayta hisoblar turlari bo'yicha, usullar bo'yicha yig'ilgan;
* ikki ko'rinish ajratilgan: pul QAYSI OYDA kelgan va QAYSI OY fakturasini
  yopgan — hech bir summa ikki marta sanalmaydi;
* tenglik o'zi tekshiriladi: hisoblangan − imtiyoz − qayta hisob =
  yig'ilgan + qolgan qarz;
* yopilgan oy o'zgarmaydi — tuzatish keyingi oyga qator bo'lib tushadi.
"""

from __future__ import annotations

import io
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

import pytest
from django.utils import timezone

from apps.attendance.models_absence import Holiday
from apps.children.models import Child
from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.finance.models import Invoice, TariffPlan

pytestmark = pytest.mark.django_db

URL = "/api/v1/reports/monthly-summary"
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


def _child(tenant: Any, first: str, *, tariff: bool = True, **extra: Any) -> Child:
    with organization_context(tenant.organization.id):
        fields: dict[str, Any] = {
            "organization": tenant.organization,
            "branch": tenant.branch,
            "first_name": first,
            "last_name": "Valiyev",
            "date_of_birth": date(2021, 3, 14),
            "gender": "male",
            "tariff": TariffPlan.objects.get(name="Asosiy") if tariff else None,
            "is_existing_client": True,
            "enrolled_on": date(2025, 9, 1),
        }
        fields.update(extra)
        return Child.objects.create(**fields)


def _issue(tenant: Any, child: Child, month: int = 9) -> Invoice:
    with organization_context(tenant.organization.id):
        return finance.issue_invoice(child=child, period_year=2026, period_month=month)


def _pay(tenant: Any, child: Child, amount: str, method: str, day: date) -> None:
    with organization_context(tenant.organization.id):
        finance.record_payment(
            child=child,
            amount=Decimal(amount),
            method=method,
            paid_at=timezone.make_aware(datetime.combine(day, time(10))),
            backdate_reason="Test tarixi",
        )


def _summary(tenant: Any, month: int = 9) -> dict[str, Any]:
    response = tenant.client().get(URL, {"year": 2026, "month": month})
    assert response.status_code == 200, response.json()
    return response.json()["data"]


def _claim(tenant: Any, child: Child, kind: str, start: str, end: str) -> Any:
    response = tenant.client().post(
        "/api/v1/absence-claims",
        {"child_id": str(child.id), "kind": kind, "date_from": start, "date_to": end},
        format="json",
    )
    assert response.status_code == 201, response.json()
    return response


# --- 15: toifalar, kutilgan summa, tenglik ---


def test_15_categories_add_up_to_the_roster_and_the_check_is_green(sept: Any):
    full = _child(sept, "Ali")
    staff = _child(sept, "Vali")
    sept.client().post(
        "/api/v1/discounts",
        {
            "child_id": str(staff.id),
            "kind": "staff_child",
            "reason": "Oshpaz farzandi",
            "valid_from": "2026-09-01",
        },
        format="json",
    )
    _child(sept, "Soli", tariff=False)  # fakturasiz — baribir ro'yxatda
    invoices = [_issue(sept, full), _issue(sept, staff)]
    _pay(sept, full, "3050000", "cash", date(2026, 9, 5))
    _pay(sept, staff, "1000000", "terminal", date(2026, 9, 10))

    data = _summary(sept)

    assert data["roster"] == 3
    assert sum(row["children"] for row in data["categories"]) == data["roster"]
    by_category = {row["category"]: row for row in data["categories"]}
    assert Decimal(by_category["staff_child"]["due"]) == Decimal("1525000")
    assert Decimal(by_category["full"]["due"]) == FEE
    assert by_category["no_invoice"]["children"] == 1
    assert Decimal(data["invoiced"]["amount_due"]) == sum(i.amount_due for i in invoices)
    assert Decimal(data["benefits_total"]) == Decimal("-1525000")
    assert Decimal(data["collected_for_month"]["total"]) == Decimal("4050000")
    assert Decimal(data["outstanding"]) == Decimal("525000")
    assert data["check"]["ok"] is True


def test_recalculations_are_split_by_kind(sept: Any):
    sick = _child(sept, "Ali")
    late = _child(
        sept, "Vali", enrolled_on=date(2026, 9, 21), skip_trial=True, is_existing_client=False
    )
    _claim(sept, sick, "medical", "2026-09-07", "2026-09-08")
    _issue(sept, sick)
    _issue(sept, late)

    data = _summary(sept)

    rows = {row["kind"]: Decimal(row["amount"]) for row in data["recalculations"]}
    assert rows["medical:fixed_per_day"] == Decimal("-75000")
    assert rows["proration"] == Decimal("1162000") - FEE
    assert data["check"]["ok"] is True


# --- 11: kassa tushumi va oy uchun yig'ilgan ---


def test_11_an_advance_counts_once_in_cash_and_once_for_its_month(sept: Any):
    child = _child(sept, "Ali")
    _pay(sept, child, "3050000", "bank_transfer", date(2026, 8, 24))
    _issue(sept, child)

    august, september = _summary(sept, 8), _summary(sept, 9)

    assert Decimal(august["cash_received"]["total"]) == FEE
    assert Decimal(september["cash_received"]["total"]) == 0
    collected = september["collected_for_month"]
    assert Decimal(collected["total"]) == FEE
    assert Decimal(collected["before_month"]) == FEE
    assert {row["method"]: Decimal(row["total"]) for row in collected["by_method"]} == {
        "bank_transfer": FEE
    }
    assert september["check"]["ok"] is True


def test_the_check_turns_red_when_a_number_drifts(sept: Any):
    invoice = _issue(sept, _child(sept, "Ali"))
    with organization_context(sept.organization.id):
        Invoice.objects.filter(pk=invoice.pk).update(amount_due=Decimal("3000000"))
    assert _summary(sept)["check"]["ok"] is False


# --- Oyni yopish ---


def _close(tenant: Any, month: int = 9, client: Any = None) -> Any:
    return (client or tenant.client()).post(
        f"{URL}/close", {"year": 2026, "month": month}, format="json"
    )


def test_a_finished_month_closes_once(sept: Any):
    _issue(sept, _child(sept, "Ali"))
    response = _close(sept)
    assert response.status_code == 201, response.json()
    assert _summary(sept)["closed"]["closed_by"] == sept.owner.full_name
    assert _close(sept).status_code == 422


def test_a_month_that_has_not_ended_cannot_close(sept: Any):
    today = timezone.localdate()
    response = sept.client().post(
        f"{URL}/close", {"year": today.year, "month": today.month}, format="json"
    )
    assert response.status_code == 422


def test_a_red_month_does_not_close(sept: Any):
    invoice = _issue(sept, _child(sept, "Ali"))
    with organization_context(sept.organization.id):
        Invoice.objects.filter(pk=invoice.pk).update(amount_due=Decimal("3000000"))
    assert _close(sept).status_code == 422


def test_only_the_owner_or_director_closes(sept: Any):
    from rest_framework.test import APIClient

    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.models import User

    with organization_context(sept.organization.id):
        user = User.objects.create_user(
            email="kassir@alfa.uz",
            password="Juda-Kuchli-Parol-2026",  # noqa: S106
            full_name="Kassir",
            organization=sept.organization,
            role=sept.role("cashier"),
            branch=sept.branch,
        )
        tokens = issue_token_pair(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert _close(sept, client=client).status_code == 403


def test_a_closed_month_takes_no_new_invoice_and_no_cancellation(sept: Any):
    ali, vali = _child(sept, "Ali"), _child(sept, "Vali")
    invoice = _issue(sept, ali)
    _close(sept)
    with organization_context(sept.organization.id):
        with pytest.raises(BusinessRuleViolation):
            finance.issue_invoice(child=vali, period_year=2026, period_month=9)
        with pytest.raises(BusinessRuleViolation):
            finance.cancel_invoice(invoice=invoice, reason="xato")


def test_a_late_claim_for_a_closed_month_lands_on_the_next_invoice(sept: Any):
    child = _child(sept, "Ali")
    september = _issue(sept, child)
    _close(sept)

    _claim(sept, child, "medical", "2026-09-07", "2026-09-08")
    october = _issue(sept, child, 10)

    with organization_context(sept.organization.id):
        september.refresh_from_db()
        correction = october.lines.get(kind="credit")
    assert september.amount_due == FEE
    assert correction.line_total == Decimal("-75000")
    assert october.amount_due == FEE - Decimal("75000")


def test_a_closed_month_cannot_be_paused(sept: Any):
    child = _child(sept, "Ali")
    _issue(sept, child)
    _close(sept)
    response = sept.client().post(
        f"/api/v1/children/{child.id}/pauses",
        {"month": "2026-09", "reason": "Safar"},
        format="json",
    )
    assert response.status_code == 422


# --- Excel: eski "oylik to'lov jadvali" ko'rinishida ---


def test_the_monthly_table_exports_one_row_per_child(sept: Any):
    from openpyxl import load_workbook

    from apps.reports.models import ReportExport
    from apps.reports.tasks import generate_export

    ali = _child(sept, "Ali")
    _claim(sept, ali, "medical", "2026-09-07", "2026-09-08")
    _issue(sept, ali)
    _pay(sept, ali, "1000000", "cash", date(2026, 9, 5))
    _pay(sept, ali, "500000", "terminal", date(2026, 9, 12))

    response = sept.client().post(
        "/api/v1/reports/monthly/export",
        {"params": {"year": 2026, "month": 9}},
        format="json",
    )
    assert response.status_code == 202, response.json()
    job_id = response.json()["data"]["id"]
    generate_export(job_id, str(sept.organization.id))

    with organization_context(sept.organization.id):
        export = ReportExport.objects.get(pk=job_id)
        content = export.file.read()
    sheet = load_workbook(io.BytesIO(content)).active
    headers = [cell.value for cell in sheet[1]]
    for name in ("Bola", "Guruh", "Narx", "Naqd", "Terminal", "Maʼlumotnoma", "Qoldiq"):
        assert name in headers, headers
    row = dict(zip(headers, [cell.value for cell in sheet[2]], strict=False))
    assert row["Naqd"] == 1000000
    assert row["Terminal"] == 500000
    assert row["Maʼlumotnoma"] == -75000
    assert row["Qoldiq"] == 3050000 - 75000 - 1500000


@pytest.mark.tenancy
def test_another_tenants_month_is_not_visible_or_closed(sept: Any, tenant_b: Any):
    _issue(sept, _child(sept, "Ali"))
    foreign = tenant_b.client().get(URL, {"year": 2026, "month": 9, "branch": str(sept.branch.id)})
    assert foreign.status_code in (200, 404)
    if foreign.status_code == 200:
        assert Decimal(foreign.json()["data"]["invoiced"]["amount_due"]) == 0
    assert _close(tenant_b).status_code in (201, 422)
    assert _summary(sept)["closed"] is None
