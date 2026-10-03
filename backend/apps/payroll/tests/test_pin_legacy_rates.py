"""
D6: eski sukut oylik stavkalarini ochiq qotirish.

Q10 sukutni 0 ga tushirdi. Sozlamaga tegmagan, lekin 12 % bilan oylik
yakunlagan bog'cha keyingi qoralamada ushlanmani jimgina yo'qotardi.
"""

from __future__ import annotations

from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command

from apps.core.tenancy import organization_context

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]


def _finalized_run_with_tax(tenant, *, tax: str = "120000") -> None:
    from apps.hr.models import Employee, Position
    from apps.payroll.models import PayrollItem, PayrollRun

    org, branch = tenant.organization, tenant.branch
    with organization_context(org.id):
        position = Position.objects.create(organization=org, branch=branch, title="Tarbiyachi")
        employee = Employee.objects.create(
            organization=org,
            branch=branch,
            first_name="Dilfuza",
            last_name="Karimova",
            position=position,
            hire_date="2025-01-01",
            base_salary=Decimal("1000000"),
        )
        run = PayrollRun.objects.create(
            organization=org, branch=branch, period_year=2026, period_month=8, status="finalized"
        )
        PayrollItem.objects.create(
            organization=org,
            branch=branch,
            payroll_run=run,
            employee=employee,
            base_amount=Decimal("1000000"),
            gross=Decimal("1000000"),
            net=Decimal("880000"),
            tax_income=Decimal(tax),
        )


def _run(*args: str) -> str:
    out = StringIO()
    call_command("pin_legacy_payroll_rates", *args, stdout=out)
    return out.getvalue()


def _setting(tenant, key: str):
    from apps.settings_app.models import SystemSetting

    with organization_context(tenant.organization.id):
        row = SystemSetting.objects.filter(key=key, branch__isnull=True).first()
        return row.value if row else None


def test_dry_run_reports_and_writes_nothing(tenant_a):
    _finalized_run_with_tax(tenant_a)
    output = _run()
    assert "payroll.income_tax_rate = 12" in output
    assert "[dry-run]" in output
    assert _setting(tenant_a, "payroll.income_tax_rate") is None


def test_apply_pins_only_what_was_actually_withheld(tenant_a, tenant_b):
    _finalized_run_with_tax(tenant_a)
    _run("--apply")
    assert _setting(tenant_a, "payroll.income_tax_rate") == 12
    # Pensiya ushlanmagan — u qotirilmaydi.
    assert _setting(tenant_a, "payroll.pension_rate") is None
    # Oylik yakunlanmagan tenant — tegilmaydi.
    assert _setting(tenant_b, "payroll.income_tax_rate") is None


def test_an_explicit_choice_is_never_overwritten(tenant_a):
    from apps.settings_app.services import set_setting

    _finalized_run_with_tax(tenant_a)
    with organization_context(tenant_a.organization.id):
        set_setting(organization=tenant_a.organization, key="payroll.income_tax_rate", value=0)
    _run("--apply")
    assert _setting(tenant_a, "payroll.income_tax_rate") == 0
