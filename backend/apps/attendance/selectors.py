"""Read-side entry points of `attendance` for other modules (invariant 1)."""

from __future__ import annotations

from datetime import date
from typing import Any

from apps.attendance.models import AttendanceRecord, AttendanceStatus

__all__ = ["present_count"]


def present_count(*, branch_id: Any, on_date: date) -> int:
    """Children marked present in a branch on a day — the kitchen's portions."""
    return AttendanceRecord.objects.filter(
        branch_id=branch_id, attendance_date=on_date, status=AttendanceStatus.PRESENT
    ).count()
