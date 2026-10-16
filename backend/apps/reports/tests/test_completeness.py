"""
Ma'lumot to'liqligi (Bosqich 13.3e, brif §4): hisobot faqat kiritilgan
ma'lumotchalik yaxshi — shuning uchun uning o'zi ham ko'rsatiladi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from apps.cash.models import CashAccount
from apps.core.tenancy import organization_context
from apps.expenses.models import Expense, ExpenseCategory
from apps.expenses.services import approve_expense

pytestmark = pytest.mark.django_db


def test_completeness_counts_receipts_closed_days_statements_and_the_queue(tenant_a: Any):
    tenant_a.fund(kind="all")
    with organization_context(tenant_a.organization.id):
        till = CashAccount.objects.get(branch=tenant_a.branch, kind="cash", is_active=True)
        category = ExpenseCategory.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Bozor"
        )
        for day, receipt in ((date(2026, 9, 3), "r.png"), (date(2026, 9, 4), "")):
            expense = Expense.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                category=category,
                amount=Decimal("100000"),
                expense_date=day,
                cash_account=till,
                receipt=receipt,
            )
            approve_expense(expense=expense, approved_by=tenant_a.owner)

    data = (
        tenant_a.client()
        .get("/api/v1/reports/completeness", {"year": 2026, "month": 9})
        .json()["data"]
    )

    assert data["expenses"]["total"] == 2
    assert data["expenses"]["with_receipt"] == 1
    assert data["expenses"]["percent"] == 50
    assert data["bank"]["statement_uploaded"] is False
    assert data["bank"]["unmatched_lines"] == 0
    assert data["cash"]["closed_days"] == 0
    assert data["cash"]["active_days"] >= 2
