"""
Oylik qaysi KUNI toʻlangani (audit, 2026-10-30).

Auditda may–sentabr hisoblashlarining hammasida `paid_at` bitta
qiymat edi — tugma bosilgan vaqt (2026-10-23 17:15). Oqibati ikkita:
30.09 holatida "toʻlanmagan oylik" 309,2 mln koʻrinardi, oktabrda
esa kassa usulida oylik 0 boʻlardi.

Sana maydoni serverda allaqachon bor edi (`paid_on`), ekran uni
yubormasdi. Shuning uchun bu yerda ikkala tomon ham tekshiriladi:
pul chiqimi aynan oʻsha kun bilan yoziladi va hisoblashning oʻz
belgisi ham oʻsha kunni koʻrsatadi.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pytest
from django.utils import timezone

from apps.cash.models import CashMovement, MovementSource
from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context
from apps.hr.models import Employee, Position
from apps.payroll import services as payroll

pytestmark = pytest.mark.django_db


@pytest.fixture
def run(tenant_a) -> Any:
    """Oʻtgan oy uchun yakunlangan hisoblash."""
    today = timezone.localdate()
    period = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    with organization_context(tenant_a.organization.id):
        from apps.cash import services as cash

        cash.ensure_branch_accounts(branch=tenant_a.branch)
        cash.record_operation(
            kind="owner_contribution",
            account=cash.account_for_method(branch=tenant_a.branch, method="cash"),
            amount=Decimal("10000000"),
            occurred_on=period,
            reason="Ishga tushirish uchun",
        )
        position = Position.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, title="Tarbiyachi"
        )
        Employee.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            position=position,
            first_name="Feruza",
            last_name="Abdullayeva",
            hire_date=period,
            base_salary=Decimal("3000000"),
        )
        created = payroll.create_run(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            period_year=period.year,
            period_month=period.month,
        )
        return payroll.finalize_run(run=created)


def test_the_money_moves_on_the_chosen_day(tenant_a, run):
    """Sentabr oyligi 05.10 da toʻlansa — chiqim 05.10 da."""
    today = timezone.localdate()
    chosen = today.replace(day=5) if today.day >= 5 else today

    with organization_context(tenant_a.organization.id):
        payroll.pay_run(run=run, paid_on=chosen, created_by=tenant_a.owner)
        run.refresh_from_db()
        moved = CashMovement.objects.filter(source_type=MovementSource.PAYROLL)
        assert moved.exists()
        for movement in moved:
            assert timezone.localtime(movement.occurred_at).date() == chosen
        # Hisoblashning oʻz belgisi ham oʻsha kun — tugma bosilgan
        # vaqt emas.
        assert timezone.localtime(run.paid_at).date() == chosen


def test_a_future_day_is_refused(tenant_a, run):
    with organization_context(tenant_a.organization.id), pytest.raises(BusinessRuleViolation):
        payroll.pay_run(
            run=run,
            paid_on=timezone.localdate() + timedelta(days=1),
            created_by=tenant_a.owner,
        )


def test_a_day_before_the_period_is_refused(tenant_a, run):
    with organization_context(tenant_a.organization.id):
        before = date(run.period_year, run.period_month, 1) - timedelta(days=1)
        with pytest.raises(BusinessRuleViolation):
            payroll.pay_run(run=run, paid_on=before, created_by=tenant_a.owner)
