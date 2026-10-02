"""
Mijozga qaragan billing endpointlari (docs/04 §18).

Barcha yo'llar chaqiruvchining tashkilotiga bog'langan: boshqa
tashkilotning hisob-kitobini so'rashning YO'LI YO'Q — endpointlar
umuman ID qabul qilmaydi, obuna tokendan aniqlanadi.
"""

from __future__ import annotations

from django.http import Http404
from django.utils.translation import gettext
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.exceptions import BusinessRuleViolation
from apps.core.permissions import HasModulePermission
from apps.core.typing import request_user
from apps.subscriptions import services
from apps.subscriptions.models import (
    Subscription,
    SubscriptionInvoice,
    SubscriptionStatus,
    UsageSnapshot,
)
from apps.subscriptions.permissions import SubscriptionWriteGate
from apps.subscriptions.serializers import (
    AcceptTrialSerializer,
    PaymentTermSerializer,
    SubscriptionInvoiceSerializer,
    SubscriptionSerializer,
    UsageSnapshotSerializer,
)

__all__ = ["BillingViewSet"]


class BillingViewSet(viewsets.ViewSet):
    """`/billing/*` — obuna, hisoblash va hisob-fakturalar."""

    permission_classes = [HasModulePermission, SubscriptionWriteGate]
    permission_module = "billing"
    permission_action_map = {
        "subscription": "read",
        "usage": "read",
        "usage_history": "read",
        "invoices": "read",
        "invoice_detail": "read",
        "accept_trial": "update",
        "payment_term": "update",
    }

    def _subscription(self, request: Request) -> Subscription:
        organization_id = request_user(request).organization_id
        subscription = (
            Subscription.objects.filter(organization_id=organization_id)
            .exclude(status=SubscriptionStatus.CANCELLED)
            .select_related("plan")
            .first()
        )
        if subscription is None:
            raise BusinessRuleViolation(gettext("Bu tashkilotda faol obuna yoʻq."))
        return subscription

    @action(detail=False, methods=["get"])
    def subscription(self, request: Request) -> Response:
        return Response(SubscriptionSerializer(self._subscription(request)).data)

    @action(detail=False, methods=["get"])
    def usage(self, request: Request) -> Response:
        """
        Joriy davr uchun **prognoz** — hisob emas.

        `is_projection: true` bezak emas: raqam hali olinmagan. Bu
        endpointning mavjudligi ushlab qolish qarori — sonning
        o'zgarishini ko'rib turgan mijoz kutilmagan hisob olmaydi
        (docs/04 §18).
        """
        return Response(services.projected_usage(subscription=self._subscription(request)))

    @action(detail=False, methods=["get"], url_path="usage/history")
    def usage_history(self, request: Request) -> Response:
        """O'tgan davrlarning dalili — har bir hisob ortidagi asos."""
        snapshots = UsageSnapshot.objects.filter(subscription=self._subscription(request)).order_by(
            "-period_year", "-period_month", "measurement_method"
        )[:60]
        return Response(UsageSnapshotSerializer(snapshots, many=True).data)

    @action(detail=False, methods=["get"])
    def invoices(self, request: Request) -> Response:
        queryset = SubscriptionInvoice.objects.filter(
            subscription=self._subscription(request)
        ).prefetch_related("payments")
        invoice_status = request.query_params.get("status")
        if invoice_status:
            queryset = queryset.filter(status=invoice_status)
        return Response(SubscriptionInvoiceSerializer(queryset[:100], many=True).data)

    @action(detail=False, methods=["get"], url_path=r"invoices/(?P<invoice_id>[0-9a-f-]{36})")
    def invoice_detail(self, request: Request, invoice_id: str = "") -> Response:
        invoice = (
            SubscriptionInvoice.objects.filter(pk=invoice_id).prefetch_related("payments").first()
        )
        if invoice is None:
            raise Http404
        return Response(SubscriptionInvoiceSerializer(invoice).data)

    @action(detail=False, methods=["post"], url_path="accept-trial")
    def accept_trial(self, request: Request) -> Response:
        """
        Sinovni to'lovli rejimga o'tkazadi.

        Birinchi hisob SINOV BOSHLANGAN kundan hisoblanadi — bu
        ro'yxatdan o'tishdagi taklifda aytilgan bo'lishi shart
        (docs/01 §4.4).
        """
        serializer = AcceptTrialSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invoice = services.accept_trial(
            subscription=self._subscription(request),
            payment_term=serializer.validated_data["payment_term"],
            committed_children=serializer.validated_data.get("committed_children"),
        )
        return Response(SubscriptionInvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="payment-term")
    def payment_term(self, request: Request) -> Response:
        serializer = PaymentTermSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscription = services.change_payment_term(
            subscription=self._subscription(request),
            payment_term=serializer.validated_data["payment_term"],
        )
        return Response(SubscriptionSerializer(subscription).data)
