"""Moliya endpointlari (docs/04 §9)."""

from __future__ import annotations

import uuid
from typing import Any

from django.http import Http404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.audit import services as audit
from apps.branches.selectors import resolve_branch
from apps.core.exceptions import BusinessRuleViolation
from apps.core.permissions import HasModulePermission
from apps.core.typing import request_user
from apps.core.viewsets import BranchScopedMixin, TenantReadOnlyViewSet, TenantViewSet
from apps.finance import selectors, services
from apps.finance.models import ChildLedgerEntry, Discount, Invoice, Payment, TariffPlan
from apps.finance.serializers import (
    DiscountSerializer,
    GenerateInvoicesSerializer,
    InvoiceSerializer,
    LedgerEntrySerializer,
    PaymentSerializer,
    PaymentWriteSerializer,
    TariffPlanSerializer,
)
from apps.subscriptions.permissions import SubscriptionWriteGate

__all__ = [
    "TariffPlanViewSet",
    "DiscountViewSet",
    "InvoiceViewSet",
    "LedgerViewSet",
    "PaymentViewSet",
    "DebtorViewSet",
]


class TariffPlanViewSet(BranchScopedMixin, TenantViewSet):
    permission_module = "payments"
    model = TariffPlan
    serializer_class = TariffPlanSerializer
    search_fields = ["name"]

    def perform_create(self, serializer: Any) -> None:
        user = request_user(self.request)
        branch = resolve_branch(user, self.request.data.get("branch_id"))
        serializer.save(organization=user.organization, branch=branch)

    def perform_destroy(self, instance: TariffPlan) -> None:
        if instance.children.filter(is_active=True).exists():
            raise BusinessRuleViolation(
                "Bu tarifga biriktirilgan bolalar bor — avval ularni boshqa tarifga o'tkazing."
            )
        instance.is_active = False
        instance.save(update_fields=["is_active"])


class DiscountViewSet(BranchScopedMixin, TenantViewSet):
    permission_module = "payments"
    model = Discount
    serializer_class = DiscountSerializer
    select_related_fields = ("child",)
    filterset_fields = ["child", "discount_type"]

    def perform_create(self, serializer: Any) -> None:
        child = serializer.validated_data["child"]
        serializer.save(organization=child.organization, branch=child.branch)
        audit.record(
            action="create",
            request=self.request._request,
            actor=request_user(self.request),
            entity_type="discount",
            entity_id=serializer.instance.id,
        )


