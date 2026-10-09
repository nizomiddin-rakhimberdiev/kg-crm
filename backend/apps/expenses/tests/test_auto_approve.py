"""
Chiqim yaratilgan zahoti tasdiqlanadi (PLAN 7.2, egasining qarori
2026-10-06).

Ilgari har bir chiqim `pending` bo'lib turardi va kimdir "Tasdiqlash"
tugmasini bosishini kutardi. Amalda bog'chada chiqimni kiritadigan odam
bilan tasdiqlaydigan odam BIR XIL — ya'ni bu bosqich hech narsani
tekshirmaydi, faqat ikkita ekranga ikki xil raqam chiqarib turadi:
hisobotda chiqim ko'rinmaydi, kassadagi pul esa kamaymaydi.

Pul harakati o'zgarmaydi: u avvalgidek tasdiqlash paytida yoziladi —
endi tasdiqlash yaratish bilan bir vaqtda bo'ladi (ADR-17).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from apps.cash.models import CashMovement, MovementDirection, MovementSource
from apps.core.tenancy import organization_context
from apps.expenses.models import ExpenseCategory

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]

URL = "/api/v1/expenses"


def _category(tenant, name: str = "Bozorlik") -> ExpenseCategory:
    # Bogʻchada pul avval tushadi, keyin chiqadi (ADR-29).
    tenant.fund()
    with organization_context(tenant.organization.id):
        return ExpenseCategory.objects.create(
            organization=tenant.organization, branch=tenant.branch, name=name
        )


def _create(client, category, amount: str = "600000", **extra):
    return client.post(
        URL,
        {
            "category_id": str(category.id),
            "amount": amount,
            "expense_date": str(date(2026, 10, 5)),
            "description": "sabzavotlar",
            **extra,
        },
        format="json",
    )


def test_a_new_expense_is_already_approved(tenant_a):
    category = _category(tenant_a)
    response = _create(tenant_a.client(), category)
    assert response.status_code == 201, response.json()
    assert response.json()["data"]["status"] == "approved"


def test_the_money_leaves_the_till_at_once(tenant_a):
    category = _category(tenant_a)
    _create(tenant_a.client(), category)
    with organization_context(tenant_a.organization.id):
        movement = CashMovement.objects.get(source_type=MovementSource.EXPENSE)
    assert movement.direction == MovementDirection.OUT
    assert movement.amount == Decimal("600000.00")


def test_it_counts_in_the_month_summary_immediately(tenant_a):
    category = _category(tenant_a)
    _create(tenant_a.client(), category)
    data = (
        tenant_a.client()
        .get(f"{URL}/summary", {"from": "2026-10-01", "to": "2026-10-31"})
        .json()["data"]
    )
    assert Decimal(data["total"]) == Decimal("600000.00")


def test_the_approver_is_the_person_who_entered_it(tenant_a):
    category = _category(tenant_a)
    body = _create(tenant_a.client(), category).json()["data"]
    assert body["approved_by_name"] == tenant_a.owner.full_name
