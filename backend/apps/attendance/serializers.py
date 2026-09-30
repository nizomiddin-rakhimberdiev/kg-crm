"""Davomat serializerlari (docs/04 §8)."""

from __future__ import annotations

from typing import Any

from django.utils.translation import gettext
from rest_framework import serializers

from apps.attendance.models import AttendanceRecord, AttendanceStatus
from apps.attendance.models_absence import AbsenceClaim, ClaimKind, Holiday
from apps.children.models import Child, Group
from apps.core.fields import TenantPrimaryKeyRelatedField

__all__ = [
    "AttendanceRecordSerializer",
    "AttendanceWriteSerializer",
    "BulkAttendanceSerializer",
]


class AttendanceRecordSerializer(serializers.ModelSerializer):
    child_name = serializers.CharField(source="child.full_name", read_only=True)
    group_name = serializers.CharField(source="group.name", read_only=True, default=None)

    class Meta:
        model = AttendanceRecord
        fields = [
            "id",
            "child",
            "child_name",
            "group",
            "group_name",
            "attendance_date",
            "status",
            "check_in_at",
            "check_out_at",
            "reason",
            "created_at",
        ]
        read_only_fields = fields


class AttendanceWriteSerializer(serializers.ModelSerializer):
    child = TenantPrimaryKeyRelatedField(model=Child)
    group = TenantPrimaryKeyRelatedField(model=Group, required=False, allow_null=True)

    class Meta:
        model = AttendanceRecord
        fields = [
            "id",
            "child",
            "group",
            "attendance_date",
            "status",
            "check_in_at",
            "check_out_at",
            "reason",
        ]
        read_only_fields = ["id"]

    def validate_attendance_date(self, value: Any) -> Any:
        from django.utils import timezone

        if value > timezone.localdate():
            raise serializers.ValidationError(
                gettext("Kelajakdagi kunga davomat belgilab bo'lmaydi.")
            )
        return value


class BulkRowSerializer(serializers.Serializer):
    child_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=AttendanceStatus.choices)
    check_in_at = serializers.DateTimeField(required=False, allow_null=True)
    check_out_at = serializers.DateTimeField(required=False, allow_null=True)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)


class BulkAttendanceSerializer(serializers.Serializer):
    group_id = TenantPrimaryKeyRelatedField(model=Group, source="group")
    attendance_date = serializers.DateField()
    records = BulkRowSerializer(many=True)

    def validate_records(self, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen = {row["child_id"] for row in value}
        if len(seen) != len(value):
            # Bitta so'rovda bir bola ikki marta — qaysi biri to'g'ri
            # ekanini taxmin qilishdan ko'ra rad etgan ma'qul.
            raise serializers.ValidationError(
                gettext("Bitta so'rovda bir bola bir marta bo'lishi kerak.")
            )
        return value


# --- Kelmagan kunlar uchun qaytarish (ADR-19) ---


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ["id", "holiday_date", "name", "created_at"]
        read_only_fields = ["id", "created_at"]


class AbsenceClaimSerializer(serializers.ModelSerializer):
    child_name = serializers.CharField(source="child.full_name", read_only=True)
    approved_by_name = serializers.CharField(
        source="approved_by.full_name", read_only=True, default=None
    )

    class Meta:
        model = AbsenceClaim
        fields = [
            "id",
            "child",
            "child_name",
            "kind",
            "date_from",
            "date_to",
            "document_no",
            "note",
            "status",
            "billable_days",
            "daily_rate",
            "credit_amount",
            "approved_by_name",
            "decided_at",
            "decision_note",
            "applied_invoice",
            "created_at",
        ]
        read_only_fields = fields


class AbsenceClaimWriteSerializer(serializers.Serializer):
    """Da'vo yozish — servis orqali, chunki kesishma tekshiriladi."""

    child_id = TenantPrimaryKeyRelatedField(model=Child, source="child")
    kind = serializers.ChoiceField(choices=ClaimKind.choices)
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    document_no = serializers.CharField(required=False, allow_blank=True, max_length=60)
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)
