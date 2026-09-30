"""Ombor endpointlari (docs/04 §12)."""

from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.audit import services as audit
from apps.core.typing import request_user
from apps.core.viewsets import BranchCreateMixin, BranchScopedMixin, TenantViewSet
from apps.inventory import services
from apps.inventory.models import (
    Product,
    ProductCategory,
    StockMovement,
    Supplier,
    Warehouse,
)
from apps.inventory.serializers import (
    MovementWriteSerializer,
    ProductCategorySerializer,
    ProductSerializer,
    StockMovementSerializer,
    SupplierSerializer,
    WarehouseSerializer,
)

__all__ = [
    "WarehouseViewSet",
    "ProductCategoryViewSet",
    "ProductViewSet",
    "SupplierViewSet",
    "StockMovementViewSet",
]


class WarehouseViewSet(BranchCreateMixin, BranchScopedMixin, TenantViewSet):
    permission_module = "inventory"
    model = Warehouse
    serializer_class = WarehouseSerializer
    search_fields = ["name"]


class ProductCategoryViewSet(BranchCreateMixin, BranchScopedMixin, TenantViewSet):
    permission_module = "inventory"
    model = ProductCategory
    serializer_class = ProductCategorySerializer
    search_fields = ["name"]


class SupplierViewSet(BranchCreateMixin, BranchScopedMixin, TenantViewSet):
    permission_module = "inventory"
    model = Supplier
    serializer_class = SupplierSerializer
    search_fields = ["name", "phone", "contact_person"]


class ProductViewSet(BranchCreateMixin, BranchScopedMixin, TenantViewSet):
    permission_module = "inventory"
    permission_action_map = {"low_stock": "read", "valuation": "read"}
    model = Product
    serializer_class = ProductSerializer
    select_related_fields = ("category",)
    search_fields = ["name", "sku"]
    ordering_fields = ["name", "current_stock"]
    filterset_fields = ["category", "unit"]

    @action(detail=False, methods=["get"], url_path="low-stock")
    def low_stock(self, request: Request) -> Response:
        """`GET /products/low-stock` — minimumdan past qoldiqlar."""
        user = request_user(request)
        return Response(
            services.low_stock_products(
                organization_id=user.organization_id, branch_id=user.branch_id
            )
        )

    @action(detail=False, methods=["get"])
    def valuation(self, request: Request) -> Response:
        """`GET /products/valuation` — qoldiq qiymati (oxirgi xarid narxi bo'yicha)."""
        user = request_user(request)
        return Response(
            services.stock_valuation(organization_id=user.organization_id, branch_id=user.branch_id)
        )


class StockMovementViewSet(BranchScopedMixin, TenantViewSet):
    """
    Stok harakatlari — append-only (D3).

    `PATCH`/`DELETE` yo'q: xato `adjustment` harakati bilan tuzatiladi.
    """

    permission_module = "inventory"
    model = StockMovement
    select_related_fields = ("product", "warehouse", "supplier")
    filterset_fields = ["product", "warehouse", "direction", "movement_type"]
    ordering_fields = ["occurred_at"]
    http_method_names = ["get", "post", "head", "options"]

    def get_serializer_class(self) -> Any:
        return (
            StockMovementSerializer
            if self.request.method in ("GET", "HEAD")
            else MovementWriteSerializer
        )

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = MovementWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        movement = services.record_movement(
            product=data["product"],
            warehouse=data["warehouse"],
            movement_type=data["movement_type"],
            quantity=data["quantity"],
            direction=data.get("direction"),
            supplier=data.get("supplier"),
            unit_cost=data.get("unit_cost"),
            occurred_at=data.get("occurred_at"),
            reference=data.get("reference", ""),
            note=data.get("note", ""),
            create_expense=data.get("create_expense", True),
            cash_account=data.get("cash_account"),
            expense_category=data.get("expense_category"),
            created_by=request_user(request),
        )
        # Stok harakati — mulk harakati. `adjustment` esa qoldiqni
        # hujjatsiz o'zgartirishning yagona yo'li, ya'ni aynan shu yerda
        # "kim tuzatdi?" degan savol paydo bo'ladi.
        audit.record(
            action="create",
            request=request._request,
            actor=request_user(request),
            entity_type="stock_movement",
            entity_id=movement.id,
            changes={
                "product": str(movement.product_id),
                "direction": movement.direction,
                "movement_type": movement.movement_type,
                "quantity": str(movement.quantity),
            },
        )
        return Response(StockMovementSerializer(movement).data, status=status.HTTP_201_CREATED)
