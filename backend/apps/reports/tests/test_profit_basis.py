"""
Ikki "foyda" — ikki asos, va har biri o'zini aytadi (audit 2026-11-12, F1).

Moliya markazidagi foyda — hisoblash usuli (oy oyligi, amortizatsiya),
Hisobotlardagi "Sof natija" — kassa usuli (davrda kirgan va chiqqan
pul). Ikkalasi to'g'ri, lekin bir xil so'z bilan atalgani uchun egasi
ikki ekranda ikki raqam ko'rib, biri xato deb o'ylardi.
"""

from __future__ import annotations

from datetime import date

import pytest
from django.utils import timezone

from apps.core.tenancy import organization_context
from apps.reports import money, selectors

pytestmark = pytest.mark.django_db


def test_the_pnl_names_its_basis(tenant_a):
    today = timezone.localdate()
    with organization_context(tenant_a.organization.id):
        pnl = money.profit_and_loss(
            organization_id=tenant_a.organization.id, year=today.year, month=today.month
        )
    assert pnl["basis"] == "accrual"


def test_the_period_report_lists_months_without_a_finished_payroll(tenant_a):
    with organization_context(tenant_a.organization.id):
        report = selectors.profit_loss(
            organization_id=tenant_a.organization.id,
            date_from=date(2026, 8, 1),
            date_to=date(2026, 10, 31),
            group_by="month",
        )
    assert report["basis"] == "cash"
    assert report["payroll_missing"] == ["2026-08", "2026-09", "2026-10"]


def test_the_home_profit_card_says_basis_and_estimate(tenant_a):
    rows = tenant_a.client().get("/api/v1/reports/home").json()["data"]["cards"]
    card = next(row for row in rows if row["key"] == "profit")
    assert card["basis"] == "accrual"
    # Yangi tashkilotda oylik hisoblanmagan — taxmin.
    assert card["payroll_estimated"] is True
