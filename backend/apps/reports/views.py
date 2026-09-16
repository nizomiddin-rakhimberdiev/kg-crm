"""
Hisobot va dashboard endpointlari (docs/04 §14).

Hammasi faqat o'qish. Eksport esa yozadi — lekin u ham hisobotning o'zini
o'zgartirmaydi, faqat ish yozuvini yaratadi.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from django.db import transaction
from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.core.exceptions import BusinessRuleViolation
from apps.core.permissions import HasModulePermission
from apps.core.typing import request_user
from apps.reports import selectors, services
from apps.reports.models import REPORT_TYPES, ExportStatus, ReportExport
from apps.reports.serializers import ExportRequestSerializer, ReportExportSerializer
from apps.reports.tasks import generate_export
from apps.subscriptions.permissions import SubscriptionWriteGate

__all__ = ["DashboardViewSet", "ReportViewSet"]


def _parse_date(value: Any, fallback: date) -> date:
    if not value:
        return fallback
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise BusinessRuleViolation(f"Sana formati noto'g'ri: {value}") from exc


def _parse_int(value: Any, fallback: int, *, low: int, high: int) -> int:
    if value in (None, ""):
        return fallback
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise BusinessRuleViolation(f"Butun son kutilgan: {value}") from exc
    if not low <= parsed <= high:
        raise BusinessRuleViolation(f"Qiymat {low}–{high} oralig'ida bo'lishi kerak: {parsed}")
    return parsed


class _ScopeMixin:
    """
    So'rovdagi davr va filialni o'qiydi.

    Filial ID'si tekshirilmaydi va tekshirilishi SHART EMAS: har bir
    so'rov allaqachon tashkilot bilan cheklangan, shuning uchun begona
    filial ID'si bo'sh natija beradi, boshqa tashkilotning ma'lumotini
    emas.
    """

    def scope(self, request: Request) -> dict[str, Any]:
        today = timezone.localdate()
        default_from = today.replace(day=1) - timedelta(days=180)
        return {
            "organization_id": request_user(request).organization_id,
            "date_from": _parse_date(request.query_params.get("from"), default_from),
            "date_to": _parse_date(request.query_params.get("to"), today),
            "branch_id": request.query_params.get("branch") or None,
        }


class DashboardViewSet(_ScopeMixin, viewsets.ViewSet):
    """`GET /dashboard` — bitta ekranga sig'adigan KPI to'plami."""

    permission_classes = [HasModulePermission, SubscriptionWriteGate]
    permission_module = "dashboard"

    def list(self, request: Request) -> Response:
        user = request_user(request)
        # Filial doirasi ROLGA bog'liq: Org Owner butun tashkilotni
        # ko'radi, qolganlar o'z filialini (docs/02 §11.3).
        branch_id = request.query_params.get("branch") or (
            user.branch_id if not user.is_org_owner else None
        )
        return Response(
            services.dashboard_kpis(organization_id=user.organization_id, branch_id=branch_id)
        )


class ReportViewSet(_ScopeMixin, viewsets.ViewSet):
    """`/reports/*` — agregatsiyalar va eksport."""

    permission_classes = [HasModulePermission, SubscriptionWriteGate]
    permission_module = "reports"
    permission_action_map = {
        "export": "export",
        "exports": "read",
        "export_detail": "read",
        "download": "read",
    }
    lookup_value_regex = "|".join(REPORT_TYPES)
    # `ScopedRateThrottle` shu nomdagi tezlikni qidiradi. U faqat
    # `export` action'iga ulangan (pastda), shuning uchun o'qish
    # endpointlariga ta'sir qilmaydi.
    throttle_scope = "export"

    @action(detail=False)
    def revenue(self, request: Request) -> Response:
        return Response(selectors.revenue_report(**self.scope(request)))

    @action(detail=False)
    def expenses(self, request: Request) -> Response:
        return Response(selectors.expense_report(**self.scope(request)))

    @action(detail=False, url_path="profit-loss")
    def profit_loss(self, request: Request) -> Response:
        return Response(selectors.profit_loss(**self.scope(request)))

    @action(detail=False)
    def debtors(self, request: Request) -> Response:
        scope = self.scope(request)
        return Response(
            selectors.debtor_report(
                organization_id=scope["organization_id"], branch_id=scope["branch_id"]
            )
        )

    @action(detail=False)
    def payroll(self, request: Request) -> Response:
        today = timezone.localdate()
        scope = self.scope(request)
        return Response(
            selectors.payroll_report(
                organization_id=scope["organization_id"],
                year=_parse_int(request.query_params.get("year"), today.year, low=2000, high=2100),
                branch_id=scope["branch_id"],
            )
        )

    @action(detail=False)
    def attendance(self, request: Request) -> Response:
        today = timezone.localdate()
        scope = self.scope(request)
        return Response(
            selectors.attendance_report(
                organization_id=scope["organization_id"],
                year=_parse_int(request.query_params.get("year"), today.year, low=2000, high=2100),
                month=_parse_int(request.query_params.get("month"), today.month, low=1, high=12),
                group_id=request.query_params.get("group") or None,
            )
        )

    # --- Eksport ---

    @action(detail=True, methods=["post"], throttle_classes=[ScopedRateThrottle])
    def export(self, request: Request, pk: str | None = None) -> Response:
        """
        `POST /reports/{type}/export` — eksportni navbatga qo'yadi.

        Javob darhol qaytadi: katta hisobotni so'rov ichida tayyorlash
        brauzerni kutdirib qo'yardi va vaqt tugashi bilan uzilardi.
        """
        serializer = ExportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request_user(request)

        export = ReportExport.objects.create(
            organization=user.organization,
            report_type=pk,
            params=serializer.validated_data.get("params", {}),
            requested_by=user,
        )
        # `on_commit` — `delay()` EMAS, to'g'ridan-to'g'ri emas.
        #
        # `ATOMIC_REQUESTS` yoqilmagan bo'lsa ham, bu view yuqoridagi
        # qatlamlarda tranzaksiya ichiga tushishi mumkin (masalan test,
        # yoki kelajakdagi `atomic` blok). U holda vazifa qatordan
        # OLDIN navbatga tushadi va ishchi hali mavjud bo'lmagan
        # `export.id` ni qidiradi — natija "eksport topilmadi" degan
        # jimgina nosozlik bo'lardi.
        #
        # `on_commit` vazifani commit'dan KEYIN yuboradi; tranzaksiya
        # bo'lmasa esa darhol chaqiradi, ya'ni oddiy holatda xatti-harakat
        # o'zgarmaydi.
        export_id, organization_id = str(export.id), str(user.organization_id)
        transaction.on_commit(lambda: generate_export.delay(export_id, organization_id))
        return Response(ReportExportSerializer(export).data, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=["get"])
    def exports(self, request: Request) -> Response:
        queryset = ReportExport.objects.select_related("requested_by").order_by("-created_at")[:50]
        return Response(ReportExportSerializer(queryset, many=True).data)

    @action(detail=False, methods=["get"], url_path=r"exports/(?P<job_id>[0-9a-f-]{36})")
    def export_detail(self, request: Request, job_id: str = "") -> Response:
        return Response(ReportExportSerializer(self._get_export(job_id)).data)

    @action(
        detail=False,
        methods=["get"],
        url_path=r"exports/(?P<job_id>[0-9a-f-]{36})/download",
    )
    def download(self, request: Request, job_id: str = "") -> FileResponse:
        """
        Faylni **shu endpoint** beradi, `/media/` havolasi emas.

        Statik media URL'i autentifikatsiyani ham, tashkilot chegarasini
        ham bilmaydi: havolani topgan har kim boshqa bog'chaning moliyaviy
        hisobotini yuklab olardi. Bu yerda esa `ReportExport.objects`
        tenant bilan cheklangan, ya'ni begona ish oddiygina `404`.
        """
        export = self._get_export(job_id)
        if export.status != ExportStatus.READY or not export.file:
            raise BusinessRuleViolation("Eksport hali tayyor emas.")
        return FileResponse(
            export.file.open("rb"),
            as_attachment=True,
            filename=export.file.name.rsplit("/", 1)[-1],
            content_type="text/csv",
        )

    def _get_export(self, job_id: str) -> ReportExport:
        export = ReportExport.objects.filter(pk=job_id).first()
        if export is None:
            raise Http404
        return export
