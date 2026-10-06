"""Davomat serializerlari (docs/04 §8)."""

from __future__ import annotations

from typing import Any

from django.utils.translation import gettext
from rest_framework import serializers

from apps.attendance.models import AttendanceRecord, AttendanceStatus
from apps.attendance.models_absence import AbsenceClaim, ClaimKind, Holiday
from apps.attendance.models_staff import StaffAttendanceStatus
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
                gettext("Kelajakdagi kunga davomat belgilab boʻlmaydi.")
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
    # Eski kunni o'zgartirish sababi (PLAN 2.6). Tarbiyachi uchun u
    # yordam bermaydi — unga oyna qattiq; direktor uchun esa MAJBURIY,
    # chunki o'tgan oyning davomati pulga tegadi.
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate_records(self, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen = {row["child_id"] for row in value}
        if len(seen) != len(value):
            # Bitta so'rovda bir bola ikki marta — qaysi biri to'g'ri
            # ekanini taxmin qilishdan ko'ra rad etgan ma'qul.
            raise serializers.ValidationError(
                gettext("Bitta soʻrovda bir bola bir marta boʻlishi kerak.")
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
    # Faylning O'ZI emas, borligi va nomi. Havola `/media/` ga
    # chiqarilmaydi: u autentifikatsiyani ham, tashkilot chegarasini
    # ham bilmaydi — yuklash `document/download` endpointi orqali
    # ketadi (eksportlardagi kabi, apps/reports/views.py).
    has_document = serializers.SerializerMethodField()
    document_name = serializers.SerializerMethodField()
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
            "has_document",
            "document_name",
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

    def get_has_document(self, obj: AbsenceClaim) -> bool:
        return bool(obj.document_file)

    def get_document_name(self, obj: AbsenceClaim) -> str:
        return obj.document_file.name.rsplit("/", 1)[-1] if obj.document_file else ""


class AbsenceClaimWriteSerializer(serializers.Serializer):
    """Da'vo yozish — servis orqali, chunki kesishma tekshiriladi."""

    child_id = TenantPrimaryKeyRelatedField(model=Child, source="child")
    kind = serializers.ChoiceField(choices=ClaimKind.choices)
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    document_no = serializers.CharField(required=False, allow_blank=True, max_length=60)
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)
    # Spravka/ariza darhol yuborilishi mumkin (`multipart/form-data`),
    # lekin shart emas: qog'oz ko'pincha keyinroq keladi — o'shanda
    # `POST .../document` ishlatiladi.
    document_file = serializers.FileField(required=False, allow_null=True)


# --- Xodimlar davomati (tabel) ---


class StaffAttendanceRowSerializer(serializers.Serializer):
    employee_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=StaffAttendanceStatus.choices)
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class StaffAttendanceBulkSerializer(serializers.Serializer):
    """`POST /staff-attendance/bulk` — bir kun, ko'p xodim."""

    attendance_date = serializers.DateField()
    branch_id = serializers.UUIDField(required=False, allow_null=True)
    records = StaffAttendanceRowSerializer(many=True, allow_empty=False)
