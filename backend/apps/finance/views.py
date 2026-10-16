"""Moliya endpointlari (docs/04 §9)."""

from __future__ import annotations

import calendar
import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from django.db.models import Q
from django.http import Http404
from django.utils import timezone
from django.utils.translation import gettext
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response

from apps.audit import services as audit
from apps.branches.selectors import resolve_branch
from apps.core.exceptions import BusinessRuleViolation
from apps.core.permissions import HasModulePermission
from apps.core.typing import request_user
from apps.core.viewsets import BranchScopedMixin, TenantReadOnlyViewSet, TenantViewSet
from apps.finance import balance, selectors, services
from apps.finance.models import ChildLedgerEntry, Discount, Invoice, Payment, TariffPlan
from apps.finance.scope import payments_own_only, restrict_payments
from apps.finance.serializers import (
    DiscountSerializer,
    GenerateInvoicesSerializer,
    InvoiceSerializer,
    LedgerEntrySerializer,
    PaymentBatchSerializer,
    PaymentDetailSerializer,
    PaymentSerializer,
    PaymentWriteSerializer,
    TariffPlanSerializer,
)
from apps.settings_app.services import get_setting
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

    def get_base_queryset(self) -> Any:
        # O'chirilgan tarif `is_active=False` bo'lib qoladi — u eski
        # hisob-fakturalar va bolalar tarixida kerak. Lekin ro'yxatda,
        # tahrirlashda va qayta o'chirishda u YO'Q: ilgari ro'yxat uni
        # ham qaytarardi va mijoz "o'chirish ishlamayapti" deb ko'rdi
        # (2026-10-14) — tugma ishlagan, karta esa joyida qolgan edi.
        return super().get_base_queryset().filter(is_active=True)

    def perform_create(self, serializer: Any) -> None:
        user = request_user(self.request)
        branch = resolve_branch(user, self.request.data.get("branch_id"))
        serializer.save(organization=user.organization, branch=branch)

    def perform_destroy(self, instance: TariffPlan) -> None:
        if instance.children.filter(is_active=True).exists():
            raise BusinessRuleViolation(
                gettext(
                    "Bu tarifga biriktirilgan bolalar bor — avval ularni boshqa tarifga oʻtkazing."
                )
            )
        instance.is_active = False
        instance.save(update_fields=["is_active"])


class DiscountViewSet(BranchScopedMixin, TenantViewSet):
    permission_module = "payments"
    model = Discount
    serializer_class = DiscountSerializer
    select_related_fields = ("child",)
    filterset_fields = ["child", "discount_type", "kind"]
    # Joyida tahrirlash va o'chirish YO'Q (Bosqich 12.2): o'zgarish — eskisini
    # `end` bilan tugatish va yangisini yozish, shunda tarix o'zi saqlanadi.
    http_method_names = ["get", "post", "head", "options"]
    permission_action_map = {"end": "update"}

    def perform_create(self, serializer: Any) -> None:
        data = serializer.validated_data
        child = data["child"]
        start, end = data["valid_from"], data.get("valid_to")
        overlapping = Discount.objects.filter(child=child, is_active=True).filter(
            Q(valid_to__isnull=True) | Q(valid_to__gte=start)
        )
        if end is not None:
            overlapping = overlapping.filter(valid_from__lte=end)
        if overlapping.exists():
            raise BusinessRuleViolation(
                gettext(
                    "Bu davrda bolada boshqa imtiyoz bor — avval uni tugating, keyin yangisini "
                    "kiriting."
                )
            )
        user = request_user(self.request)
        serializer.save(organization=child.organization, branch=child.branch, created_by=user)
        # Katta imtiyoz — egaga darhol (Bosqich 13.4).
        from apps.intelligence import alerts

        discount = serializer.instance
        kind_type, value = (
            services.benefit_terms(discount.kind, discount.branch)
            if (discount.kind and discount.kind != "custom")
            else (discount.discount_type, discount.value)
        )
        alerts.benefit_given(
            discount,
            Decimal(value) if kind_type == "percent" else None,
            Decimal(value) if kind_type != "percent" else None,
        )
        audit.record(
            action="create",
            request=self.request._request,
            actor=user,
            entity_type="discount",
            entity_id=serializer.instance.id,
            changes={
                "child": child.full_name,
                "kind": serializer.instance.kind,
                "reason": serializer.instance.reason,
                "from": str(start),
                "to": str(end) if end else None,
            },
        )

    @action(detail=True, methods=["post"])
    def end(self, request: Request, pk: str | None = None) -> Response:
        """`POST /discounts/{id}/end {valid_to}` — imtiyozni tugatadi, o'chirmaydi."""
        discount = self.get_object()
        raw = request.data.get("valid_to")
        try:
            valid_to = date.fromisoformat(str(raw))
        except ValueError as exc:
            raise BusinessRuleViolation(gettext("Tugash sanasini kiriting.")) from exc
        if valid_to < discount.valid_from:
            raise BusinessRuleViolation(
                gettext("Tugash sanasi boshlanishdan oldin boʻlishi mumkin emas.")
            )
        before = discount.valid_to
        discount.valid_to = valid_to
        discount.save(update_fields=["valid_to", "updated_at"])
        audit.record(
            action="update",
            request=request._request,
            actor=request_user(request),
            entity_type="discount",
            entity_id=discount.id,
            changes={"valid_to": [str(before) if before else None, str(valid_to)]},
        )
        return Response(DiscountSerializer(discount).data)


