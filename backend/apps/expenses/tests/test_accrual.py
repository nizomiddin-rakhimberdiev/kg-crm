"""
Chiqim: tegishli oy, kapital xarajat, nasiya, ikki darajali toifa
(Bosqich 13.2a, "Moliya markazi" brifi §3.3–3.6).

Excel'dagi saboq: kommunal oktyabrda to'lansa ham sentabr xarajati;
konditsioner — investitsiya, oylik xarajatni buzmaydi; go'sht oy davomida
olinib, oy oxirida to'lanadi — u to'languncha yetkazib beruvchiga qarz.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from apps.cash import selectors
from apps.cash.models import CashAccount, CashMovement
from apps.core.tenancy import organization_context
from apps.expenses.models import Expense, ExpenseCategory
from apps.inventory.models import Supplier

pytestmark = pytest.mark.django_db

URL = "/api/v1/expenses"


def _category(tenant: Any, name: str = "Kommunal", **extra: Any) -> ExpenseCategory:
    with organization_context(tenant.organization.id):
        return ExpenseCategory.objects.create(
            organization=tenant.organization, branch=tenant.branch, name=name, **extra
        )


@pytest.fixture(autouse=True)
def _funded(tenant_a: Any) -> None:
    tenant_a.fund(kind="all")


def _bank(tenant: Any) -> CashAccount:
    with organization_context(tenant.organization.id):
        return CashAccount.objects.get(branch=tenant.branch, kind="bank", is_active=True)


def _create(tenant: Any, **extra: Any) -> Any:
    payload = {
        "category_id": str(extra.pop("category", None) or _category(tenant).id),
        "amount": "1200000",
        "expense_date": "2026-10-05",
        "cash_account_id": str(_bank(tenant).id),
        **extra,
    }
    return tenant.client().post(URL, payload, format="json")


# --- Tegishli oy ---


def test_the_month_defaults_to_the_month_it_was_paid(tenant_a: Any):
    response = _create(tenant_a)
    assert response.status_code == 201, response.json()
    assert response.json()["data"]["period"] == "2026-10"


def test_a_utility_bill_paid_in_october_belongs_to_september(tenant_a: Any):
    response = _create(tenant_a, period="2026-09")
    assert response.status_code == 201, response.json()
    with organization_context(tenant_a.organization.id):
        expense = Expense.objects.get()
    assert (expense.period_year, expense.period_month) == (2026, 9)
    assert expense.expense_date == date(2026, 10, 5)


def test_a_malformed_month_is_refused(tenant_a: Any):
    assert _create(tenant_a, period="2026-13").status_code == 400


# --- Kapital xarajat ---


def test_an_investment_is_marked_and_spread(tenant_a: Any):
    response = _create(tenant_a, amount="12000000", is_capex=True, amortize_months=12)
    assert response.status_code == 201, response.json()
    data = response.json()["data"]
    assert data["is_capex"] is True
    assert data["amortize_months"] == 12


def test_spreading_needs_the_investment_flag(tenant_a: Any):
    assert _create(tenant_a, amortize_months=12).status_code == 400


# --- Nasiya ---


def test_a_purchase_on_credit_moves_no_money_until_it_is_paid(tenant_a: Any):
    with organization_context(tenant_a.organization.id):
        supplier = Supplier.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Goʻsht doʻkoni"
        )
    bank = _bank(tenant_a)
    with organization_context(tenant_a.organization.id):
        before = selectors.account_balance(account_id=bank.id)

    response = _create(
        tenant_a,
        on_credit=True,
        supplier_id=str(supplier.id),
        due_date="2026-10-31",
        amount="4500000",
    )

    assert response.status_code == 201, response.json()
    expense_id = response.json()["data"]["id"]
    assert response.json()["data"]["on_credit"] is True
    assert response.json()["data"]["paid_on"] is None
    with organization_context(tenant_a.organization.id):
        assert selectors.account_balance(account_id=bank.id) == before
        assert not CashMovement.objects.filter(source_id=expense_id).exists()

    paid = tenant_a.client().post(
        f"{URL}/{expense_id}/mark-paid",
        {"cash_account_id": str(bank.id), "paid_on": "2026-10-30"},
        format="json",
    )

    assert paid.status_code == 200, paid.json()
    assert paid.json()["data"]["paid_on"] == "2026-10-30"
    with organization_context(tenant_a.organization.id):
        assert selectors.account_balance(account_id=bank.id) == before - Decimal("4500000")
        movement = CashMovement.objects.get(source_id=expense_id)
    assert movement.occurred_at.date() == date(2026, 10, 30)

    again = tenant_a.client().post(
        f"{URL}/{expense_id}/mark-paid", {"cash_account_id": str(bank.id)}, format="json"
    )
    with organization_context(tenant_a.organization.id):
        assert CashMovement.objects.filter(source_id=expense_id).count() == 1
    assert again.status_code in (200, 422)


def test_a_credit_purchase_names_its_supplier(tenant_a: Any):
    assert _create(tenant_a, on_credit=True).status_code == 400


@pytest.mark.tenancy
def test_another_tenants_supplier_is_refused(tenant_a: Any, tenant_b: Any):
    with organization_context(tenant_b.organization.id):
        foreign = Supplier.objects.create(
            organization=tenant_b.organization, branch=tenant_b.branch, name="Begona"
        )
    assert _create(tenant_a, on_credit=True, supplier_id=str(foreign.id)).status_code == 400


# --- Ikki darajali toifa va hisob kodi ---


def test_categories_have_two_levels_and_an_account_code(tenant_a: Any):
    client = tenant_a.client()
    parent = client.post(
        "/api/v1/expense-categories", {"name": "Oziq-ovqat", "account_code": "2010"}, format="json"
    )
    assert parent.status_code == 201, parent.json()
    child = client.post(
        "/api/v1/expense-categories",
        {"name": "Goʻsht", "parent_id": parent.json()["data"]["id"]},
        format="json",
    )
    assert child.status_code == 201, child.json()
    assert child.json()["data"]["parent_name"] == "Oziq-ovqat"

    grandchild = client.post(
        "/api/v1/expense-categories",
        {"name": "Mol goʻshti", "parent_id": child.json()["data"]["id"]},
        format="json",
    )
    assert grandchild.status_code == 400


def test_a_new_branch_starts_with_the_default_categories(tenant_a: Any):
    from apps.expenses.services import ensure_default_categories

    with organization_context(tenant_a.organization.id):
        created = ensure_default_categories(branch=tenant_a.branch)
        again = ensure_default_categories(branch=tenant_a.branch)
        names = set(
            ExpenseCategory.objects.filter(parent__isnull=True).values_list("name", flat=True)
        )
    assert created > 0 and again == 0
    assert {"Ish haqi", "Oziq-ovqat", "Kommunal", "Bank xarajatlari va komissiyalar"} <= names
