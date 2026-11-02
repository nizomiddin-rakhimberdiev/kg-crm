"""
Oyligi hisoblanmagan oyda foyda oyliksiz chiqmaydi (audit, 2026-10-30).

Auditda oktabr hisoblashi qoralama edi — va Moliya markazida oktabr
foydasi 137 177 728, marjasi 91,8 % boʻlib koʻrindi: oylik 0 deb
olingan. Raqam notoʻgʻri emas, UMUMAN boshqa savolga javob berardi,
va ekran buni aytmasdi.

Endi yakunlangan hisoblash boʻlmasa, P&L faol xodimlar okladi
boʻyicha TAXMINIY oylikni oladi va javobda `payroll_estimated`
bayrogʻini qaytaradi — ekran va PDF shu bayroqqa qarab banner
koʻrsatadi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.utils import timezone

from apps.core.tenancy import organization_context
from apps.hr.models import Employee, Position
from apps.reports import money

pytestmark = pytest.mark.django_db


@pytest.fixture
def staff(tenant_a) -> Any:
    today = timezone.localdate()
    with organization_context(tenant_a.organization.id):
        position = Position.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, title="Tarbiyachi"
        )
        for index, salary in enumerate((Decimal("3000000"), Decimal("4000000"))):
            Employee.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                position=position,
                first_name=f"Xodim{index}",
                last_name="Testov",
                hire_date=date(today.year, 1, 5),
                base_salary=salary,
            )
        return tenant_a


def test_without_a_finalised_run_the_payroll_is_estimated(staff, tenant_a):
    today = timezone.localdate()
    with organization_context(tenant_a.organization.id):
        result = money.profit_and_loss(
            organization_id=tenant_a.organization.id, year=today.year, month=today.month
        )
    assert result["payroll_estimated"] is True
    assert Decimal(result["payroll"]) == Decimal("7000000.00")


def test_an_employee_hired_later_is_not_counted(staff, tenant_a):
    """Kelasi oyda ishga kiradigan odam bu oyning taxminiga kirmaydi."""
    today = timezone.localdate()
    with organization_context(tenant_a.organization.id):
        position = Position.objects.first()
        Employee.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            position=position,
            first_name="Keyingi",
            last_name="Xodim",
            hire_date=date(today.year, 12, 31),
            base_salary=Decimal("9000000"),
        )
        result = money.profit_and_loss(
            organization_id=tenant_a.organization.id, year=today.year, month=today.month
        )
    if today.month < 12:
        assert Decimal(result["payroll"]) == Decimal("7000000.00")


def test_a_finalised_run_is_used_as_is(staff, tenant_a):
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
        result = money.profit_and_loss(
            organization_id=tenant_a.organization.id, year=today.year, month=today.month
        )
    assert result["payroll_estimated"] is False