class InvoiceViewSet(BranchScopedMixin, TenantReadOnlyViewSet):
    """
    Hisob-fakturalar — faqat o'qish + aniq amallar.

    `PATCH`/`DELETE` ataylab yo'q: hisob-faktura ledger yozuvini yaratgan
    hujjat. Uni tahrirlash ledger bilan hujjatni bir-biridan ajratib
    yuborardi. O'zgartirish kerak bo'lsa — bekor qilib, yangisini chiqarish
    (D3, docs/03 §13.3).
    """

    permission_module = "payments"
    permission_action_map = {"generate": "create", "preview_run": "create", "cancel": "update"}
    model = Invoice
    serializer_class = InvoiceSerializer
    select_related_fields = ("child", "tariff")
    filterset_fields = ["status", "period_year", "period_month", "child"]
    ordering_fields = ["issued_date", "due_date", "amount_due"]
    search_fields = ["number", "child__first_name", "child__last_name"]

    def get_base_queryset(self) -> Any:
        return super().get_base_queryset().prefetch_related("lines")

    @action(detail=False, methods=["post"], url_path="preview-run")
    def preview_run(self, request: Request) -> Response:
        """
        `POST /invoices/preview-run` — generatsiya nima qilishini oldindan aytadi.

        Hech narsa yozmaydi. 200 bolali bog'chada "Hisob-faktura
        chiqarish" bitta bosishda 200 ta moliyaviy hujjat yaratadi va
        ularni qaytarish uchun har birini alohida bekor qilish kerak —
        shuning uchun avval ro'yxat ko'rsatiladi (PLAN 1.4).
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

        preview = services.preview_monthly_invoices(
            organization=user.organization,
            branch=branch,
            period_year=data["period_year"],
            period_month=data["period_month"],
        )
        return Response(preview.as_dict(), status=status.HTTP_200_OK)

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
        """
        `GET /ledger/balance?child=<uuid>` — bolaning to'liq moliyaviy manzarasi.

        Qaytaradi: balans, avans, muddati o'tgan qarz va ochiq hujjatlar
        (FIFO tartibida). Kassir oynasi ham, bola kartasi ham shu bitta
        manbadan o'qiydi — ikki ekran ikki xil raqam ko'rsatmasligi uchun
        (`docs/big-update/PLAN.md` §2).
        """
        child_id = request.query_params.get("child")
        if not child_id:
            raise BusinessRuleViolation(gettext("`child` parametri majburiy."))

        from apps.children.models import Child

        # `Child.objects` tenant bilan cheklangan — begona bola "topilmadi".
        # `404`, `422` EMAS (invariant 2): boshqa tenantning qatoriga
        # urinish "mavjud emas" deb javob oladi, biznes qoidasi xatosi
        # emas. Yakuniy qabul ssenariysi (9-qadam) topdi.
        child = Child.objects.filter(pk=child_id).first()
        if child is None:
            raise NotFound(gettext("Bola topilmadi."))

        detail = balance.child_balance(child)
        # Ochiq hujjatlar FIFO tartibida — kassir ekranidagi taqsimot
        # ko'rinishi aynan shu ro'yxat bo'yicha chiziladi, ya'ni ekranda
        # ko'rsatilgan taqsimot serverdagisi bilan bir xil bo'ladi.
        open_invoices = [
            {
                "id": str(invoice.id),
                "number": invoice.number,
                "period": f"{invoice.period_year}-{invoice.period_month:02d}",
                "due_date": invoice.due_date.isoformat(),
                "amount_due": f"{invoice.amount_due:.2f}",
                "amount_paid": f"{invoice.amount_paid:.2f}",
                "outstanding": f"{invoice.amount_outstanding:.2f}",
                "is_overdue": invoice.due_date < timezone.localdate(),
            }
            for invoice in services.open_invoices(child)
        ]

        return Response(
            {
                **detail.as_dict(),
                "full_name": child.full_name,
                # Keshdan EMAS, ledger'dan hisoblangan (D3).
                "balance": str(services.child_balance(child.id)),
                "cached_balance": str(child.balance),
                "open_invoices": open_invoices,
                # Qaysi oylar uchun qancha (Bosqich 12.3).
                "months": balance.open_months(child),
                # Shundan eski sana — sabab bilan (Bosqich 12.4). Kassir
                # oynasi maydonni oldindan ko'rsatsin, server rad etgach emas.
                "backdate_days": int(get_setting(key="finance.backdate_days") or 0),
                # Kim to'lashi mumkin — kassir oynasidagi "to'lovchi"
                # tanlovi uchun (Bosqich 12.4).
                "guardians": [
                    {
                        "id": str(link.guardian_id),
                        "full_name": link.guardian.full_name,
                        "relation": link.relation,
                        "is_primary": link.is_primary,
                    }
                    for link in child.guardian_links.select_related("guardian").order_by(
                        "-is_primary", "created_at"
                    )
                ],
            }
        )


class PaymentViewSet(BranchScopedMixin, TenantViewSet):
    """
    To'lovlar (docs/04 §9.3).

    `PATCH`/`DELETE` yo'q: to'lov o'zgarmas. Tuzatish `POST /{id}/reverse`
    orqali qarshi yozuv bilan qilinadi (D3).
    """

    permission_module = "payments"
    permission_action_map = {
        "reverse": "update",
        "refund": "update",
        "in_transit": "read",
        "settle": "update",
        "daily_summary": "read",
        "batch": "create",
        "board": "read",
        "board_summary": "read",
        "journal_summary": "read",
        "receipt": "read",
    }
    model = Payment
    select_related_fields = ("child", "invoice")
    # Jurnal filtri (PLAN 1.8): sana oralig'i, usul, bola, kassir.
    filterset_fields = {
        "child": ["exact"],
        "invoice": ["exact"],
        "method": ["exact"],
        "received_by": ["exact"],
        "paid_at": ["date__gte", "date__lte"],
    }
    ordering_fields = ["paid_at", "amount"]
    http_method_names = ["get", "post", "head", "options"]

    def get_serializer_class(self) -> Any:
        if self.request.method not in ("GET", "HEAD"):
            return PaymentWriteSerializer
        # Bitta to'lov — pul qaysi oylarga ketgani bilan (Bosqich 12.4).
        return PaymentDetailSerializer if self.action == "retrieve" else PaymentSerializer

    def get_base_queryset(self) -> Any:
        # Ro'yxat, bitta to'lov, kvitansiya va qaytarish — hammasi shu
        # yerdan o'tadi, ya'ni boshqa kassirning to'lovi `404` beradi
        # (`403` emas: u mavjudligini ham bilmasligi kerak).
        return restrict_payments(super().get_base_queryset(), request_user(self.request))

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
            payer=data.get("payer"),
            employee=data.get("employee"),
            backdate_reason=data.get("backdate_reason", ""),
            allocation_reason=data.get("allocation_reason", ""),
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

    @staticmethod
    def _period(request: Request) -> tuple[int, int]:
        """`?period_year=&period_month=` — berilmasa joriy oy."""
        today = timezone.localdate()
        try:
            year = int(request.query_params.get("period_year") or today.year)
            month = int(request.query_params.get("period_month") or today.month)
        except ValueError as exc:
            raise BusinessRuleViolation(
                gettext("`period_year` va `period_month` butun son boʻlishi kerak.")
            ) from exc
        if not 1 <= month <= 12:
            raise BusinessRuleViolation(gettext("Oy 1–12 oraligʻida boʻlishi kerak."))
        return year, month

    @staticmethod
    def _branch_scope(request: Request, user: Any) -> Any:
        """
        Filial doirasi ROLGA bog'liq (docs/02 §11.3).

        Org Owner butun tashkilotni ko'radi, qolganlar o'z filialini.
        Begona filial ID'si bo'sh natija beradi — tashkilot chegarasi
        allaqachon so'rovda.
        """
        return request.query_params.get("branch") or (None if user.is_org_owner else user.branch_id)

    @action(detail=False, methods=["get"])
    def board(self, request: Request) -> Response:
        """
        `GET /payments/board?period_year=&period_month=&search=&status=`

        Kassirning ekrani: shu oyda qaysi bola qancha to'lashi kerak.

        Manba — BOLALAR ro'yxati, hisob-faktura unga chap tomondan
        qo'shiladi (docs/04 §9.7). Hisob-fakturalar ro'yxatiga tayanish
        ikki sababdan noto'g'ri edi: faktura chiqarilmagan bola umuman
        ko'rinmasdi, va ro'yxat sahifalanar — 41 bolali bog'chada 16
        bola ekranga chiqmasdi.
        """
        user = request_user(request)
        year, month = self._period(request)
        queryset = selectors.month_board_queryset(
            organization_id=user.organization_id,
            period_year=year,
            period_month=month,
            branch_id=self._branch_scope(request, user),
            search=(request.query_params.get("search") or "").strip(),
            status=(request.query_params.get("status") or "").strip(),
        )
        page = self.paginate_queryset(queryset)
        rows = [selectors.board_row(child) for child in (page if page is not None else queryset)]
        if page is not None:
            return self.get_paginated_response(rows)
        return Response(rows)

    @action(detail=False, methods=["get"], url_path="board-summary")
    def board_summary(self, request: Request) -> Response:
        """
        `GET /payments/board-summary` — oyning yakuni, SAHIFADAN qat'i nazar.

        Ilgari yuqoridagi "jami" faqat yuklangan qatorlardan
        hisoblanardi, ya'ni har doim kam ko'rsatardi.
        """
        user = request_user(request)
        year, month = self._period(request)
        summary = selectors.month_board_summary(
            organization_id=user.organization_id,
            period_year=year,
            period_month=month,
            branch_id=self._branch_scope(request, user),
        )
        if payments_own_only(user):
            # Doska kassirning ishi, oyning umumiy tushumi esa yo'q
            # (ADR-30). Kalitlar QOLADI, qiymat `null` — ekran "bu raqam
            # sizga ko'rsatilmaydi" ni "yuklanmadi" dan ajrata oladi.
            summary.update(charged=None, paid=None, outstanding=None)
        return Response(summary)

    @action(detail=False, methods=["post"])
    def batch(self, request: Request) -> Response:
        """
        `POST /payments/batch` — bitta harakatda bir nechta usul.

        Ortiqcha summa RAD ETILMAYDI: hisob-faktura to'lgach qolgani
        avans bo'lib yoziladi (docs/03 §13.5a).
        """
        serializer = PaymentBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request_user(request)

        payments = services.record_payment_batch(
            child=data["child"],
            lines=data["lines"],
            invoice=data.get("invoice"),
            paid_at=data.get("paid_at"),
            received_by=user,
            idempotency_key=request.headers.get("Idempotency-Key", "").strip(),
            payer=data.get("payer"),
            backdate_reason=data.get("backdate_reason", ""),
            allocation_reason=data.get("allocation_reason", ""),
        )
        for payment in payments:
            audit.record(
                action="create",
                request=request._request,
                actor=user,
                entity_type="payment",
                entity_id=payment.id,
                changes={
                    "amount": str(payment.amount),
                    "method": payment.method,
                    "batch": str(payment.batch_id),
                },
            )
        return Response(PaymentSerializer(payments, many=True).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def receipt(self, request: Request, pk: str | None = None) -> Response:
        """
        `GET /payments/{id}/receipt` — kvitansiya ma'lumoti (PLAN 1.7).

        Bitta KASSIR HARAKATI bo'yicha: bir necha usul bilan to'langan
        pul bitta kvitansiyaga tushadi, chunki ota-ona uchun bu bitta
        hodisa. Jurnaldan qayta chop etilganda raqam ham, mazmun ham
        o'sha bo'ladi.
        """
        return Response(services.receipt_for(self.get_object()))

    @action(detail=False, methods=["get"], url_path="in-transit")
    def in_transit(self, request: Request) -> Response:
        """
        `GET /payments/in-transit` — bankka hali tushmagan terminal/Click/Payme
        pullari (Bosqich 13.2c). Kassir faqat o'zi qabul qilganlarini ko'radi.
        """
        user = request_user(request)
        branch = request.query_params.get("branch") or None
        items = selectors.in_transit(
            organization_id=user.organization_id,
            branch_id=branch if user.is_org_owner else user.branch_id,
            received_by_id=user.id if payments_own_only(user) else None,
        )
        total = sum((Decimal(row["expected_amount"]) for row in items), Decimal("0"))
        return Response(
            {
                "items": items,
                "expected_total": f"{total:.2f}",
                "overdue_count": sum(1 for row in items if row["overdue"]),
            }
        )

    @action(detail=False, methods=["post"])
    def settle(self, request: Request) -> Response:
        """
        `POST /payments/settle {payment_ids, settled_on, reference?}` — bank
        tushumini tasdiqlash. Bank ko'chirmasi importi (13.3) ham shu servisni
        chaqiradi.
        """
        from datetime import date as date_type

        from rest_framework.exceptions import PermissionDenied

        user = request_user(request)
        if payments_own_only(user):
            raise PermissionDenied(gettext("Bu amalga ruxsat yoʻq."))
        ids = request.data.get("payment_ids") or []
        if not isinstance(ids, list):
            raise BusinessRuleViolation(gettext("`payment_ids` roʻyxat boʻlishi kerak."))
        payments = list(Payment.objects.filter(pk__in=ids).select_related("child"))
        if len(payments) != len(set(ids)):
            raise NotFound(gettext("Toʻlov topilmadi."))
        raw_day = request.data.get("settled_on")
        try:
            settled_on = date_type.fromisoformat(str(raw_day)) if raw_day else timezone.localdate()
        except ValueError as exc:
            raise BusinessRuleViolation(gettext("Sana YYYY-MM-DD koʻrinishida boʻlsin.")) from exc
        total = services.settle_payments(
            payments=payments,
            settled_on=settled_on,
            reference=str(request.data.get("reference", "")),
            created_by=user,
        )
        audit.record(
            action="update",
            request=request._request,
            actor=user,
            entity_type="payment_settlement",
            changes={"payments": [str(p.id) for p in payments], "total": str(total)},
        )
        return Response(
            {"count": len(payments), "expected_total": f"{total:.2f}"},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def refund(self, request: Request, pk: str | None = None) -> Response:
        """
        `POST /payments/{id}/refund {amount, cash_account_id, reason}` — avansni
        ota-onaga qaytarish (Bosqich 13.2b). Pul qopdan chiqadi, shuning uchun
        "faqat o'ziniki" kassirga yopiq.
        """
        from rest_framework.exceptions import PermissionDenied

        from apps.cash.models import CashAccount

        user = request_user(request)
        if payments_own_only(user):
            raise PermissionDenied(gettext("Bu amalga ruxsat yoʻq."))
        payment = self.get_object()
        account = CashAccount.objects.filter(pk=request.data.get("cash_account_id")).first()
        if account is None:
            raise BusinessRuleViolation(gettext("Pul qaysi qopdan qaytarilishini tanlang."))
        try:
            amount = Decimal(str(request.data.get("amount", "")))
        except ArithmeticError as exc:
            raise BusinessRuleViolation(gettext("Summa raqam boʻlishi kerak.")) from exc
        refund = services.refund_payment(
            payment=payment,
            amount=amount,
            account=account,
            reason=str(request.data.get("reason", "")),
            created_by=user,
            allow_negative=str(request.data.get("allow_negative", "")).lower() == "true",
        )
        audit.record(
            action="create",
            request=request._request,
            actor=user,
            entity_type="refund",
            entity_id=refund.id,
            changes={"payment": str(payment.id), "amount": str(refund.amount)},
        )
        return Response(
            {"id": str(refund.id), "amount": f"{refund.amount:.2f}"},
            status=status.HTTP_201_CREATED,
        )

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

    @action(detail=False, methods=["get"], url_path="journal-summary")
    def journal_summary(self, request: Request) -> Response:
        """
        `GET /payments/journal-summary` — jurnalning YIG'INDISI (PLAN 1.8).

        Ro'yxat sahifalanadi, yig'indi esa sahifaga bog'liq bo'lmasligi
        kerak: "1–25 / 105" ostida turgan "jami" faqat 25 qatordan
        hisoblansa, u har doim kam ko'rsatadi.
        """
        from apps.reports.selectors import payment_journal_summary

        user = request_user(request)
        today = timezone.localdate()
        params = request.query_params
        date_from = params.get("paid_from")
        date_to = params.get("paid_to")

        summary = payment_journal_summary(
            organization_id=user.organization_id,
            date_from=date.fromisoformat(date_from) if date_from else today.replace(day=1),
            date_to=date.fromisoformat(date_to) if date_to else today,
            branch_id=self._branch_scope(request, user),
            method=params.get("method") or "",
            child_id=params.get("child") or None,
            # Cheklangan foydalanuvchi boshqa kassirni so'rab doirani
            # kengaytira olmaydi — filtr uning o'ziga qotiriladi.
            received_by=(user.id if payments_own_only(user) else params.get("received_by") or None),
        )
        return Response(summary)

    @action(detail=False, methods=["get"], url_path="daily-summary")
    def daily_summary(self, request: Request) -> Response:
        """`GET /payments/daily-summary?date=` — kassirning kunlik hisoboti."""
        from datetime import datetime

        raw = request.query_params.get("date")
        try:
            on_date = datetime.strptime(raw, "%Y-%m-%d").date() if raw else timezone.localdate()
        except ValueError as exc:
            raise BusinessRuleViolation(gettext("`date` formati: 2026-07-24")) from exc

        user = request_user(request)
        return Response(
            services.daily_cash_summary(
                organization_id=user.organization_id,
                on_date=on_date,
                branch_id=user.branch_id,
                received_by_id=user.id if payments_own_only(user) else None,
            )
        )


def _parse_period(value: str) -> tuple[int, int]:
    """`"2026-09"` → `(2026, 9)`. Buzuq qiymat — `422`, `500` emas."""
    try:
        year, month = value.split("-")
        year_int, month_int = int(year), int(month)
    except (ValueError, AttributeError) as exc:
        raise BusinessRuleViolation(gettext("Davr «YYYY-MM» koʻrinishida boʻlishi kerak.")) from exc
    if not 1 <= month_int <= 12 or not 2000 <= year_int <= 2100:
        raise BusinessRuleViolation(gettext("Davr «YYYY-MM» koʻrinishida boʻlishi kerak."))
    return year_int, month_int


def _period_start(value: str | None, *, default: date) -> date:
    if not value:
        return default
    year, month = _parse_period(value)
    return date(year, month, 1)


def _period_end(value: str | None, *, default: date) -> date:
    if not value:
        return default
    year, month = _parse_period(value)
    last = calendar.monthrange(year, month)[1]
    return date(year, month, last)


class DebtorViewSet(viewsets.ViewSet):
    """
    Qarzdorlar — **hisoblangan ro'yxat**, jadval emas (ADR-7).

    `ViewSet` (model emas): ortida hech qanday `debtor` jadvali yo'q va
    bo'lmasligi kerak. Ro'yxat har safar ledger'dan hisoblanadi, shuning
    uchun u haqiqatdan hech qachon ajralmaydi.
    """

    permission_classes = [HasModulePermission, SubscriptionWriteGate]
    permission_module = "debtors"
    # Qarzni kechirish — `debtors.approve` (egasi, direktor). Kassirda
    # `debtors` bor, lekin `approve` yo'q: qarzni kechirish uning ishi emas.
    permission_action_map = {"write_off": "approve"}

    @action(detail=False, methods=["post"], url_path="write-off")
    def write_off(self, request: Request) -> Response:
        """
        `POST /debtors/write-off {invoice_id, amount, reason}` (Bosqich 12.3).

        Qarzni qo'lda 0 qilishning o'rniga — hujjat: summa, sabab, kim.
        """
        from apps.finance.serializers import InvoiceWriteOffSerializer

        invoice = Invoice.objects.filter(pk=request.data.get("invoice_id")).first()
        if invoice is None:
            raise Http404
        user = request_user(request)
        try:
            amount = Decimal(str(request.data.get("amount")))
        except (ArithmeticError, ValueError) as exc:
            raise BusinessRuleViolation(gettext("Summani kiriting.")) from exc
        record = services.write_off_invoice(
            invoice=invoice,
            amount=amount,
            reason=str(request.data.get("reason") or ""),
            created_by=user,
        )
        audit.record(
            action="create",
            request=request._request,
            actor=user,
            entity_type="invoice_write_off",
            entity_id=record.id,
            changes={
                "invoice": invoice.number,
                "amount": str(record.amount),
                "reason": record.reason,
            },
        )
        return Response(InvoiceWriteOffSerializer(record).data, status=status.HTTP_201_CREATED)

    def list(self, request: Request) -> Response:
        from decimal import Decimal as D

        from apps.core.params import parse_bool, parse_decimal, parse_int, parse_uuid

        params = request.query_params
        order_by = params.get("order_by") or "debt"
        if order_by not in ("debt", "days", "name"):
            order_by = "debt"

        rows = selectors.debtor_rows(
            min_amount=parse_decimal(params.get("min_amount"), field=gettext("Summa")),
            overdue_only=parse_bool(params.get("overdue")),
            # "15+ / 30+ / 60+ kun" filtrlari (PLAN 3.5).
            min_days=parse_int(params.get("min_days"), field=gettext("Kunlar")),
            group_id=parse_uuid(params.get("group_id")),
            order_by=order_by,
        )
        total = sum(D(row["balance"]) for row in rows)
        return Response({"count": len(rows), "total_debt": str(total), "results": rows})

    @action(detail=False, methods=["get"], url_path="by-period")
    def by_period(self, request: Request) -> Response:
        """
        Oy boʻyicha qarzdorlik yoshi (PLAN 9.2).

        `?from=2026-09&to=2026-10` — davr; `period=2026-09` berilsa,
        oʻsha oyning tafsiloti (kim, qancha, qachon, nima orqali).
        Ikkalasi bitta endpointda, chunki ekranda ham bitta jadval:
        qatorni ochganda ichidagi roʻyxat chiqadi.
        """
        from apps.core.params import parse_bool, parse_uuid

        params = request.query_params
        group_id = parse_uuid(params.get("group_id"))
        branch_id = parse_uuid(params.get("branch_id"))

        period = params.get("period")
        if period:
            year, month = _parse_period(period)
            rows = selectors.debt_period_children(
                period_year=year,
                period_month=month,
                branch_id=branch_id,
                group_id=group_id,
                debtors_only=parse_bool(params.get("debtors_only")),
            )
            return Response({"period": period, "count": len(rows), "results": rows})

        today = timezone.localdate()
        date_from = _period_start(params.get("from"), default=today.replace(day=1, month=1))
        date_to = _period_end(params.get("to"), default=today)
        rows = selectors.debt_by_period(
            date_from=date_from, date_to=date_to, branch_id=branch_id, group_id=group_id
        )
        totals = {
            key: f"{sum(Decimal(row[key]) for row in rows):.2f}"
            for key in ("invoiced", "paid", "outstanding")
        }
        return Response({"count": len(rows), "totals": totals, "results": rows})

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
