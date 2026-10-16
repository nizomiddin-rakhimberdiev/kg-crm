"""
Kassa endpointlari (docs/04 §9.4, ADR-17).

Qoplar RO'YXATI ochiq, lekin ularning HARAKATLARI emas: harakat —
pul yozuvi, va u hisobotlar orqali, o'z ruxsati bilan ko'riladi.
Bu yerda faqat "qaysi qoplar bor va ularda qancha" degan savol.
"""

from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal
from typing import Any

from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response

from apps.audit import services as audit
from apps.branches.selectors import resolve_branch
from apps.cash import selectors, services
from apps.cash.models import CashAccount, CashCount, CashHandover, MoneyOperation
from apps.cash.serializers import (
    CashAccountSerializer,
    CashAdjustSerializer,
    CashCountSerializer,
    CashCountWriteSerializer,
    CashHandoverSerializer,
    CashHandoverWriteSerializer,
    CashTransferSerializer,
    MoneyOperationSerializer,
    MoneyOperationWriteSerializer,
)
from apps.core.typing import request_user
from apps.core.viewsets import BranchScopedMixin, TenantViewSet
from apps.finance.scope import payments_own_only

__all__ = [
    "CashAccountViewSet",
    "CashCountViewSet",
    "CashHandoverViewSet",
    "MoneyOperationViewSet",
]


