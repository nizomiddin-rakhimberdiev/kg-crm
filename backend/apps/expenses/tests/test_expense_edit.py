"""
Chiqimni tahrirlash va "Qaysi puldan" majburiyligi (mijoz soʻrovi, 2026-10-14).

Chiqim yaratilishi bilan tasdiqlanadi va pul qopdan chiqadi (PLAN 7.2,
ADR-17). Demak tahrirlash — hujjatni oʻzgartirish VA pul izini
toʻgʻrilash: eski chiqimga qarshi yozuv, yangisiga chiqim. Jurnal
append-only qoladi; hech bir eski harakat oʻzgarmaydi.

"Qaysi puldan" endi majburiy: sukut naqd kassa boʻlganda bankdan
toʻlangan chiqim jimgina kassadan yozilardi, va adashish koʻrinmasdi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.authentication import issue_token_pair
from apps.accounts.models import User
from apps.cash import selectors
from apps.cash.models import CashAccount, CashMovement, MovementSource
from apps.core.tenancy import organization_context
from apps.expenses.models import Expense, ExpenseCategory

pytestmark = pytest.mark.django_db


def _data(response: Any) -> Any:
    body = response.json()
    return body.get("data", body)


@pytest.fixture
def pots(tenant_a: Any) -> dict[str, CashAccount]:
    tenant_a.fund("1000000", kind="cash")
    tenant_a.fund("1000000", kind="bank")
    with organization_context(tenant_a.organization.id):
        return {
            a.kind: a for a in CashAccount.objects.filter(branch=tenant_a.branch, is_active=True)
        }


@pytest.fixture
def category(tenant_a: Any) -> ExpenseCategory:
    with organization_context(tenant_a.organization.id):
        return ExpenseCategory.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Bozorlik"
        )


def _balance(tenant: Any, pot: CashAccount) -> Decimal:
    with organization_context(tenant.organization.id):
        return selectors.account_balance(account_id=pot.id)


def _create(client: APIClient, category: ExpenseCategory, pot: CashAccount, price: str) -> str:
    response = client.post(
        reverse("v1:expense-list"),
        {
            "category_id": str(category.id),
            "expense_date": "2026-10-14",
            "cash_account_id": str(pot.id),
            "items": [{"name": "Non", "quantity": "1", "unit": "dona", "unit_price": price}],
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    return str(_data(response)["id"])


def _edit(client: APIClient, expense_id: str, **payload: Any) -> Any:
    return client.patch(reverse("v1:expense-detail", args=[expense_id]), payload, format="json")


# --- "Qaysi puldan" majburiy ---


def test_creating_an_expense_without_a_pot_is_refused(tenant_a: Any, category: Any, pots: Any):
    response = tenant_a.client().post(
        reverse("v1:expense-list"),
        {
            "category_id": str(category.id),
            "expense_date": "2026-10-14",
            "items": [{"name": "Non", "quantity": "1", "unit": "dona", "unit_price": "1000"}],
        },
        format="json",
    )
    assert response.status_code == 400
    assert "cash_account_id" in str(response.json())
    assert _balance(tenant_a, pots["cash"]) == Decimal("1000000.00")


# --- Tahrirlash ---


def test_editing_the_amount_moves_only_the_difference(tenant_a: Any, category: Any, pots: Any):
    client = tenant_a.client()
    expense_id = _create(client, category, pots["cash"], "72000")

    response = _edit(
        client,
        expense_id,
        items=[{"name": "Non", "quantity": "10", "unit": "dona", "unit_price": "10000"}],
    )

    assert response.status_code == 200, response.json()
    assert Decimal(_data(response)["amount"]) == Decimal("100000.00")
    assert _balance(tenant_a, pots["cash"]) == Decimal("900000.00")


def test_editing_the_pot_moves_the_money(tenant_a: Any, category: Any, pots: Any):
    client = tenant_a.client()
    expense_id = _create(client, category, pots["cash"], "200000")

    response = _edit(client, expense_id, cash_account_id=str(pots["bank"].id))

    assert response.status_code == 200, response.json()
    assert _balance(tenant_a, pots["cash"]) == Decimal("1000000.00")
    assert _balance(tenant_a, pots["bank"]) == Decimal("800000.00")


def test_editing_twice_leaves_one_expense_worth_of_money_out(
    tenant_a: Any, category: Any, pots: Any
):
    client = tenant_a.client()
    expense_id = _create(client, category, pots["cash"], "100000")

    _edit(client, expense_id, items=[{"name": "Non", "quantity": "1", "unit_price": "50000"}])
    _edit(client, expense_id, items=[{"name": "Non", "quantity": "1", "unit_price": "70000"}])

    assert _balance(tenant_a, pots["cash"]) == Decimal("930000.00")


def test_editing_keeps_the_journal_append_only(tenant_a: Any, category: Any, pots: Any):
    client = tenant_a.client()
    expense_id = _create(client, category, pots["cash"], "100000")
    with organization_context(tenant_a.organization.id):
        before = list(CashMovement.objects.filter(source_id=expense_id).values("id", "amount"))

    _edit(client, expense_id, items=[{"name": "Non", "quantity": "1", "unit_price": "40000"}])

    with organization_context(tenant_a.organization.id):
        still = list(
            CashMovement.objects.filter(id__in=[r["id"] for r in before]).values("id", "amount")
        )
        total = CashMovement.objects.filter(
            source_type=MovementSource.EXPENSE, source_id=expense_id
        ).count()
    assert still == before
    assert total == 3  # chiqim, qarshi yozuv, yangi chiqim


def test_editing_description_and_category_touches_no_money(tenant_a: Any, category: Any, pots: Any):
    client = tenant_a.client()
    expense_id = _create(client, category, pots["cash"], "100000")
    with organization_context(tenant_a.organization.id):
        other = ExpenseCategory.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Taʼmir"
        )
        movements = CashMovement.objects.filter(source_id=expense_id).count()

    response = _edit(client, expense_id, description="Kraska", category_id=str(other.id))

    assert response.status_code == 200, response.json()
    with organization_context(tenant_a.organization.id):
        expense = Expense.objects.get(id=expense_id)
        assert CashMovement.objects.filter(source_id=expense_id).count() == movements
    assert expense.description == "Kraska"
    assert expense.category_id == other.id


def test_an_edit_the_pot_cannot_cover_asks_first(tenant_a: Any, category: Any, pots: Any):
    """ADR-29: qopda yetmasa rad etiladi; ogohlantirishni oʻqib belgilasa — yoziladi."""
    client = tenant_a.client()
    expense_id = _create(client, category, pots["cash"], "100000")
    big = [{"name": "Goʻsht", "quantity": "20", "unit": "kg", "unit_price": "95000"}]

    refused = _edit(client, expense_id, items=big, cash_account_id=str(pots["bank"].id))
    assert refused.status_code == 422
    assert _balance(tenant_a, pots["cash"]) == Decimal("900000.00")

    allowed = _edit(
        client,
        expense_id,
        items=big,
        cash_account_id=str(pots["bank"].id),
        allow_negative=True,
    )
    assert allowed.status_code == 200, allowed.json()
    assert _balance(tenant_a, pots["bank"]) == Decimal("-900000.00")


def test_a_rejected_expense_cannot_be_edited(tenant_a: Any, category: Any, pots: Any):
    with organization_context(tenant_a.organization.id):
        expense = Expense.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            category=category,
            amount=Decimal("1000"),
            expense_date=date(2026, 10, 14),
            status="rejected",
        )
    response = _edit(tenant_a.client(), str(expense.id), description="x")
    assert response.status_code == 422


def test_a_stock_purchase_keeps_its_lines(tenant_a: Any, category: Any, pots: Any):
    """Ombor xaridi chiqimi qatorlari omborda — ularni bu yerdan oʻzgartirish miqdorni buzardi."""
    from apps.inventory.models import Product, StockMovement, Warehouse

    client = tenant_a.client()
    expense_id = _create(client, category, pots["cash"], "100000")
    with organization_context(tenant_a.organization.id):
        product = Product.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Un", unit="kg"
        )
        warehouse = Warehouse.objects.filter(branch=tenant_a.branch).first() or (
            Warehouse.objects.create(
                organization=tenant_a.organization, branch=tenant_a.branch, name="Asosiy"
            )
        )
        StockMovement.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            product=product,
            warehouse=warehouse,
            direction="in",
            movement_type="purchase",
            quantity=Decimal("10"),
            unit_cost=Decimal("10000"),
            occurred_at=timezone.now(),
            expense_id=expense_id,
        )

    lines = _edit(client, expense_id, items=[{"name": "Un", "quantity": "1", "unit_price": "5000"}])
    words = _edit(client, expense_id, description="Un xaridi")

    assert lines.status_code == 422
    assert words.status_code == 200
    assert _balance(tenant_a, pots["cash"]) == Decimal("900000.00")


# --- Ruxsat va tashkilot chegarasi ---


def test_editing_needs_expenses_update(tenant_a: Any, category: Any, pots: Any):
    expense_id = _create(tenant_a.client(), category, pots["cash"], "1000")
    with organization_context(tenant_a.organization.id):
        teacher = User.objects.create_user(
            email="davomat@alfa.uz",
            password="Juda-Kuchli-Parol-2026",  # noqa: S106
            full_name="Davomat",
            organization=tenant_a.organization,
            role=tenant_a.role("attendance_manager"),
            branch=tenant_a.branch,
        )
        tokens = issue_token_pair(teacher)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert _edit(client, expense_id, description="x").status_code == 403


@pytest.mark.tenancy
def test_another_tenants_expense_is_404(tenant_a: Any, tenant_b: Any, category: Any, pots: Any):
    expense_id = _create(tenant_a.client(), category, pots["cash"], "1000")
    assert _edit(tenant_b.client(), expense_id, description="x").status_code == 404
