"""
Kassa endpointlari (docs/04 §9.4, ADR-17).

Qoplar RO'YXATI ochiq, lekin ularning HARAKATLARI emas: harakat —
pul yozuvi, va u hisobotlar orqali, o'z ruxsati bilan ko'riladi.
Bu yerda faqat "qaysi qoplar bor va ularda qancha" degan savol.
"""

from __future__ import annotations

from datetime import datetime, time
from typing import Any

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.audit import services as audit
from apps.branches.selectors import resolve_branch
from apps.cash import selectors, services
from apps.cash.models import CashAccount
from apps.cash.serializers import CashAccountSerializer, CashAdjustSerializer
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
    permission_action_map = {"balances": "read", "adjust": "update"}
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

    @action(detail=True, methods=["post"])
    def adjust(self, request: Request, pk: str | None = None) -> Response:
        """
        `POST /cash-accounts/{id}/adjust` — boshlangʻich qoldiq yoki
        sanoq farqi (ADR-29).

        Busiz qoldiq doim noldan boshlanardi: tizimga yil oʻrtasida
        kelgan bogʻchaning seyfidagi pul hech qayerda yoʻq edi va
        birinchi chiqimdayoq qoldiq manfiyga tushardi.
        """
        account = self.get_object()
        user = request_user(request)
        payload = CashAdjustSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        occurred_on = data.get("occurred_on")
        movement = services.adjust_balance(
            account=account,
            amount=data["amount"],
            reason=data["reason"],
            opening=data.get("opening", False),
            occurred_at=(
                timezone.make_aware(datetime.combine(occurred_on, time.min))
                if occurred_on
                else None
            ),
            created_by=user,
        )
        audit.record(
            action="update",
            request=request._request,
            actor=user,
            entity_type="cash_account",
            entity_id=account.id,
            changes={
                "amount": str(data["amount"]),
                "reason": data["reason"],
                "opening": data.get("opening", False),
            },
        )
        return Response(
            {
                "id": str(movement.id),
                "balance": f"{selectors.account_balance(account_id=account.id):.2f}",
            },
            status=status.HTTP_201_CREATED,
        )

    def perform_create(self, serializer: Any) -> None:
        user = request_user(self.request)
        branch = resolve_branch(user, self.request.data.get("branch_id"))
        serializer.save(organization=user.organization, branch=branch)

    def get_base_queryset(self) -> Any:
        return super().get_base_queryset().select_related("branch")
