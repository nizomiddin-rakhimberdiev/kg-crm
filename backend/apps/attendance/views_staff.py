"""Xodimlar davomati endpointlari (docs/04 §8.3, 2026-10)."""

from __future__ import annotations

from typing import Any

from django.utils import timezone
from django.utils.translation import gettext
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.attendance import services_staff as staff
from apps.attendance.serializers import StaffAttendanceBulkSerializer
from apps.attendance.views import _parse_date
from apps.core.exceptions import BusinessRuleViolation
from apps.core.permissions import HasModulePermission
from apps.core.typing import request_user
from apps.subscriptions.permissions import SubscriptionWriteGate

__all__ = ["StaffAttendanceViewSet"]


class StaffAttendanceViewSet(viewsets.ViewSet):
    """
    `/staff-attendance/*` — kunlik jurnal, belgilash va oylik tabel.

    Ruxsat — `attendance` moduli: tabelni bolalar davomatini yurituvchi
    odam belgilaydi. Javoblarda maosh yo'q — faqat ism, lavozim va kunlar,
    ya'ni `payroll.read` talab qilinmaydi.
    """

    permission_classes = [HasModulePermission, SubscriptionWriteGate]
    permission_module = "attendance"
    permission_action_map = {"daily": "read", "timesheet": "read", "bulk": "create"}

    @action(detail=False, methods=["get"])
    def daily(self, request: Request) -> Response:
        """`GET /staff-attendance/daily?date=&branch=`"""
        target = _parse_date(request.query_params.get("date"), "date")
        branch_id = staff.scope_branch_id(request_user(request), request.query_params.get("branch"))
        return Response(
            {
                "date": target.isoformat(),
                "rows": staff.daily_register(branch_id=branch_id, attendance_date=target),
            }
        )

    @action(detail=False, methods=["post"])
    def bulk(self, request: Request) -> Response:
        """`POST /staff-attendance/bulk` — bir kunni bitta chaqiruvda belgilaydi."""
        serializer = StaffAttendanceBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data: dict[str, Any] = serializer.validated_data
        user = request_user(request)
        saved = staff.mark_bulk(
            organization=user.organization,
            branch_id=staff.scope_branch_id(user, data.get("branch_id")),
            attendance_date=data["attendance_date"],
            records=data["records"],
            recorded_by=user,
        )
        return Response({"saved": saved})

    @action(detail=False, methods=["get"])
    def timesheet(self, request: Request) -> Response:
        """`GET /staff-attendance/timesheet?month=2026-10&branch=` — oylik tabel."""
        raw = request.query_params.get("month") or timezone.localdate().strftime("%Y-%m")
        try:
            year, month = (int(part) for part in raw.split("-", 1))
        except ValueError as exc:
            raise BusinessRuleViolation(gettext("`month` formati: 2026-07")) from exc
        user = request_user(request)
        return Response(
            staff.monthly_timesheet(
                organization_id=user.organization_id,
                branch_id=staff.scope_branch_id(user, request.query_params.get("branch")),
                year=year,
                month=month,
            )
        )