class InvoiceViewSet(BranchScopedMixin, TenantReadOnlyViewSet):
    """
    Hisob-fakturalar — faqat o'qish + aniq amallar.

    `PATCH`/`DELETE` ataylab yo'q: hisob-faktura ledger yozuvini yaratgan
    hujjat. Uni tahrirlash ledger bilan hujjatni bir-biridan ajratib
    yuborardi. O'zgartirish kerak bo'lsa — bekor qilib, yangisini chiqarish
    (D3, docs/03 §13.3).
    """

    permission_module = "payments"
    permission_action_map = {"generate": "create", "cancel": "update"}
    model = Invoice
    serializer_class = InvoiceSerializer
    select_related_fields = ("child", "tariff")
    filterset_fields = ["status", "period_year", "period_month", "child"]
    ordering_fields = ["issued_date", "due_date", "amount_due"]
    search_fields = ["number", "child__first_name", "child__last_name"]

    def get_base_queryset(self) -> Any:
        return super().get_base_queryset().prefetch_related("lines")

    @action(detail=False, methods=["post"])
    def generate(self, request: Request) -> Response:
        """
        `POST /invoices/generate` — davr uchun oylik hisob-fakturalar.

        Idempotent: qayta chaqirilsa mavjudlari o'tkazib yuboriladi va
        ikkinchi marta hisoblanmaydi.
        """
        serializer = GenerateInvoicesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = request_user(request)
        branch = None
        if data.get("branch_id"):
            branch = resolve_branch(user, data["branch_id"])
        elif user.branch_id:
            branch = user.branch

        result = services.generate_monthly_invoices(
            organization=user.organization,
            branch=branch,
            period_year=data["period_year"],
            period_month=data["period_month"],
            created_by=user,
        )
        audit.record(
            action="create",
            request=request._request,
            actor=user,
            entity_type="invoice_run",
            changes=result.as_dict(),
        )
        return Response(result.as_dict(), status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def cancel(self, request: Request, pk: str | None = None) -> Response:
        """Hisob-fakturani qarshi ledger yozuvi bilan bekor qiladi."""
        invoice = self.get_object()
        user = request_user(request)
        services.cancel_invoice(
            invoice=invoice,
            reason=request.data.get("reason", ""),
            created_by=user,
        )
        audit.record(
            action="update",
            request=request._request,
            actor=user,
            entity_type="invoice",
            entity_id=invoice.id,
            changes={"status": "cancelled", "reason": request.data.get("reason", "")},
        )
        invoice.refresh_from_db()
        return Response(InvoiceSerializer(invoice).data)


class LedgerViewSet(BranchScopedMixin, TenantReadOnlyViewSet):
    """
    Ledger — **faqat o'qish**, hech qanday yozish endpointi yo'q.

    Yozuvlar servis qatlamidagi `post_ledger_entry()` orqali qo'shiladi.
    API orqali qo'lda yozuv qo'shish imkoniyati ledger'ning ishonchliligini
    yo'q qilardi: har bir qator qaysi hujjatdan kelganini ko'rsatishi shart.
    """

    permission_module = "payments"
    model = ChildLedgerEntry
    serializer_class = LedgerEntrySerializer
    filterset_fields = ["child", "entry_type", "direction", "source_type"]
    ordering_fields = ["occurred_at"]

    @action(detail=False, methods=["get"], url_path="balance")
    def balance(self, request: Request) -> Response:
        """`GET /ledger/balance?child=<uuid>` — ledger'dan hisoblangan balans."""
        child_id = request.query_params.get("child")
        if not child_id:
            raise BusinessRuleViolation("`child` parametri majburiy.")

        from apps.children.models import Child

        # `Child.objects` tenant bilan cheklangan — begona bola "topilmadi".
        child = Child.objects.filter(pk=child_id).first()
        if child is None:
            raise BusinessRuleViolation("Bola topilmadi.")

        return Response(
            {
                "child_id": str(child.id),
                "full_name": child.full_name,
                # Keshdan EMAS, ledger'dan hisoblangan (D3).
                "balance": str(services.child_balance(child.id)),
                "cached_balance": str(child.balance),
            }
        )


class PaymentViewSet(BranchScopedMixin, TenantViewSet):
    """
    To'lovlar (docs/04 §9.3).

    `PATCH`/`DELETE` yo'q: to'lov o'zgarmas. Tuzatish `POST /{id}/reverse`
    orqali qarshi yozuv bilan qilinadi (D3).
    """

    permission_module = "payments"
    permission_action_map = {"reverse": "update", "daily_summary": "read"}
    model = Payment
    select_related_fields = ("child", "invoice")
    filterset_fields = ["child", "invoice", "method"]
    ordering_fields = ["paid_at", "amount"]
    http_method_names = ["get", "post", "head", "options"]

    def get_serializer_class(self) -> Any:
        return (
            PaymentSerializer if self.request.method in ("GET", "HEAD") else PaymentWriteSerializer
        )

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = PaymentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request_user(request)

        # `Idempotency-Key` — sanoat konvensiyasi (Stripe va boshqalar
        # shu nomni ishlatadi). Mijoz uni FORMA yuborilishiga bog'laydi,
        # so'rovga emas: qayta yuborilgan so'rov o'sha kalit bilan
        # keladi va ikkinchi to'lov yozilmaydi.
        #
        # Sarlavha bo'lmasa xatti-harakat avvalgidek — eski mijozlar va
        # skriptlar ishlayveradi, lekin ular takrorlanishdan himoyalanmagan.
        payment = services.record_payment(
            child=data["child"],
            amount=data["amount"],
            method=data["method"],
            invoice=data.get("invoice"),
            reference=data.get("reference", ""),
            paid_at=data.get("paid_at"),
            received_by=user,
            idempotency_key=request.headers.get("Idempotency-Key", "").strip(),
        )
        audit.record(
            action="create",
            request=request._request,
            actor=user,
            entity_type="payment",
            entity_id=payment.id,
            changes={"amount": str(payment.amount), "method": payment.method},
        )
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def reverse(self, request: Request, pk: str | None = None) -> Response:
        """To'lovni qaytaradi — qarshi ledger yozuvi bilan."""
        payment = self.get_object()
        user = request_user(request)
        services.reverse_payment(
            payment=payment, reason=request.data.get("reason", ""), created_by=user
        )
        audit.record(
            action="update",
            request=request._request,
            actor=user,
            entity_type="payment",
            entity_id=payment.id,
            changes={"reversed": True, "reason": request.data.get("reason", "")},
        )
        payment.refresh_from_db()
        return Response(PaymentSerializer(payment).data)

    @action(detail=False, methods=["get"], url_path="daily-summary")
    def daily_summary(self, request: Request) -> Response:
        """`GET /payments/daily-summary?date=` — kassirning kunlik hisoboti."""
        from datetime import datetime

        raw = request.query_params.get("date")
        try:
            on_date = datetime.strptime(raw, "%Y-%m-%d").date() if raw else timezone.localdate()
        except ValueError as exc:
            raise BusinessRuleViolation("`date` formati: 2026-07-24") from exc

        user = request_user(request)
        return Response(
            services.daily_cash_summary(
                organization_id=user.organization_id,
                on_date=on_date,
                branch_id=user.branch_id,
            )
        )


class DebtorViewSet(viewsets.ViewSet):
    """
    Qarzdorlar — **hisoblangan ro'yxat**, jadval emas (ADR-7).

    `ViewSet` (model emas): ortida hech qanday `debtor` jadvali yo'q va
    bo'lmasligi kerak. Ro'yxat har safar ledger'dan hisoblanadi, shuning
    uchun u haqiqatdan hech qachon ajralmaydi.
    """

    permission_classes = [HasModulePermission, SubscriptionWriteGate]
    permission_module = "debtors"

    def list(self, request: Request) -> Response:
        from decimal import Decimal as D

        raw_min = request.query_params.get("min_amount")
        min_amount = D(raw_min) if raw_min else None
        overdue_only = request.query_params.get("overdue") == "true"

        rows = selectors.debtor_rows(min_amount=min_amount, overdue_only=overdue_only)
        total = sum(D(row["balance"]) for row in rows)
        return Response({"count": len(rows), "total_debt": str(total), "results": rows})

    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        """
        Qarzdor tafsiloti — to'liq moliyaviy ko'chirma bilan.

        Topilmagan bola `404` beradi, `422` emas. Farqi muhim: qolgan
        HAMMA endpoint begona tashkilot qatoriga `404` qaytaradi
        (docs/04 §2), va bitta endpoint boshqacha javob berishi
        skanerlaydigan odamga aynan shu endpoint boshqacha ishlashini
        aytib qo'yadi.
        """
        from apps.children.models import Child

        # Buzuq UUID ham `404` beradi, `500` emas.
        #
        # Bu `ViewSet` (ADR-7: ortida jadval yo'q), ya'ni DRF'ning
        # `get_object()` va uning UUID tekshiruvi bu yerda ishlamaydi —
        # `filter(pk="not-a-uuid")` esa `ValidationError` ko'taradi va
        # `500` bo'lib chiqadi. Qolgan HAMMA endpoint bunday holatda
        # `404` qaytaradi, va bitta endpointning boshqacha javob
        # berishi skanerlaydigan odamga aynan shu yerda kutilmagan
        # narsa borligini aytib qo'yadi.
        try:
            child_id = uuid.UUID(str(pk))
        except (TypeError, ValueError) as exc:
            raise Http404 from exc

        # `Child.objects` tenant bilan cheklangan — begona bola bu yerda
        # umuman mavjud emas.
        child = Child.objects.filter(pk=child_id).first()
        if child is None:
            raise Http404
        return Response(selectors.child_statement(child=child))
