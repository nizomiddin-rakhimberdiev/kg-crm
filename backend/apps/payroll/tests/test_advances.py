"""
Avanslar (oy davomida berilgan pul).

Bog'chada odatiy hol: xodim 15-kuni pul oladi, oylik esa oy oxirida
hisoblanadi. Avans bo'lmaganda buni faqat "ushlab qolish" sifatida
kiritish mumkin edi — payslipda esa bu "jarima" kabi ko'rinardi va
"kim, qachon, qancha oldi" degan savol javobsiz qolardi.

Bog'lanish DAVR bo'yicha (avans sanasi), bog'lovchi ustun orqali emas:
shuning uchun qayta hisoblash idempotent.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from apps.core.tenancy import organization_context
from apps.hr.models import Employee
from apps.payroll import services
from apps.payroll.models import PayrollStatus

pytestmark = pytest.mark.django_db


@pytest.fixture
def employee(tenant_a: Any) -> Employee:
    with organization_context(tenant_a.organization.id):
        return Employee.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Nilufar",
            last_name="Sodiqova",
            hire_date=date(2026, 1, 10),
            base_salary=Decimal("3000000"),
        )


def _run(tenant_a: Any, month: int = 9):
    return services.create_run(
        organization=tenant_a.organization,
        branch=tenant_a.branch,
        period_year=2026,
        period_month=month,
    )


def test_advance_is_deducted_from_net(tenant_a: Any, employee: Employee):
    with organization_context(tenant_a.organization.id):
        services.record_advance(
            employee=employee, amount=Decimal("1000000"), paid_on=date(2026, 9, 15)
        )
        run = _run(tenant_a)
        item = run.items.get(employee=employee)

    assert item.advance == Decimal("1000000.00")
    assert item.gross == Decimal("3000000.00")
    assert item.net == Decimal("2000000.00")


def test_advance_after_the_run_lands_after_recalculation(tenant_a: Any, employee: Employee):
    """Hisoblash oy oxirida yaratiladi, avans esa keyinroq berilishi mumkin."""
    with organization_context(tenant_a.organization.id):
        run = _run(tenant_a)
        assert run.items.get(employee=employee).net == Decimal("3000000.00")

        # Avans yozilishi QORALAMANI darhol yangilaydi.
        services.record_advance(
            employee=employee, amount=Decimal("700000"), paid_on=date(2026, 9, 20)
        )
        assert run.items.get(employee=employee).net == Decimal("2300000.00")


def test_recalculation_is_idempotent(tenant_a: Any, employee: Employee):
    with organization_context(tenant_a.organization.id):
        services.record_advance(
            employee=employee, amount=Decimal("500000"), paid_on=date(2026, 9, 5)
        )
        run = _run(tenant_a)
        for _ in range(3):
            services.recalculate_run(run)
        item = run.items.get(employee=employee)

    assert item.advance == Decimal("500000.00")
    assert item.net == Decimal("2500000.00")


def test_recalculation_adds_a_newly_hired_employee(tenant_a: Any, employee: Employee):
    """Oy o'rtasida ishga kirgan xodim — hisoblashni o'chirmasdan qo'shiladi."""
    with organization_context(tenant_a.organization.id):
        run = _run(tenant_a)
        before = run.items.count()
        newcomer = Employee.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Sevara",
            last_name="Karimova",
            hire_date=date(2026, 9, 12),
            base_salary=Decimal("2500000"),
        )
        services.recalculate_run(run)

        assert run.items.count() == before + 1
        assert run.items.filter(employee=newcomer).exists()


def test_advance_from_another_month_is_not_counted(tenant_a: Any, employee: Employee):
    with organization_context(tenant_a.organization.id):
        services.record_advance(
            employee=employee, amount=Decimal("900000"), paid_on=date(2026, 8, 15)
        )
        run = _run(tenant_a, month=9)

        assert run.items.get(employee=employee).advance == Decimal("0.00")


def test_advance_cannot_exceed_gross(tenant_a: Any, employee: Employee):
    from apps.core.exceptions import BusinessRuleViolation

    with organization_context(tenant_a.organization.id):
        _run(tenant_a)
        with pytest.raises(BusinessRuleViolation):
            services.record_advance(
                employee=employee, amount=Decimal("5000000"), paid_on=date(2026, 9, 15)
            )


def test_finalized_run_is_not_touched_by_a_late_advance(tenant_a: Any, employee: Employee):
    """Yakunlangan hisoblash o'zgarmaydi — tuzatish keyingi oyda."""
    with organization_context(tenant_a.organization.id):
        run = _run(tenant_a)
        services.finalize_run(run=run)
        services.record_advance(
            employee=employee, amount=Decimal("400000"), paid_on=date(2026, 9, 25)
        )
        run.refresh_from_db()

        assert run.status == PayrollStatus.FINALIZED
        assert run.items.get(employee=employee).advance == Decimal("0.00")


def test_advance_endpoint_records_and_lists(tenant_a: Any, employee: Employee):
    client = tenant_a.client()
    created = client.post(
        "/api/v1/payroll/advances",
        {"employee_id": str(employee.id), "amount": "250000", "paid_on": "2026-09-10"},
        format="json",
    )
    assert created.status_code == 201, created.content

    listed = client.get("/api/v1/payroll/advances").json()["data"]
    assert [row["amount"] for row in listed] == ["250000.00"]
