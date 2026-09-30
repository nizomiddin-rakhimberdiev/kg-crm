"""
Kassa endpointlari (docs/04 §9.4, ADR-17).

Qoplar RO'YXATI ochiq, lekin ularning HARAKATLARI emas: harakat —
pul yozuvi, va u hisobotlar orqali, o'z ruxsati bilan ko'riladi.
Bu yerda faqat "qaysi qoplar bor va ularda qancha" degan savol.
"""

from __future__ import annotations

from typing import Any

from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.branches.selectors import resolve_branch
from apps.cash import selectors
from apps.cash.models import CashAccount
from apps.cash.serializers import CashAccountSerializer
from apps.core.typing import request_user
from apps.core.viewsets import BranchScopedMixin, TenantViewSet

__all__ = ["CashAccountViewSet"]


class CashAccountViewSet(BranchScopedMixin, TenantViewSet):
    """
    Pul qoplari — nomini o'zgartirish va yangisini qo'shish mumkin.

    `payments` moduli ruxsati bilan: qopni ko'rish "kassada qancha
    pul bor" degan savolga yaqin, va u moliyaviy savol.
    """

    permission_module = "payments"
    permission_action_map = {"balances": "read"}
    model = CashAccount
    serializer_class = CashAccountSerializer
    search_fields = ["name"]
    ordering_fields = ["kind", "name"]

    @action(detail=False, methods=["get"])
    def balances(self, request: Request) -> Response:
        """`GET /cash-accounts/balances` — har bir qopdagi qoldiq."""
        user = request_user(request)
        return Response(
            selectors.account_balances(
                organization_id=user.organization_id,
                branch_id=request.query_params.get("branch") or None,
            )
        )

    def perform_create(self, serializer: Any) -> None:
        user = request_user(self.request)
        branch = resolve_branch(user, self.request.data.get("branch_id"))
        serializer.save(organization=user.organization, branch=branch)

    def get_base_queryset(self) -> Any:
        return super().get_base_queryset().select_related("branch")
