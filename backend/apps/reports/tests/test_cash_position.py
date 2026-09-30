"""
Kassa qoldig'i — "ayni paytda qo'limizda qancha pul bor".

Mijozning birinchi savoli va u hech qayerda ko'rinmasdi: tushum ham,
chiqim ham, oylik ham alohida ekranlarda yotardi, ularni qo'shib
ayirishni esa bog'cha egasi o'zi qilardi.

Bu yerdagi eng muhim tekshiruv — AVANS ikki marta sanalmasligi:
yakunlangan davrning avansi sof maoshdan allaqachon ayrilgan.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.utils import timezone

from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.expenses.models import Expense, ExpenseCategory, ExpenseStatus
from apps.finance import services as finance
from apps.hr.models import Employee
from apps.payroll import services as payroll
from apps.reports import selectors

pytestmark = pytest.mark.django_db


def _child(tenant: Any) -> Child:
    with organization_context(tenant.organization.id):
        return Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Kassa",
            last_name="Bolasi",
            date_of_birth=date(2021, 3, 14),
            gender="male",
        )


def _expense(tenant: Any, amount: str, status: str) -> Expense:
    with organization_context(tenant.organization.id):
        category, _ = ExpenseCategory.objects.get_or_create(
            organization=tenant.organization, branch=tenant.branch, name="Kommunal"
        )
        return Expense.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            category=category,
            amount=Decimal(amount),
            expense_date=timezone.localdate(),
            status=status,
        )


def _employee(tenant: Any, salary: str = "4000000") -> Employee:
    with organization_context(tenant.organization.id):
        return Employee.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Xodim",
            last_name="Testov",
            hire_date=date(2026, 1, 10),
            base_salary=Decimal(salary),
        )


def test_balance_is_income_minus_expenses_minus_payroll(tenant_a: Any):
    child = _child(tenant_a)
    _employee(tenant_a)

    with organization_context(tenant_a.organization.id):
        finance.record_payment(child=child, amount=Decimal("10000000"), method="cash")
        run = payroll.create_run(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            period_year=timezone.localdate().year,
            period_month=timezone.localdate().month,
        )
        payroll.finalize_run(run=run)

    _expense(tenant_a, "1500000", ExpenseStatus.APPROVED)
    # Kutilayotgan chiqim hali xarajat emas — hisobotlardagi qoida bilan bir xil.
    _expense(tenant_a, "9000000", ExpenseStatus.PENDING)

    with organization_context(tenant_a.organization.id):
        position = selectors.cash_position(organization_id=tenant_a.organization.id)

    assert position["income"] == "10000000.00"
    assert position["expenses"] == "1500000.00"
    assert position["payroll"] == "4000000.00"
    assert position["balance"] == "4500000.00"


def test_advance_is_not_counted_twice(tenant_a: Any):
    """
    Avans sof maoshdan ayrilgan, ya'ni "net + avans" = yalpi.

    Shuning uchun qoldiq `gross − deductions` dan hisoblanadi; avansni
    ustiga yana qo'shish bog'chani o'zi bermagan pul bilan qarzdor
    qilib ko'rsatardi.
    """
    child = _child(tenant_a)
    employee = _employee(tenant_a)
    today = timezone.localdate()

    with organization_context(tenant_a.organization.id):
        finance.record_payment(child=child, amount=Decimal("10000000"), method="cash")
        payroll.record_advance(
            employee=employee, amount=Decimal("1000000"), paid_on=today.replace(day=15)
        )
        run = payroll.create_run(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            period_year=today.year,
            period_month=today.month,
        )
        payroll.finalize_run(run=run)
        run.refresh_from_db()

        assert run.total_net == Decimal("3000000.00"), "avans sof maoshdan ayrilgan"
        position = selectors.cash_position(organization_id=tenant_a.organization.id)

    assert position["payroll"] == "4000000.00"
    assert position["balance"] == "6000000.00"


def test_advance_without_a_finalized_run_still_leaves_the_till(tenant_a: Any):
    """Hisoblash hali qoralama bo'lsa ham, berilgan avans kassadan chiqqan."""
    child = _child(tenant_a)
    employee = _employee(tenant_a)
    today = timezone.localdate()

    with organization_context(tenant_a.organization.id):
        finance.record_payment(child=child, amount=Decimal("5000000"), method="cash")
        payroll.record_advance(
            employee=employee, amount=Decimal("700000"), paid_on=today.replace(day=10)
        )
        position = selectors.cash_position(organization_id=tenant_a.organization.id)

    assert position["payroll"] == "700000.00"
    assert position["balance"] == "4300000.00"


def test_reversed_payment_is_not_income(tenant_a: Any):
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        payment = finance.record_payment(child=child, amount=Decimal("1500000"), method="cash")
        finance.record_payment(child=child, amount=Decimal("500000"), method="terminal")
        finance.reverse_payment(payment=payment, reason="Xato summa")

        position = selectors.cash_position(organization_id=tenant_a.organization.id)
        revenue = selectors.revenue_report(
            organization_id=tenant_a.organization.id,
            date_from=timezone.localdate(),
            date_to=timezone.localdate(),
        )

    assert position["income"] == "500000.00"
    # Tushum hisoboti ham, usul kesimi ham qaytarilganni sanamaydi.
    assert revenue["total"] == "500000.00"
    assert [row["method"] for row in revenue["by_method"]] == ["terminal"]
