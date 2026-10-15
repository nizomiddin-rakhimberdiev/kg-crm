"""Davomat endpointlari (docs/04 §8)."""

from __future__ import annotations

from datetime import datetime
from pathlib import PurePosixPath
from typing import Any

from django.db import transaction
from django.http import FileResponse, Http404
from django.utils.translation import gettext
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from apps.attendance import services
from apps.attendance import services_absence as absence
from apps.attendance.models import AttendanceRecord
from apps.attendance.models_absence import AbsenceClaim, AbsenceKind, Holiday
from apps.attendance.serializers import (
    AbsenceClaimSerializer,
    AbsenceClaimWriteSerializer,
    AbsenceKindSerializer,
    AttendanceRecordSerializer,
    AttendanceWriteSerializer,
    BulkAttendanceSerializer,
    HolidaySerializer,
)
from apps.audit import services as audit
from apps.children.models import Group
from apps.core.exceptions import BusinessRuleViolation
from apps.core.typing import request_user
from apps.core.viewsets import BranchScopedMixin, TenantViewSet

__all__ = ["AttendanceViewSet", "AbsenceClaimViewSet", "HolidayViewSet"]


def _parse_date(raw: str | None, field: str) -> Any:
    if not raw:
        raise BusinessRuleViolation(gettext("`{field}` parametri majburiy.").format(field=field))
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError as exc:
        raise BusinessRuleViolation(
            gettext("`{field}` formati notoʻgʻri (kutilgan: 2026-07-24).").format(field=field)
        ) from exc


def _resolve_group(group_id: str | None) -> Group:
    if not group_id:
        raise BusinessRuleViolation(gettext("`group` parametri majburiy."))
    # `Group.objects` tenant bilan cheklangan — begona guruh "topilmadi".
    group = Group.objects.filter(pk=group_id).first()
    if group is None:
        raise BusinessRuleViolation(gettext("Guruh topilmadi."))
    return group


