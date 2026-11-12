"""
Ombor testlari (docs/03 §15.5, §26).

Asosiy savol: "stok manfiy boʻlib qola oladimi?" — bu ombor uchun
balansning noto'g'ri bo'lishi bilan bir xil og'irlikdagi xato.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse

from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context
from apps.inventory import services
from apps.inventory.models import (
    MovementDirection,
    Product,
    ProductCategory,
    StockMovement,
    Warehouse,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def warehouse(tenant_a) -> Warehouse:
    # Xarid — pul chiqishi (Q13); boʻsh qopdan chiqim endi
    # toʻxtaydi (ADR-29), shuning uchun avval qop toʻldiriladi.
    tenant_a.fund()
    with organization_context(tenant_a.organization.id):
        return Warehouse.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Oshxona ombori"
        )


@pytest.fixture
def product(tenant_a) -> Product:
    with organization_context(tenant_a.organization.id):
        category = ProductCategory.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Sabzavot"
        )
        return Product.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            name="Kartoshka",
            category=category,
            unit="kg",
            min_stock=Decimal("10"),
        )


def _cash_pot(tenant):
    from apps.cash.models import CashAccount

    with organization_context(tenant.organization.id):
        return CashAccount.objects.get(branch=tenant.branch, kind="cash", is_active=True)


def _in(tenant, product, warehouse, qty: str, cost: str | None = None):
    with organization_context(tenant.organization.id):
        return services.record_movement(
            product=product,
            warehouse=warehouse,
            movement_type="purchase",
            quantity=Decimal(qty),
            unit_cost=Decimal(cost) if cost else None,
        )


def _out(tenant, product, warehouse, qty: str):
    with organization_context(tenant.organization.id):
        return services.record_movement(
            product=product,
            warehouse=warehouse,
            movement_type="consumption",
            quantity=Decimal(qty),
        )


class TestStockIsDerived:
    def test_stock_is_inbound_minus_outbound(self, tenant_a, product, warehouse):
        _in(tenant_a, product, warehouse, "50")
        _in(tenant_a, product, warehouse, "30")
        _out(tenant_a, product, warehouse, "20")

        with organization_context(tenant_a.organization.id):
            assert services.product_stock(product_id=product.id) == Decimal("60.000")

    def test_cache_is_never_the_source_of_truth(self, tenant_a, product, warehouse):
        """Keshni ataylab buzib, harakatlardan tiklanishini tekshiramiz."""
        _in(tenant_a, product, warehouse, "50")
        with organization_context(tenant_a.organization.id):
            Product.objects.filter(pk=product.pk).update(current_stock=Decimal("999"))
            assert services.product_stock(product_id=product.id) == Decimal("50.000")
            assert services.recompute_product_stock(product) == Decimal("50.000")
            product.refresh_from_db()
            assert product.current_stock == Decimal("50.000")

    def test_database_rejects_non_positive_quantity(self, tenant_a, product, warehouse):
        with (
            organization_context(tenant_a.organization.id),
            pytest.raises(IntegrityError),
            transaction.atomic(),
        ):
            StockMovement.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                product=product,
                warehouse=warehouse,
                direction="in",
                movement_type="purchase",
                quantity=Decimal("0"),
                occurred_at="2026-07-01T00:00:00Z",
            )


class TestNegativeStockGuard:
    def test_outbound_beyond_stock_is_rejected(self, tenant_a, product, warehouse):
        """
        Qoldiqdan ortiq chiqim rad etiladi.

        Buni DB `CHECK` bilan ifodalab bo'lmaydi — u yugurib boruvchi
        yig'indini ko'rmaydi. Shuning uchun tekshiruv qulf ostida,
        tranzaksiya ichida (docs/03 §26).
        """
        _in(tenant_a, product, warehouse, "10")
        with (
            organization_context(tenant_a.organization.id),
            pytest.raises(BusinessRuleViolation, match="yetarli emas"),
        ):
            services.record_movement(
                product=product,
                warehouse=warehouse,
                movement_type="consumption",
                quantity=Decimal("11"),
            )

    def test_exact_stock_can_be_consumed(self, tenant_a, product, warehouse):
        _in(tenant_a, product, warehouse, "10")
        _out(tenant_a, product, warehouse, "10")
        with organization_context(tenant_a.organization.id):
            assert services.product_stock(product_id=product.id) == Decimal("0.000")

    def test_stock_never_goes_negative_across_many_movements(self, tenant_a, product, warehouse):
        _in(tenant_a, product, warehouse, "100")
        for _ in range(5):
            _out(tenant_a, product, warehouse, "20")
        with organization_context(tenant_a.organization.id):
            assert services.product_stock(product_id=product.id) == Decimal("0.000")
            with pytest.raises(BusinessRuleViolation):
                services.record_movement(
                    product=product,
                    warehouse=warehouse,
                    movement_type="consumption",
                    quantity=Decimal("0.001"),
                )


class TestDirectionInference:
    def test_purchase_is_inbound(self, tenant_a, product, warehouse):
        movement = _in(tenant_a, product, warehouse, "5")
        assert movement.direction == MovementDirection.IN

    def test_waste_is_outbound(self, tenant_a, product, warehouse):
        _in(tenant_a, product, warehouse, "5")
        with organization_context(tenant_a.organization.id):
            movement = services.record_movement(
                product=product,
                warehouse=warehouse,
                movement_type="waste",
                quantity=Decimal("1"),
            )
        assert movement.direction == MovementDirection.OUT

    def test_adjustment_requires_explicit_direction(self, tenant_a, product, warehouse):
        """
        `adjustment` ikki tomonlama — yo'nalish taxmin qilinmaydi.

        Taxmin qilish "tuzatdim, lekin qaysi tomonga?" degan noaniqlikni
        jimgina hal qilib yuborardi.
        """
        with (
            organization_context(tenant_a.organization.id),
            pytest.raises(BusinessRuleViolation, match="yoʻnalish"),
        ):
            services.record_movement(
                product=product,
                warehouse=warehouse,
                movement_type="adjustment",
                quantity=Decimal("1"),
            )

    def test_adjustment_with_direction_works(self, tenant_a, product, warehouse):
        with organization_context(tenant_a.organization.id):
            movement = services.record_movement(
                product=product,
                warehouse=warehouse,
                movement_type="adjustment",
                quantity=Decimal("3"),
                direction="in",
            )
        assert movement.direction == MovementDirection.IN


class TestLowStock:
    def test_lists_products_below_minimum(self, tenant_a, product, warehouse):
        _in(tenant_a, product, warehouse, "5")  # min_stock = 10
        with organization_context(tenant_a.organization.id):
            rows = services.low_stock_products(organization_id=tenant_a.organization.id)
        assert len(rows) == 1
        assert rows[0]["name"] == "Kartoshka"

    def test_sufficient_stock_is_not_listed(self, tenant_a, product, warehouse):
        _in(tenant_a, product, warehouse, "50")
        with organization_context(tenant_a.organization.id):
            assert services.low_stock_products(organization_id=tenant_a.organization.id) == []


class TestValuation:
    def test_uses_last_purchase_price(self, tenant_a, product, warehouse):
        _in(tenant_a, product, warehouse, "10", cost="5000")
        _in(tenant_a, product, warehouse, "10", cost="6000")
        with organization_context(tenant_a.organization.id):
            result = services.stock_valuation(organization_id=tenant_a.organization.id)
        assert result["basis"] == "last_purchase_price"
        assert result["total_value"] == "120000.00"


class TestEndpoints:
    def test_record_movement_endpoint(self, tenant_a, product, warehouse):
        response = tenant_a.client().post(
            reverse("v1:stock-movement-list"),
            {
                "product_id": str(product.id),
                "warehouse_id": str(warehouse.id),
                "movement_type": "purchase",
                "quantity": "25.5",
                "unit_cost": "4500",
                # Pul chiqadigan xarid o'z qopini aytadi (audit 2026-11-12).
                "cash_account_id": str(_cash_pot(tenant_a).id),
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["data"]["direction"] == "in"

    def test_movements_are_append_only(self, tenant_a, product, warehouse):
        movement = _in(tenant_a, product, warehouse, "5")
        client = tenant_a.client()
        url = reverse("v1:stock-movement-detail", args=[movement.id])
        assert client.patch(url, {"quantity": "1"}, format="json").status_code == 405
        assert client.delete(url).status_code == 405

    def test_current_stock_is_read_only_over_the_api(self, tenant_a, product, warehouse):
        """Qoldiqni toʻgʻridan-toʻgʻri yozib boʻlmaydi — faqat harakat orqali."""
        _in(tenant_a, product, warehouse, "10")
        response = tenant_a.client().patch(
            reverse("v1:product-detail", args=[product.id]),
            {"current_stock": "9999"},
            format="json",
        )
        assert response.status_code == 200
        # So'rov tugagach kontekst tozalanadi (P0-001) — o'qish uchun qayta ochamiz.
        with organization_context(tenant_a.organization.id):
            product.refresh_from_db()
            assert product.current_stock == Decimal("10.000")

    def test_low_stock_endpoint(self, tenant_a, product, warehouse):
        _in(tenant_a, product, warehouse, "5")
        response = tenant_a.client().get(reverse("v1:product-low-stock"))
        assert response.status_code == 200
        assert len(response.json()["data"]) == 1

    @pytest.mark.tenancy
    def test_cannot_move_stock_into_another_tenants_warehouse(self, tenant_a, tenant_b, product):
        with organization_context(tenant_b.organization.id):
            foreign = Warehouse.objects.create(
                organization=tenant_b.organization, branch=tenant_b.branch, name="Begona"
            )
        response = tenant_a.client().post(
            reverse("v1:stock-movement-list"),
            {
                "product_id": str(product.id),
                "warehouse_id": str(foreign.id),
                "movement_type": "purchase",
                "quantity": "1",
            },
            format="json",
        )
        # Begona ombor `TenantPrimaryKeyRelatedField` da "mavjud emas".
        assert response.status_code == 400
        assert "warehouse_id" in response.json()["error"]["details"]

    def test_manager_can_manage_inventory(self, tenant_a, product, warehouse):
        """Menejerda `inventory` toʻliq (docs/02 §11.2)."""
        from rest_framework.test import APIClient

        from apps.accounts.authentication import issue_token_pair
        from apps.accounts.models import User

        with organization_context(tenant_a.organization.id):
            manager = User.objects.create_user(
                email="menejer@alfa.uz",
                password="Juda-Kuchli-Parol-2026",  # noqa: S106
                full_name="Menejer",
                organization=tenant_a.organization,
                role=tenant_a.role("manager"),
                branch=tenant_a.branch,
            )
            tokens = issue_token_pair(manager)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        response = client.post(
            reverse("v1:stock-movement-list"),
            {
                "product_id": str(product.id),
                "warehouse_id": str(warehouse.id),
                "movement_type": "purchase",
                "quantity": "5",
            },
            format="json",
        )
        assert response.status_code == 201
