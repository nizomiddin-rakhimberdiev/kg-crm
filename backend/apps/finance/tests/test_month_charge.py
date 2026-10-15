"""
Bitta oylik hisoblagich (Bosqich 12.1, owner's brief 2026-10-14).

Oyning summasi ilgari ikki joyda hisoblanardi (`issue_invoice` va oldindan
koʻrish) va qayta hisob stavkasi hisob-fakturaning `amount_due` sidan
olinardi — oy oʻrtasida kelgan bolada bu qisqartirilgan summa, ya'ni stavka
past chiqardi. Endi hammasi `charges.plan_month()` dan oʻqiydi.

Raqamlar brifning §8 boʻlimidan: 2026-sentabr, 1-sentabr bayram, asosiy
narx 3 050 000.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from apps.attendance.models_absence import Holiday
from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.finance.charges import plan_month
from apps.finance.models import TariffPlan
from apps.settings_app.services import set_setting

pytestmark = pytest.mark.django_db

FEE = Decimal("3050000")


@pytest.fixture
def sept(tenant_a: Any) -> Any:
    """1-sentabr — bayram (Mustaqillik kuni)."""
    with organization_context(tenant_a.organization.id):
        Holiday.objects.create(
            organization=tenant_a.organization,
            holiday_date=date(2026, 9, 1),
            name="Mustaqillik kuni",
        )
    return tenant_a


def _child(tenant: Any, **fields: Any) -> Child:
    with organization_context(tenant.organization.id):
        tariff = TariffPlan.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            name=f"Asosiy {Child.objects.count()}",
            amount=FEE,
        )
        defaults: dict[str, Any] = {
            "organization": tenant.organization,
            "branch": tenant.branch,
            "first_name": "Ali",
            "last_name": "Valiyev",
            "date_of_birth": date(2021, 3, 14),
            "gender": "male",
            "tariff": tariff,
            "is_existing_client": True,
        }
        defaults.update(fields)
        return Child.objects.create(**defaults)


def _plan(tenant: Any, child: Child) -> Any:
    with organization_context(tenant.organization.id):
        return plan_month(child, 2026, 9)


# --- 1–2: ish kunlari va kunlik stavka ---


def test_1_five_day_week_has_21_working_days_and_rate_145238(sept: Any):
    charge = _plan(sept, _child(sept))
    assert charge.working_days == 21
    assert charge.daily_rate == Decimal("145238")
    assert charge.amount_due == FEE


def test_2_six_day_week_has_25_working_days_and_rate_122000(sept: Any):
    with organization_context(sept.organization.id):
        set_setting(
            organization=sept.organization,
            key="attendance.working_weekdays",
            value="1,2,3,4,5,6",
            branch=sept.branch,
        )
    charge = _plan(sept, _child(sept))
    assert charge.working_days == 25
    assert charge.daily_rate == Decimal("122000")


# --- 3–4: kelgan bola va sinov muddati ---


def test_3_arriving_on_the_21st_without_trial_pays_8_days(sept: Any):
    child = _child(sept, is_existing_client=False, enrolled_on=date(2026, 9, 21), skip_trial=True)
    charge = _plan(sept, child)
    assert charge.billable_days == 8
    assert charge.amount_due == Decimal("1162000")
    # Formula qatorda koʻrinadi — "Nega?" shundan oʻqiydi.
    assert any("8" in line.formula and "21" in line.formula for line in charge.lines)


def test_4_trial_makes_the_first_three_days_free(sept: Any):
    child = _child(sept, is_existing_client=False, enrolled_on=date(2026, 9, 21))
    charge = _plan(sept, child)
    assert charge.billable_days == 5
    assert charge.amount_due == Decimal("726000")


def test_4b_a_child_who_leaves_during_the_trial_owes_nothing(sept: Any):
    child = _child(
        sept,
        is_existing_client=False,
        enrolled_on=date(2026, 9, 21),
        enrollment_status="withdrawn",
        status_changed_on=date(2026, 9, 23),
    )
    assert _plan(sept, child).amount_due == Decimal("0")


def test_trial_days_are_a_setting(sept: Any):
    with organization_context(sept.organization.id):
        set_setting(
            organization=sept.organization, key="finance.trial_days", value=0, branch=sept.branch
        )
    child = _child(sept, is_existing_client=False, enrolled_on=date(2026, 9, 21))
    assert _plan(sept, child).amount_due == Decimal("1162000")


# --- Ketgan bola ---


def test_a_child_leaving_mid_month_pays_up_to_the_last_day(sept: Any):
    """15-sentabrdan ketdi — 2..14-sentabr: 9 ish kuni."""
    child = _child(sept, enrollment_status="withdrawn", status_changed_on=date(2026, 9, 15))
    charge = _plan(sept, child)
    assert charge.billable_days == 9
    assert charge.amount_due == Decimal("1307000")


# --- Yaxlitlash ---


def test_rounding_step_is_a_setting(sept: Any):
    with organization_context(sept.organization.id):
        set_setting(
            organization=sept.organization,
            key="finance.rounding_step",
            value=1,
            branch=sept.branch,
        )
    child = _child(sept, is_existing_client=False, enrolled_on=date(2026, 9, 21), skip_trial=True)
    assert _plan(sept, child).amount_due == Decimal("1161905")


# --- 10: bir oylik ariza ---


def test_10_a_paused_month_is_zero_and_the_child_keeps_their_place(sept: Any):
    from apps.children.services import pause_child

    child = _child(sept)
    with organization_context(sept.organization.id):
        pause_child(child=child, year=2026, month=9, reason="1 oylik ariza")
        invoice = finance.issue_invoice(child=child, period_year=2026, period_month=9)
        child.refresh_from_db()

    assert invoice.amount_due == Decimal("0")
    assert child.enrollment_status == "active"
    assert child.balance == Decimal("0")


# --- Bitta manba: faktura, oldindan koʻrish va qayta hisob stavkasi ---


def test_the_invoice_is_exactly_the_plan(sept: Any):
    child = _child(sept, is_existing_client=False, enrolled_on=date(2026, 9, 21), skip_trial=True)
    with organization_context(sept.organization.id):
        invoice = finance.issue_invoice(child=child, period_year=2026, period_month=9)
        lines = sum(line.line_total for line in invoice.lines.all())
    assert invoice.amount_due == Decimal("1162000")
    assert lines == invoice.amount_due


def test_preview_and_issue_agree(sept: Any):
    child = _child(sept, is_existing_client=False, enrolled_on=date(2026, 9, 21), skip_trial=True)
    with organization_context(sept.organization.id):
        preview = finance.preview_monthly_invoices(
            organization=sept.organization, period_year=2026, period_month=9
        )
    row = next(r for r in preview.rows if r.child_id == str(child.id))
    assert row.amount == Decimal("1162000")


def test_the_day_rate_for_a_credit_ignores_a_prorated_invoice(sept: Any):
    """Oy oʻrtasida kelgan bolaning kunlik stavkasi — toʻliq oylikdan, kesilgan fakturadan emas."""
    from apps.attendance.services_absence import daily_rate_for

    child = _child(sept, is_existing_client=False, enrolled_on=date(2026, 9, 21), skip_trial=True)
    with organization_context(sept.organization.id):
        finance.issue_invoice(child=child, period_year=2026, period_month=9)
        rate, days = daily_rate_for(child=child, on_date=date(2026, 9, 22))
    assert days == 21
    assert rate.quantize(Decimal("1")) == Decimal("145238")
