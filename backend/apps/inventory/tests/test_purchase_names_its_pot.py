"""
Ombor xaridi qaysi hisobdan to'langanini aytadi (audit 2026-11-12, A4).

Xarid — pul chiqishi (Q13, ADR-17). Har bir pul chiqadigan hujjat o'z
qopini aytadi (17-invariant); xarid esa sukut naqd kassadan yechardi
va bankdan to'langan xarid jimgina kassadan yozilardi. Harakatlar
ro'yxatida esa kim va qachon yozgani ko'rinmasdi.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.cash.models import CashAccount
from apps.core.tenancy import organization_context
from apps.inventory.models import Product, ProductCategory, Warehouse

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup(tenant_a):
    tenant_a.fund()
    with organization_context(tenant_a.organization.id):
        warehouse = Warehouse.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Asosiy"
        )
        category = ProductCategory.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Sabzavot"
        )
        product = Product.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            category=category,
            name="Kartoshka",
            unit="kg",
        )
        pot = CashAccount.objects.get(branch=tenant_a.branch, kind="cash", is_active=True)
    return product, warehouse, pot


def _post(tenant_a, product, warehouse, **extra):
    return tenant_a.client().post(
        reverse("v1:stock-movement-list"),
        {
            "product_id": str(product.id),
            "warehouse_id": str(warehouse.id),
            "movement_type": "purchase",
            "quantity": "10",
            **extra,
        },
        format="json",
    )


def test_a_paid_purchase_without_a_pot_is_refused(tenant_a, setup):
    product, warehouse, _ = setup
    response = _post(tenant_a, product, warehouse, unit_cost="4500")
    assert response.status_code == 422, response.json()


def test_a_free_purchase_needs_no_pot(tenant_a, setup):
    product, warehouse, _ = setup
    assert _post(tenant_a, product, warehouse).status_code == 201


def test_the_list_says_who_and_when(tenant_a, setup):
    product, warehouse, pot = setup
    created = _post(tenant_a, product, warehouse, unit_cost="4500", cash_account_id=str(pot.id))
    assert created.status_code == 201, created.json()

    row = tenant_a.client().get(reverse("v1:stock-movement-list")).json()["data"][0]
    assert row["created_by_name"]
    assert row["occurred_at"]
    assert Decimal(row["unit_cost"]) == Decimal("4500")
