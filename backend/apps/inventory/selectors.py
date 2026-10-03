"""Read-side entry points of `inventory` for other modules (invariant 1)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from apps.inventory.models import MovementType, Product, StockMovement, Warehouse

__all__ = ["products_queryset", "warehouses_queryset", "last_purchase_costs", "available_stock"]


def products_queryset() -> Any:
    return Product.objects.filter(is_active=True)


def warehouses_queryset() -> Any:
    return Warehouse.objects.filter(is_active=True)


def last_purchase_costs(product_ids: list[Any]) -> dict[Any, Decimal]:
    """Latest purchase unit cost per product — the same basis as `stock_valuation`."""
    costs: dict[Any, Decimal] = {}
    rows = (
        StockMovement.objects.filter(
            product_id__in=product_ids,
            movement_type=MovementType.PURCHASE,
            unit_cost__isnull=False,
        )
        .order_by("product_id", "-occurred_at")
        .values_list("product_id", "unit_cost")
    )
    for product_id, unit_cost in rows:
        costs.setdefault(product_id, unit_cost)
    return costs


def available_stock(product_id: Any) -> Decimal:
    """What `record_movement` checks a stock-out against."""
    from apps.inventory.services import product_stock

    return product_stock(product_id=product_id)
