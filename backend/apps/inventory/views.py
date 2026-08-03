"""Ombor endpointlari (docs/04 §12)."""

from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.audit import services as audit
from apps.branches.selectors import resolve_branch
from apps.core.typing import request_user
from apps.core.viewsets import BranchScopedMixin, TenantViewSet
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


class _BranchCreateMixin:
    """Filialni `resolve_branch()` orqali aniqlaydigan umumiy create."""

    def perform_create(self, serializer: Any) -> None:
        user = request_user(self.request)  # type: ignore[attr-defined]
        branch = resolve_branch(user, self.request.data.get("branch_id"))  # type: ignore[attr-defined]
        serializer.save(organization=user.organization, branch=branch)


class WarehouseViewSet(_BranchCreateMixin, BranchScopedMixin, TenantViewSet):
    permission_module = "inventory"
    model = Warehouse
    serializer_class = WarehouseSerializer
    search_fields = ["name"]


class ProductCategoryViewSet(_BranchCreateMixin, BranchScopedMixin, TenantViewSet):
    permission_module = "inventory"
    model = ProductCategory
    serializer_class = ProductCategorySerializer
    search_fields = ["name"]


class SupplierViewSet(_BranchCreateMixin, BranchScopedMixin, TenantViewSet):
    permission_module = "inventory"
    model = Supplier
    serializer_class = SupplierSerializer
    search_fields = ["name", "phone", "contact_person"]


class ProductViewSet(_BranchCreateMixin, BranchScopedMixin, TenantViewSet):
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
