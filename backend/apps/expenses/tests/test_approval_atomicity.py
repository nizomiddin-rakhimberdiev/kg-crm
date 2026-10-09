"""
Tasdiqlash — bitta hodisa, yarmi emas (invariant 12).

Chiqimni tasdiqlash IKKI yozuv qiladi: hujjat holati `approved` ga
oʻtadi va pul kassadan chiqadi. Ular bitta tranzaksiyada boʻlishi
SHART. Aks holda ikkinchisi yiqilganda birinchisi joyida qoladi:
chiqim hisobotda ham, oylik yigʻindida ham koʻrinadi, kassada esa
hech narsa qimirlamaydi — va bu farqni hech kim sezmaydi, chunki
ikkala raqam ham "toʻgʻri" koʻrinadi.

Bu ADR-29 dan keyin nazariy xavf boʻlmay qoldi: qopda pul yetmasa
`post_movement()` ENDI muntazam xato koʻtaradi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context
from apps.expenses import services
from apps.expenses.models import Expense, ExpenseCategory, ExpenseStatus

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]


def _pending_expense(tenant: Any, amount: str = "500000") -> Expense:
    with organization_context(tenant.organization.id):
        category = ExpenseCategory.objects.create(
            organization=tenant.organization, branch=tenant.branch, name="Kommunal"
        )
        return Expense.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            category=category,
            amount=Decimal(amount),
            expense_date=date(2026, 10, 1),
            description="Elektr",
        )


def test_a_refused_payout_leaves_the_expense_pending(tenant_a: Any):
    """
    Kassada pul yoʻq → tasdiqlash yiqiladi → hujjat TEGILMAGAN qoladi.

    Ilgari hujjat `approved` boʻlib saqlanib, keyin pul harakati
    yiqilardi: chiqim hisobotga kirib, kassadan esa chiqmasdi.
    """
    expense = _pending_expense(tenant_a)
    with organization_context(tenant_a.organization.id):
        with pytest.raises(BusinessRuleViolation):
            services.approve_expense(expense=expense, approved_by=tenant_a.owner)

        expense.refresh_from_db()

    assert expense.status == ExpenseStatus.PENDING
    assert expense.approved_by_id is None
    assert expense.decided_at is None


def test_the_cash_ledger_is_untouched_when_approval_fails(tenant_a: Any):
    """Yarim yozuv ham qolmasin: jurnalda hech narsa paydo boʻlmaydi."""
    from apps.cash.models import CashMovement

    expense = _pending_expense(tenant_a)
    with organization_context(tenant_a.organization.id):
        before = CashMovement.objects.count()
        with pytest.raises(BusinessRuleViolation):
            services.approve_expense(expense=expense, approved_by=tenant_a.owner)
        assert CashMovement.objects.count() == before


def test_a_funded_pot_approves_both_halves(tenant_a: Any):
    """Qarama-qarshi tomoni: pul boʻlsa — ikkala yozuv ham boʻladi."""
    from apps.cash.models import CashMovement, MovementSource

    tenant_a.fund()
    expense = _pending_expense(tenant_a)
    with organization_context(tenant_a.organization.id):
        services.approve_expense(expense=expense, approved_by=tenant_a.owner)
        expense.refresh_from_db()
        moved = CashMovement.objects.filter(
            source_type=MovementSource.EXPENSE, source_id=expense.id
        ).count()

    assert expense.status == ExpenseStatus.APPROVED
    assert moved == 1
