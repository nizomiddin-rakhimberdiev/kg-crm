"""
Ekran bazadagi stavkani koʻrsatadi (audit, 2026-10-30).

Auditda: sozlamalarda 12 % / 0,1 % / 12 % koʻrinardi, bazada esa
`payroll.income_tax_rate`, `pension` va `social_tax` = 0. Natijada
oylikda JShDS, INPS va ijtimoiy soliq umuman hisoblanmasdi, bogʻcha
esa ekranga qarab "hisoblanyapti" deb oʻylardi.

Sabab: ekran PRESET qiymatlarini koʻrsatardi. Preset — taklif, bazada
turgan qiymat emas.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from apps.core.tenancy import organization_context
from apps.settings_app import legal
from apps.settings_app.services import get_setting

pytestmark = pytest.mark.django_db


def test_the_list_carries_the_stored_values(tenant_a):
    with organization_context(tenant_a.organization.id):
        data = legal.presets()
    assert "current_values" in data
    # Sukut — 0 (Q10): bogʻcha soliqni ONGLI ravishda yoqadi.
    assert Decimal(str(data["current_values"]["payroll.income_tax_rate"])) == Decimal("0")


def test_applying_a_preset_writes_the_rates(tenant_a):
    with organization_context(tenant_a.organization.id):
        legal.apply_preset(organization=tenant_a.organization, preset="pq403")
        assert Decimal(str(get_setting(key="payroll.income_tax_rate"))) == Decimal("12")
        data = legal.presets()
    assert Decimal(str(data["current_values"]["payroll.income_tax_rate"])) == Decimal("12")


def test_the_payroll_uses_the_stored_rates(tenant_a):
    """Stavka yozilgandan keyin hisoblash uni ishlatadi."""
    from datetime import date

    from apps.hr.models import Employee, Position
    from apps.payroll import services as payroll

    with organization_context(tenant_a.organization.id):
        legal.apply_preset(organization=tenant_a.organization, preset="pq403")
        position = Position.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, title="Tarbiyachi"
        )
        Employee.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            position=position,
            first_name="Feruza",
            last_name="Abdullayeva",
            hire_date=date(2026, 1, 5),
            base_salary=Decimal("1000000"),
            official_salary=Decimal("1000000"),
        )
        run = payroll.create_run(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            period_year=2026,
            period_month=10,
        )
        item = run.items.first()
    assert item is not None
    # 12 % JShDS va 12 % ijtimoiy soliq.
    assert item.tax_income == Decimal("120000.00")
    assert item.tax_social == Decimal("120000.00")
