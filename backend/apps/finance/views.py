"""Moliya endpointlari (docs/04 §9)."""

from __future__ import annotations

import calendar
import uuid
from datetime import date
from decimal import Decimal
from typing import Any

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
from apps.finance.serializers import (
    DiscountSerializer,
    GenerateInvoicesSerializer,
    InvoiceSerializer,
    LedgerEntrySerializer,
    PaymentBatchSerializer,
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
        return Response(
            selectors.month_board_summary(
                organization_id=user.organization_id,
                period_year=year,
                period_month=month,
                branch_id=self._branch_scope(request, user),
            )
        )

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
            received_by=params.get("received_by") or None,
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
