"""
Rad etilgan chiqim bazada QOLMAYDI (audit, 2026-10-30).

Auditda: qoldiqdan ortiq summa yuborilsa `422` keladi, lekin bazada
`pending` chiqim paydo boʻlardi. Foydalanuvchi tugmani qayta bosardi —
va har bosish yana bitta qator qoldirardi.

Sababi oddiy: ekran avval hujjatni saqlab, keyin uni tasdiqlardi.
Tasdiqlash ADR-29 ga urilib rad etilardi, saqlangan hujjat esa
oʻz-oʻzidan qaytmasdi — `perform_create` tranzaksiyada emas edi.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.urls import reverse

from apps.cash import services as cash
from apps.core.tenancy import organization_context
from apps.expenses.models import Expense, ExpenseCategory

pytestmark = pytest.mark.django_db


@pytest.fixture
def category(tenant_a) -> ExpenseCategory:
    with organization_context(tenant_a.organization.id):
        cash.ensure_branch_accounts(branch=tenant_a.branch)
        return ExpenseCategory.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Xoʻjalik"
        )


def _count(tenant_a: Any) -> int:
    with organization_context(tenant_a.organization.id):
        return Expense.objects.count()


def test_an_overdrawn_expense_leaves_no_row(tenant_a, category):
    before = _count(tenant_a)
    with organization_context(tenant_a.organization.id):
        pot = cash.account_for_method(branch=tenant_a.branch, method="cash")

    response = tenant_a.client().post(
        reverse("v1:expense-list"),
        {
            "category_id": str(category.id),
            "amount": "5000000",
            "expense_date": "2026-10-30",
            "description": "Boʻsh kassadan",
            "cash_account_id": str(pot.id),
        },
        format="json",
    )

    assert response.status_code == 422, response.data
    assert _count(tenant_a) == before


def test_pressing_twice_does_not_pile_up_drafts(tenant_a, category):
    before = _count(tenant_a)
    with organization_context(tenant_a.organization.id):
        pot = cash.account_for_method(branch=tenant_a.branch, method="cash")

    payload = {
        "category_id": str(category.id),
        "amount": "5000000",
        "expense_date": "2026-10-30",
        "description": "Boʻsh kassadan",
        "cash_account_id": str(pot.id),
    }
    for _ in range(3):
        assert (
            tenant_a.client().post(reverse("v1:expense-list"), payload, format="json").status_code
            == 422
        )

    assert _count(tenant_a) == before
