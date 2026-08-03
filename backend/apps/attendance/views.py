"""Davomat endpointlari (docs/04 §8)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.attendance import services
from apps.attendance.models import AttendanceRecord
from apps.attendance.serializers import (
    AttendanceRecordSerializer,
    AttendanceWriteSerializer,
    BulkAttendanceSerializer,
)
from apps.children.models import Group
from apps.core.exceptions import BusinessRuleViolation
from apps.core.typing import request_user
from apps.core.viewsets import BranchScopedMixin, TenantViewSet

__all__ = ["AttendanceViewSet"]


def _parse_date(raw: str | None, field: str) -> Any:
    if not raw:
        raise BusinessRuleViolation(f"`{field}` parametri majburiy.")
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError as exc:
        raise BusinessRuleViolation(f"`{field}` formati noto'g'ri (kutilgan: 2026-07-24).") from exc


def _resolve_group(group_id: str | None) -> Group:
    if not group_id:
        raise BusinessRuleViolation("`group` parametri majburiy.")
    # `Group.objects` tenant bilan cheklangan — begona guruh "topilmadi".
    group = Group.objects.filter(pk=group_id).first()
    if group is None:
        raise BusinessRuleViolation("Guruh topilmadi.")
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
            raise BusinessRuleViolation("`month` parametri majburiy (masalan 2026-07).")
        try:
            year, month = (int(part) for part in raw_month.split("-", 1))
        except ValueError as exc:
            raise BusinessRuleViolation("`month` formati: 2026-07") from exc

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