class CashAccountViewSet(BranchScopedMixin, TenantViewSet):
    """
    Pul qoplari — nomini o'zgartirish va yangisini qo'shish mumkin.

    `payments` moduli ruxsati bilan: qopni ko'rish "kassada qancha
    pul bor" degan savolga yaqin, va u moliyaviy savol.
    """

    permission_module = "payments"
    permission_action_map = {
        "balances": "read",
        "adjust": "update",
        "transfer": "update",
        "custody": "read",
    }
    model = CashAccount
    serializer_class = CashAccountSerializer
    search_fields = ["name"]
    ordering_fields = ["kind", "name"]

    @action(detail=False, methods=["get"])
    def balances(self, request: Request) -> Response:
        """
        `GET /cash-accounts/balances` — har bir qopdagi qoldiq.

        Ikki to'siq, ikkalasi ham ilgari yo'q edi:

        * "Faqat o'z to'lovlari" bilan cheklangan odam (kassir, ADR-30)
          qoldiqni ko'rmaydi: qopdagi pul — bog'chaning butun tushumi.
          Ekranda u allaqachon yashiringan, lekin API ochiq qolardi.
        * Filialga bog'langan xodim faqat O'Z filialining qoplarini
          ko'radi, `?branch=` bilan boshqasini so'rasa ham — to'lovlar
          va hisobotlardagi qoida bilan bir xil. Egasi istalganini.
        """
        user = request_user(request)
        if payments_own_only(user):
            raise PermissionDenied(gettext("Bu amalga ruxsat yoʻq."))
        branch = request.query_params.get("branch") or None
        branch_id = branch if user.is_org_owner else user.branch_id
        rows = selectors.account_balances(organization_id=user.organization_id, branch_id=branch_id)
        # Bank qoldig'i ikkiga bo'linadi (Bosqich 13.2c): tushgan va yo'lda —
        # terminal/Click/Payme puli hali bankka kelmagan.
        from apps.finance.selectors import in_transit

        transit: dict[str, Decimal] = {}
        for item in in_transit(organization_id=user.organization_id, branch_id=branch_id):
            key = item["cash_account_id"]
            transit[key] = transit.get(key, Decimal("0")) + Decimal(item["expected_amount"])
        for row in rows:
            moving = transit.get(row["id"], Decimal("0"))
            row["in_transit"] = f"{moving:.2f}"
            row["arrived"] = f"{Decimal(row['balance']) - moving:.2f}"
        return Response(rows)

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

    @action(detail=False, methods=["post"])
    def transfer(self, request: Request) -> Response:
        """
        `POST /cash-accounts/transfer` — inkassa, bankdan naqd yechish
        (Bosqich 12.5, test 14).

        Tushum ham, xarajat ham o'zgarmaydi: ikki harakat, bitta
        `transfer_group`. Qopda yo'q pul ko'chmaydi (ADR-29) — faqat
        `allow_negative` bilan, ogohlantirishni o'qigandan keyin.
        """
        user = request_user(request)
        _refuse_own_only(user)
        payload = CashTransferSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        occurred_on = data.get("occurred_on")
        out, into = services.transfer(
            source=data["source"],
            target=data["target"],
            amount=data["amount"],
            description=data["reason"],
            occurred_at=(
                timezone.make_aware(datetime.combine(occurred_on, time(12)))
                if occurred_on
                else None
            ),
            created_by=user,
            allow_negative=data.get("allow_negative", False),
        )
        audit.record(
            action="create",
            request=request._request,
            actor=user,
            entity_type="cash_transfer",
            entity_id=out.transfer_group,
            changes={
                "from": str(data["source"].id),
                "to": str(data["target"].id),
                "amount": str(data["amount"]),
                "reason": data["reason"],
            },
        )
        return Response(
            {
                "transfer_group": str(out.transfer_group),
                "from_balance": f"{selectors.account_balance(account_id=out.cash_account_id):.2f}",
                "to_balance": f"{selectors.account_balance(account_id=into.cash_account_id):.2f}",
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"])
    def custody(self, request: Request) -> Response:
        """
        `GET /cash-accounts/custody` — kimning qo'lida qancha naqd pul
        (Bosqich 12.5). "Faqat o'ziniki" foydalanuvchi faqat o'zini ko'radi.
        """
        user = request_user(request)
        branch = request.query_params.get("branch") or None
        return Response(
            selectors.custody(
                organization_id=user.organization_id,
                branch_id=branch if user.is_org_owner else user.branch_id,
                user_id=user.pk if payments_own_only(user) else None,
            )
        )

    def perform_create(self, serializer: Any) -> None:
        user = request_user(self.request)
        branch = resolve_branch(user, self.request.data.get("branch_id"))
        serializer.save(organization=user.organization, branch=branch)

    def get_base_queryset(self) -> Any:
        return super().get_base_queryset().select_related("branch")


def _refuse_own_only(user: Any) -> None:
    """Butun qopga tegadigan amal — "faqat o'ziniki" kassirga yopiq (ADR-30)."""
    if payments_own_only(user):
        raise PermissionDenied(gettext("Bu amalga ruxsat yoʻq."))


class CashHandoverViewSet(BranchScopedMixin, TenantViewSet):
    """
    Naqd pulni topshirish — kassir → mas'ul shaxs (Bosqich 12.5).

    Yozuv o'zgarmaydi va o'chmaydi: faqat qabul qiluvchi tasdiqlaydi yoki
    sababi bilan rad etadi.
    """

    permission_module = "payments"
    permission_action_map = {"confirm": "read", "reject": "read", "receivers": "read"}
    model = CashHandover
    serializer_class = CashHandoverSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_base_queryset(self) -> Any:
        queryset = (
            super()
            .get_base_queryset()
            .select_related("from_user", "to_user")
            .order_by("-created_at")
        )
        user = request_user(self.request)
        if payments_own_only(user):
            queryset = queryset.filter(Q(from_user=user) | Q(to_user=user))
        return queryset

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        from apps.accounts.models import User

        user = request_user(request)
        payload = CashHandoverWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        receiver = User.objects.filter(pk=data["to_user_id"]).first()
        if receiver is None:
            raise NotFound(gettext("Qabul qiluvchi topilmadi."))
        handover = services.hand_over(
            from_user=user,
            to_user=receiver,
            amount=data["amount"],
            note=data.get("note", ""),
            account=data.get("cash_account"),
        )
        audit.record(
            action="create",
            request=request._request,
            actor=user,
            entity_type="cash_handover",
            entity_id=handover.id,
            changes={"to": str(receiver.id), "amount": str(handover.amount)},
        )
        return Response(CashHandoverSerializer(handover).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def receivers(self, request: Request) -> Response:
        """
        `GET /cash-handovers/receivers` — kimga topshirish mumkin.

        Mas'ul shaxs — butun kassani ko'radigan odam: `payments.read` bor va
        "faqat o'ziniki" emas. Kassir kassirga topshirmaydi: pul baribir
        "kassada" qolardi, faqat boshqa kassirning cho'ntagida.
        Kassirda `users.read` yo'q, shuning uchun ro'yxat shu yerda.
        """
        from apps.accounts.models import User
        from apps.core.permissions import has_permission_code

        user = request_user(request)
        people = User.objects.filter(is_active=True).exclude(pk=user.pk).select_related("role")
        if user.branch_id:
            people = people.filter(Q(branch_id=user.branch_id) | Q(branch__isnull=True))
        rows = [
            {"id": str(person.id), "full_name": person.full_name}
            for person in people.order_by("full_name")
            if (person.is_org_owner or has_permission_code(person, "payments.read"))
            and not payments_own_only(person)
        ]
        return Response(rows)

    @action(detail=True, methods=["post"])
    def confirm(self, request: Request, pk: str | None = None) -> Response:
        """`POST /cash-handovers/{id}/confirm` — qabul qiluvchi "oldim" deydi."""
        user = request_user(request)
        handover = services.confirm_handover(handover=self.get_object(), user=user)
        audit.record(
            action="approve",
            request=request._request,
            actor=user,
            entity_type="cash_handover",
            entity_id=handover.id,
            changes={"status": handover.status},
        )
        return Response(CashHandoverSerializer(handover).data)

    @action(detail=True, methods=["post"])
    def reject(self, request: Request, pk: str | None = None) -> Response:
        """`POST /cash-handovers/{id}/reject {reason}` — sababi bilan."""
        user = request_user(request)
        handover = services.reject_handover(
            handover=self.get_object(), user=user, reason=str(request.data.get("reason", ""))
        )
        audit.record(
            action="reject",
            request=request._request,
            actor=user,
            entity_type="cash_handover",
            entity_id=handover.id,
            changes={"status": handover.status, "reason": handover.decision_note},
        )
        return Response(CashHandoverSerializer(handover).data)


class CashCountViewSet(BranchScopedMixin, TenantViewSet):
    """
    Kun yopilishi — sanoq tizim bilan (Bosqich 12.5).

    Butun qopga tegadi, shuning uchun "faqat o'ziniki" kassirga yopiq:
    kassir pulni mas'ulga topshiradi, mas'ul sanaydi va yopadi.
    """

    permission_module = "payments"
    permission_action_map = {"create": "update"}
    model = CashCount
    serializer_class = CashCountSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_base_queryset(self) -> Any:
        _refuse_own_only(request_user(self.request))
        return super().get_base_queryset().select_related("cash_account", "created_by")

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        user = request_user(request)
        _refuse_own_only(user)
        payload = CashCountWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        count = services.close_day(
            account=data["cash_account"],
            counted=data["counted"],
            reason=data.get("reason", ""),
            created_by=user,
        )
        audit.record(
            action="create",
            request=request._request,
            actor=user,
            entity_type="cash_count",
            entity_id=count.id,
            changes={
                "counted": str(count.counted),
                "system": str(count.system_balance),
                "difference": str(count.difference),
                "reason": count.reason,
            },
        )
        return Response(CashCountSerializer(count).data, status=status.HTTP_201_CREATED)


class MoneyOperationViewSet(BranchScopedMixin, TenantViewSet):
    """
    `/money-operations` — boshqa daromad, egaga to'lov, egadan kiritma,
    kredit, soliq to'lovi (Bosqich 13.2b).

    Butun qopga va egasining puliga tegadi: "faqat o'ziniki" kassirga yopiq;
    yozish — `payments.update`. Hujjat o'zgarmaydi va o'chmaydi.
    """

    permission_module = "payments"
    permission_action_map = {"create": "update"}
    model = MoneyOperation
    serializer_class = MoneyOperationSerializer
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ["kind"]

    def get_base_queryset(self) -> Any:
        _refuse_own_only(request_user(self.request))
        return super().get_base_queryset().select_related("cash_account", "created_by")

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        user = request_user(request)
        _refuse_own_only(user)
        payload = MoneyOperationWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        period = data.get("period") or ""
        operation = services.record_operation(
            kind=data["kind"],
            subtype=data.get("subtype", ""),
            account=data["cash_account"],
            amount=data["amount"],
            occurred_on=data["occurred_on"],
            reason=data["reason"],
            period=tuple(int(part) for part in period.split("-")) if period else None,  # type: ignore[arg-type]
            counterparty=data.get("counterparty", ""),
            created_by=user,
            allow_negative=data.get("allow_negative", False),
        )
        audit.record(
            action="create",
            request=request._request,
            actor=user,
            entity_type="money_operation",
            entity_id=operation.id,
            changes={
                "kind": operation.kind,
                "amount": str(operation.amount),
                "reason": operation.reason,
            },
        )
        return Response(MoneyOperationSerializer(operation).data, status=status.HTTP_201_CREATED)
