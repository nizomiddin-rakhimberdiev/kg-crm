"""
Yopilgan oyga pul ham yozilmaydi (audit 2026-11-12, A7 — egasining qarori).

Oy faqat tengligi "yashil" bo'lganda yopiladi. Ilgari faqat fakturalar
qulflanardi: orqaga sanalangan chiqim, to'lov, avans yoki ko'chirma
yopilgan oyning raqamini jimgina buzar, yopish esa "yashil edi" deb
turaverardi. Endi har qanday pul hujjati o'sha oyga yozilmaydi;
tuzatish — joriy oyda, qarshi yozuv bilan.
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

import pytest
from django.utils import timezone

from apps.cash import services as cash
from apps.children.models import Child
from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context
from apps.expenses import services as expenses
from apps.expenses.models import ExpenseCategory
from apps.finance import services as finance
from apps.finance.models import MonthClose
from apps.hr.models import Employee
from apps.payroll import services as payroll

pytestmark = pytest.mark.django_db

CLOSED = date(2026, 9, 15)


@pytest.fixture
def closed(tenant_a: Any) -> Any:
    tenant_a.fund(kind="all")
    with organization_context(tenant_a.organization.id):
        MonthClose.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            period_year=2026,
            period_month=9,
        )
    return tenant_a


def _at(day: date) -> datetime:
    return timezone.make_aware(datetime.combine(day, time(10, 0)))


def _child(tenant: Any) -> Child:
    return Child.objects.create(
        organization=tenant.organization,
        branch=tenant.branch,
        first_name="Ali",
        last_name="Valiyev",
        date_of_birth=date(2021, 3, 14),
        gender="male",
    )


def test_a_payment_into_a_closed_month_is_refused(closed):
    with (
        organization_context(closed.organization.id),
        pytest.raises(BusinessRuleViolation, match="yopilgan"),
    ):
        finance.record_payment(
            child=_child(closed),
            amount=Decimal("500000"),
            method="cash",
            received_by=closed.owner,
            paid_at=_at(CLOSED),
            backdate_reason="Qogʻozdagi kvitansiya",
        )


def test_an_expense_into_a_closed_month_is_refused(closed):
    with organization_context(closed.organization.id):
        category = ExpenseCategory.objects.create(
            organization=closed.organization, branch=closed.branch, name="Bozorlik"
        )
        with pytest.raises(BusinessRuleViolation, match="yopilgan"):
            expenses.create_expense_with_items(
                organization=closed.organization,
                branch=closed.branch,
                category=category,
                expense_date=CLOSED,
                items=[{"name": "Non", "quantity": "1", "unit": "dona", "unit_price": "5000"}],
                cash_account=cash.account_for_method(branch=closed.branch, method="cash"),
                created_by=closed.owner,
            )


def test_an_advance_into_a_closed_month_is_refused(closed):
    with organization_context(closed.organization.id):
        employee = Employee.objects.create(
            organization=closed.organization,
            branch=closed.branch,
            first_name="Nilufar",
            last_name="Sodiqova",
            hire_date=date(2026, 1, 10),
            base_salary=Decimal("3000000"),
        )
        with pytest.raises(BusinessRuleViolation, match="yopilgan"):
            payroll.record_advance(employee=employee, amount=Decimal("100000"), paid_on=CLOSED)


def test_a_transfer_into_a_closed_month_is_refused(closed):
    with organization_context(closed.organization.id):
        till = cash.account_for_method(branch=closed.branch, method="cash")
        bank = cash.account_for_method(branch=closed.branch, method="transfer")
        with pytest.raises(BusinessRuleViolation, match="yopilgan"):
            cash.transfer(source=till, target=bank, amount=Decimal("1000"), occurred_at=_at(CLOSED))


def test_money_lent_in_a_closed_month_is_refused(closed):
    with organization_context(closed.organization.id):
        till = cash.account_for_method(branch=closed.branch, method="cash")
        with pytest.raises(BusinessRuleViolation, match="yopilgan"):
            cash.lend_money(
                account=till,
                amount=Decimal("1000"),
                occurred_on=CLOSED,
                person="Oshpaz",
                reason="Kasalxonaga",
                created_by=closed.owner,
            )


def test_the_open_month_is_untouched(closed):
    with organization_context(closed.organization.id):
        finance.record_payment(
            child=_child(closed),
            amount=Decimal("500000"),
            method="cash",
            received_by=closed.owner,
        )
