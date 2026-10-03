"""
Kitchen endpoints (PLAN 6.6). Module `inventory`: the kitchen is where the
store is spent, and the same people run both — a new module would change
every role in production for a screen that fits this one.
"""

from __future__ import annotations

from typing import Any

from django.utils.translation import gettext
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response

from apps.branches.selectors import resolve_branch
from apps.core.typing import request_user
from apps.core.viewsets import BranchScopedMixin, TenantViewSet
from apps.kitchen import services
from apps.kitchen.models import Dish, MenuDay
from apps.kitchen.serializers import (
    DishSerializer,
    DishWriteSerializer,
    MenuDaySerializer,
    MenuPlanSerializer,
    ServeSerializer,
)

__all__ = ["DishViewSet", "MenuDayViewSet"]


class DishViewSet(BranchScopedMixin, TenantViewSet):
    permission_module = "inventory"
    model = Dish
    serializer_class = DishSerializer
    search_fields = ["name"]

    def get_base_queryset(self) -> Any:
        return Dish.objects.filter(is_active=True)

    def _save(self, request: Request, dish: Dish | None) -> Dish:
        serializer = DishWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request_user(request)
        branch = dish.branch if dish else resolve_branch(user, data.get("branch_id"))
        return services.save_dish(
            organization=user.organization,
            branch=branch,
            dish=dish,
            name=data["name"],
            portion_grams=data.get("portion_grams"),
            note=data.get("note", ""),
            ingredients=data["ingredients"],
        )

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        dish = self._save(request, None)
        return Response(DishSerializer(dish).data, status=status.HTTP_201_CREATED)

    def update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        dish = self._save(request, self.get_object())
        return Response(DishSerializer(dish).data)

    def perform_destroy(self, instance: Dish) -> None:
        # Past menus keep pointing at it (RESTRICT): switched off, never deleted.
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])


class MenuDayViewSet(BranchScopedMixin, TenantViewSet):
    permission_module = "inventory"
    permission_action_map = {
        "plan": "create",
        "preview": "read",
        "serve": "create",
        "unserve": "update",
    }
    model = MenuDay
    serializer_class = MenuDaySerializer
    select_related_fields = ("warehouse",)
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self) -> Any:
        queryset = super().get_queryset()
        start = self.request.query_params.get("from")
        end = self.request.query_params.get("to")
        if start:
            queryset = queryset.filter(menu_date__gte=start)
        if end:
            queryset = queryset.filter(menu_date__lte=end)
        return queryset

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return self._plan(request)

    @action(detail=False, methods=["post"])
    def plan(self, request: Request) -> Response:
        return self._plan(request)

    def _plan(self, request: Request) -> Response:
        from apps.inventory.selectors import warehouses_queryset

        serializer = MenuPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request_user(request)
        branch = resolve_branch(user, data.get("branch_id"))
        warehouse = warehouses_queryset().filter(pk=data["warehouse_id"]).first()
        if warehouse is None:
            raise NotFound(gettext("Ombor topilmadi."))
        menu_day = services.set_menu(
            organization=user.organization,
            branch=branch,
            menu_date=data["menu_date"],
            warehouse=warehouse,
            items=data["items"],
        )
        return Response(MenuDaySerializer(menu_day).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def preview(self, request: Request, pk: str | None = None) -> Response:
        try:
            staff = max(0, int(request.query_params.get("staff_portions", 0)))
        except ValueError:
            staff = 0
        return Response(services.preview(self.get_object(), staff_portions=staff))

    @action(detail=True, methods=["post"])
    def serve(self, request: Request, pk: str | None = None) -> Response:
        serializer = ServeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        menu_day = services.serve(
            self.get_object(),
            staff_portions=serializer.validated_data["staff_portions"],
            user=request_user(request),
        )
        return Response(MenuDaySerializer(menu_day).data)

    @action(detail=True, methods=["post"])
    def unserve(self, request: Request, pk: str | None = None) -> Response:
        menu_day = services.unserve(self.get_object(), user=request_user(request))
        return Response(MenuDaySerializer(menu_day).data)