class AttendanceViewSet(BranchScopedMixin, TenantViewSet):
    permission_module = "attendance"
    permission_action_map = {
        "bulk": "create",
        "daily": "read",
        "summary": "read",
    }
    model = AttendanceRecord
    select_related_fields = ("child", "group")
    filterset_fields = ["status", "attendance_date", "child", "group"]
    ordering_fields = ["attendance_date"]

    def get_serializer_class(self) -> Any:
        return (
            AttendanceRecordSerializer
            if self.request.method in ("GET", "HEAD")
            else AttendanceWriteSerializer
        )

    def perform_create(self, serializer: Any) -> None:
        user = request_user(self.request)
        child = serializer.validated_data["child"]
        serializer.save(
            organization=user.organization,
            branch=child.branch,
            recorded_by=user,
        )

    @action(detail=False, methods=["post"])
    def bulk(self, request: Request) -> Response:
        """Bir guruhning bir kunini bitta chaqiruvda belgilaydi."""
        serializer = BulkAttendanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = request_user(request)
        group = data["group"]
        records = services.mark_bulk(
            organization=user.organization,
            branch=group.branch,
            group=group,
            attendance_date=data["attendance_date"],
            records=data["records"],
            recorded_by=user,
            # Eski kunni o'zgartirish sababi (PLAN 2.6) — u auditga
            # tushadi, chunki o'tgan oyning davomati qayta hisobga va
            # hisobotga ta'sir qiladi.
            reason=str(request.data.get("reason", "")),
        )
        return Response(
            AttendanceRecordSerializer(records, many=True).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def daily(self, request: Request) -> Response:
        """
        `GET /attendance/daily?group=&date=` — kunlik jurnal.

        Belgilanmagan bolalar ham qaytadi (`status: null`), aks holda
        tarbiyachi kimni o'tkazib yuborganini ko'rmasdi.
        """
        group = _resolve_group(request.query_params.get("group"))
        target = _parse_date(request.query_params.get("date"), "date")
        return Response(
            {
                "group": {"id": str(group.id), "name": group.name},
                "date": target.isoformat(),
                "rows": services.daily_register(group=group, attendance_date=target),
            }
        )

    @action(detail=False, methods=["get"])
    def summary(self, request: Request) -> Response:
        """`GET /attendance/summary?month=2026-07&group=` — oylik yig'ma."""
        raw_month = request.query_params.get("month")
        if not raw_month:
            raise BusinessRuleViolation(gettext("`month` parametri majburiy (masalan 2026-07)."))
        try:
            year, month = (int(part) for part in raw_month.split("-", 1))
        except ValueError as exc:
            raise BusinessRuleViolation(gettext("`month` formati: 2026-07")) from exc

        group_id = request.query_params.get("group")
        group = _resolve_group(group_id) if group_id else None

        user = request_user(request)
        return Response(
            {
                "month": raw_month,
                "rows": services.monthly_summary(
                    organization_id=user.organization_id,
                    year=year,
                    month=month,
                    group=group,
                ),
            }
        )


class HolidayViewSet(TenantViewSet):
    """
    Bayram kalendari (ADR-19).

    Tashkilot darajasida: bayram milliy, va uch filialli tashkilotga
    uni uch marta yozdirish uchta har xil javob olish demak.
    """

    permission_module = "attendance"
    model = Holiday
    serializer_class = HolidaySerializer
    search_fields = ["name"]
    ordering_fields = ["holiday_date"]


class AbsenceClaimViewSet(BranchScopedMixin, TenantViewSet):
    """
    Hujjat bilan tasdiqlangan kelmaslik (docs/03 §12.2, ADR-19).

    `PATCH`/`DELETE` yo'q: da'vo tasdiqlangandan keyin u bergan raqam
    hisob-fakturaga tushadi, shuning uchun uni tahrirlash pul
    harakatini orqadan o'zgartirardi. Xato bo'lsa — rad etish yoki
    yangi da'vo.
    """

    permission_module = "attendance"
    permission_action_map = {"approve": "approve", "reject": "approve", "kinds": "read"}
    model = AbsenceClaim
    serializer_class = AbsenceClaimSerializer
    select_related_fields = ("child", "approved_by")
    #: Spravka/ariza 10 MB gacha — telefonda suratga olingan ikki
    #: betlik qog'oz shuncha chiqadi; bundan kattasi deyarli har doim
    #: siqilmagan skaner, va u bog'chaning diskini yeb qo'yardi.
    MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
    ALLOWED_DOCUMENT_SUFFIXES = (".pdf", ".png", ".jpg", ".jpeg", ".webp", ".heic")
    filterset_fields = ["status", "kind", "child"]
    ordering_fields = ["date_from", "created_at"]
    http_method_names = ["get", "post", "head", "options"]
    # Yaratishda fayl ham kelishi mumkin — shuning uchun JSON yonida
    # `multipart` ham qabul qilinadi.
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        payload = AbsenceClaimWriteSerializer(data=request.data, context={"request": request})
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        user = request_user(request)
        # Yozgan odam tasdiqlashga ham haqli bo'lsa — ikkinchi bosish
        # so'ralmaydi (mijoz so'rovi, 2026-10-14). Haqli bo'lmasa da'vo
        # avvalgidek kutadi: aks holda `attendance.create` jimgina pulni
        # harakatga keltirish huquqiga aylanardi.
        may_approve = user.is_org_owner or "attendance.approve" in user.permission_codes()

        # Bitta tranzaksiya: tasdiqlab bo'lmaydigan da'vo (masalan faqat
        # dam olish kunlari) "kutilmoqda" bo'lib qolib ketmasin.
        with transaction.atomic():
            claim = absence.create_claim(
                child=data["child"],
                kind=data["kind"],
                date_from=data["date_from"],
                date_to=data["date_to"],
                document_no=data.get("document_no", ""),
                note=data.get("note", ""),
                document_file=self._checked_document(data.get("document_file")),
                created_by=user,
            )
            if may_approve:
                absence.approve_claim(claim=claim, approved_by=user)
                claim.refresh_from_db()
        audit.record(
            action="create",
            request=request._request,
            actor=user,
            entity_type="absence_claim",
            entity_id=claim.id,
            changes={
                "from": str(claim.date_from),
                "to": str(claim.date_to),
                "kind": claim.kind,
                "status": claim.status,
                "credit": str(claim.credit_amount) if claim.credit_amount is not None else None,
            },
        )
        return Response(AbsenceClaimSerializer(claim).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def kinds(self, request: Request) -> Response:
        """
        `GET /absence-claims/kinds` — da'vo formasi uchun faol turlar (Bosqich 12.3).

        `attendance.read` bilan: tarbiyachi tur tanlashi kerak. Qoidani
        o'zgartirish esa `/absence-kinds` da va `settings.update` talab qiladi
        — bu pul siyosati.
        """
        absence.ensure_absence_kinds(request_user(request).organization)
        return Response(
            AbsenceKindSerializer(AbsenceKind.objects.filter(is_active=True), many=True).data
        )

    def _checked_document(self, uploaded: Any) -> Any:
        """Hajm va kengaytma — biriktirishning ikkala yo'lida bir xil."""
        if uploaded is None:
            return None
        if uploaded.size > self.MAX_DOCUMENT_BYTES:
            raise BusinessRuleViolation(gettext("Fayl 10 MB dan kichik boʻlishi kerak."))
        suffix = PurePosixPath(str(uploaded.name)).suffix.lower()
        if suffix not in self.ALLOWED_DOCUMENT_SUFFIXES:
            raise BusinessRuleViolation(gettext("PDF yoki rasm (JPG, PNG, WEBP) yuboring."))
        return uploaded

    @action(detail=True, methods=["post"], url_path="document", parser_classes=[MultiPartParser])
    def document(self, request: Request, pk: str | None = None) -> Response:
        """Spravka/arizani keyinroq biriktirish (PLAN 7.7)."""
        claim = self.get_object()
        uploaded = request.FILES.get("file")
        if uploaded is None:
            raise BusinessRuleViolation(gettext("Fayl yuborilmagan."))
        absence.attach_document(claim=claim, uploaded=self._checked_document(uploaded))
        audit.record(
            action="update",
            request=request._request,
            actor=request_user(request),
            entity_type="absence_claim",
            entity_id=claim.id,
            changes={"document": claim.document_file.name.rsplit("/", 1)[-1]},
        )
        return Response(AbsenceClaimSerializer(claim).data)

    @action(detail=True, methods=["get"], url_path="document/download")
    def document_download(self, request: Request, pk: str | None = None) -> FileResponse:
        """
        Faylni **shu endpoint** beradi, `/media/` havolasi emas.

        Statik media URL'i na kirishni, na tashkilot chegarasini
        biladi — havolani topgan har kim begona bolaning tibbiy
        ma'lumotnomasini ochardi. Bu yerda `get_object()` tenant bilan
        cheklangan, ya'ni begona da'vo oddiygina `404`.
        """
        claim = self.get_object()
        if not claim.document_file:
            raise Http404
        name = claim.document_file.name.rsplit("/", 1)[-1]
        return FileResponse(claim.document_file.open("rb"), as_attachment=True, filename=name)

    @action(detail=True, methods=["post"])
    def approve(self, request: Request, pk: str | None = None) -> Response:
        """Tasdiqlaydi va qaytariladigan summani MUZLATADI."""
        claim = self.get_object()
        user = request_user(request)
        absence.approve_claim(claim=claim, approved_by=user, note=request.data.get("note", ""))
        claim.refresh_from_db()
        audit.record(
            action="update",
            request=request._request,
            actor=user,
            entity_type="absence_claim",
            entity_id=claim.id,
            changes={
                "status": "approved",
                "days": claim.billable_days,
                "credit": str(claim.credit_amount),
            },
        )
        return Response(AbsenceClaimSerializer(claim).data)

    @action(detail=True, methods=["post"])
    def reject(self, request: Request, pk: str | None = None) -> Response:
        claim = self.get_object()
        user = request_user(request)
        absence.reject_claim(claim=claim, approved_by=user, note=request.data.get("note", ""))
        audit.record(
            action="update",
            request=request._request,
            actor=user,
            entity_type="absence_claim",
            entity_id=claim.id,
            changes={"status": "rejected"},
        )
        claim.refresh_from_db()
        return Response(AbsenceClaimSerializer(claim).data)


class AbsenceKindViewSet(TenantViewSet):
    """
    `/absence-kinds` — qayta hisob turlari va qoidalari (Bosqich 12.3, ADR-33).

    `settings` moduli: qaytarish usuli va summa — bog'chaning pul siyosati,
    tarbiyachi uni o'zgartirmaydi. O'chirish yo'q — `is_active=false`:
    eski da'volar tur kodiga bog'langan.
    """

    permission_module = "settings"
    model = AbsenceKind
    serializer_class = AbsenceKindSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_base_queryset(self) -> Any:
        absence.ensure_absence_kinds(request_user(self.request).organization)
        return super().get_base_queryset()

    def perform_create(self, serializer: Any) -> None:
        user = request_user(self.request)
        serializer.save(organization=user.organization)
        audit.record(
            action="create",
            request=self.request._request,
            actor=user,
            entity_type="absence_kind",
            entity_id=serializer.instance.id,
            changes={k: str(v) for k, v in serializer.validated_data.items()},
        )

    def perform_update(self, serializer: Any) -> None:
        serializer.save()
        audit.record(
            action="update",
            request=self.request._request,
            actor=request_user(self.request),
            entity_type="absence_kind",
            entity_id=serializer.instance.id,
            changes={k: str(v) for k, v in serializer.validated_data.items()},
        )
