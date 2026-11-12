"""
Avansning ikki chegarasi (audit 2026-11-12, A1–A2).

Kelajak sanali avans kassani hali chiqmagan pul bilan kamaytirardi.
O'chirish esa sababsiz o'tardi va yakunlangan hisoblashga allaqachon
tushgan avansni ham olib tashlardi — hisoblash summasi o'zgarmas
qolib, uning ortidagi avans yo'qolardi.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pytest
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context
from apps.hr.models import Employee
from apps.payroll import services
from apps.payroll.models import EmployeeAdvance

pytestmark = pytest.mark.django_db


@pytest.fixture
def employee(tenant_a: Any) -> Employee:
    tenant_a.fund(kind="all")
    with organization_context(tenant_a.organization.id):
        return Employee.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Nilufar",
            last_name="Sodiqova",
            hire_date=date(2026, 1, 10),
            base_salary=Decimal("3000000"),
        )


def test_advance_cannot_be_dated_in_the_future(tenant_a: Any, employee: Employee):
    tomorrow = timezone.localdate() + timedelta(days=1)
    with organization_context(tenant_a.organization.id):
        with pytest.raises(BusinessRuleViolation, match="kelajakda"):
            services.record_advance(employee=employee, amount=Decimal("100000"), paid_on=tomorrow)
        assert not EmployeeAdvance.objects.exists()


def test_deleting_an_advance_needs_a_reason(tenant_a: Any, employee: Employee):
    with organization_context(tenant_a.organization.id):
        advance = services.record_advance(
            employee=employee, amount=Decimal("100000"), paid_on=date(2026, 9, 10)
        )
    client = tenant_a.client()
    url = f"/api/v1/payroll/advances/{advance.id}"

    assert client.delete(url, {"reason": "xa"}, format="json").status_code == 400
    with organization_context(tenant_a.organization.id):
        assert EmployeeAdvance.objects.filter(pk=advance.id).exists()

    response = client.delete(url, {"reason": "Xato xodimga yozilgan"}, format="json")
    assert response.status_code == 204, response.content
    with organization_context(tenant_a.organization.id):
        log = AuditLog.objects.get(entity_type="employee_advance", action="delete")
    assert log.changes["reason"] == "Xato xodimga yozilgan"


def test_advance_inside_a_finalized_run_cannot_be_deleted(tenant_a: Any, employee: Employee):
    with organization_context(tenant_a.organization.id):
        advance = services.record_advance(
            employee=employee, amount=Decimal("500000"), paid_on=date(2026, 9, 10)
        )
        run = services.create_run(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            period_year=2026,
            period_month=9,
        )
        services.finalize_run(run=run)

        with pytest.raises(BusinessRuleViolation, match="yakunlangan"):
            services.delete_advance(advance=advance, reason="Xato kiritilgan")
        assert EmployeeAdvance.objects.filter(pk=advance.id).exists()


def test_advance_given_after_finalizing_can_still_be_deleted(tenant_a: Any, employee: Employee):
    """Yakunlashdan keyin berilgan avans hisoblashga tushmagan — uni olib tashlash xavfsiz."""
    with organization_context(tenant_a.organization.id):
        run = services.create_run(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            period_year=2026,
            period_month=9,
        )
        services.finalize_run(run=run)
        late = services.record_advance(
            employee=employee, amount=Decimal("300000"), paid_on=date(2026, 9, 25)
        )

        services.delete_advance(advance=late, reason="Ikki marta yozilgan")
        assert not EmployeeAdvance.objects.filter(pk=late.id).exists()
