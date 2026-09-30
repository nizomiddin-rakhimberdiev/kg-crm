"""Davomat endpointlari (docs/04 §8)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from django.utils.translation import gettext
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.attendance import services
from apps.attendance import services_absence as absence
from apps.attendance.models import AttendanceRecord
from apps.attendance.models_absence import AbsenceClaim, Holiday
from apps.attendance.serializers import (
    AbsenceClaimSerializer,
    AbsenceClaimWriteSerializer,
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
            gettext("`{field}` formati noto'g'ri (kutilgan: 2026-07-24).").format(field=field)
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
    permission_action_map = {"approve": "approve", "reject": "approve"}
    model = AbsenceClaim
    serializer_class = AbsenceClaimSerializer
    select_related_fields = ("child", "approved_by")
    filterset_fields = ["status", "kind", "child"]
    ordering_fields = ["date_from", "created_at"]
    http_method_names = ["get", "post", "head", "options"]

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        payload = AbsenceClaimWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        user = request_user(request)

        claim = absence.create_claim(
            child=data["child"],
            kind=data["kind"],
            date_from=data["date_from"],
            date_to=data["date_to"],
            document_no=data.get("document_no", ""),
            note=data.get("note", ""),
            created_by=user,
        )
        audit.record(
            action="create",
            request=request._request,
            actor=user,
            entity_type="absence_claim",
            entity_id=claim.id,
            changes={"from": str(claim.date_from), "to": str(claim.date_to), "kind": claim.kind},
        )
        return Response(AbsenceClaimSerializer(claim).data, status=status.HTTP_201_CREATED)

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
