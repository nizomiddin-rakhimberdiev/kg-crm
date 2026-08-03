"""Bolalar domeni serializerlari (docs/04 §7)."""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.branches.models import Branch
from apps.children.models import Child, ChildGuardian, Enrollment, Group, Guardian
from apps.core.fields import TenantPrimaryKeyRelatedField
from apps.finance.models import TariffPlan

__all__ = [
    "ChildSerializer",
    "ChildWriteSerializer",
    "GuardianSerializer",
    "GroupSerializer",
    "EnrollmentSerializer",
    "ChildGuardianSerializer",
]


class GuardianSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Guardian
        fields = ["id", "first_name", "last_name", "full_name", "phone", "email", "is_active"]
        read_only_fields = ["id", "full_name"]


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = [
            "id",
            "name",
            "age_min",
            "age_max",
            "capacity",
            "enrolled_count",
            "is_active",
            "created_at",
        ]
        # `enrolled_count` — enrollment'lardan hisoblangan kesh (D3),
        # mijoz uni yozolmaydi.
        read_only_fields = ["id", "enrolled_count", "created_at"]


class ChildGuardianSerializer(serializers.ModelSerializer):
    guardian = GuardianSerializer(read_only=True)

    class Meta:
        model = ChildGuardian
        fields = ["id", "guardian", "relation", "is_primary", "can_pickup"]
        read_only_fields = ["id"]


class EnrollmentSerializer(serializers.ModelSerializer):
    group = GroupSerializer(read_only=True)
    group_id = TenantPrimaryKeyRelatedField(model=Group, source="group", write_only=True)

    class Meta:
        model = Enrollment
        fields = ["id", "group", "group_id", "start_date", "end_date", "status"]
        read_only_fields = ["id", "status"]


class ChildSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    age_years = serializers.IntegerField(read_only=True)
    tariff_name = serializers.CharField(source="tariff.name", read_only=True, default=None)
    guardians = ChildGuardianSerializer(source="guardian_links", many=True, read_only=True)
    current_group = serializers.SerializerMethodField()

    class Meta:
        model = Child
        fields = [
            "id",
            "first_name",
            "last_name",
            "middle_name",
            "full_name",
            "date_of_birth",
            "age_years",
            "gender",
            "enrollment_status",
            "enrolled_on",
            "tariff",
            "tariff_name",
            "balance",
            "notes",
            "guardians",
            "current_group",
            "is_active",
            "created_at",
        ]
        read_only_fields = fields

    def get_current_group(self, obj: Child) -> dict[str, Any] | None:
        # `prefetch_related` bilan kelgan ro'yxatdan o'qiymiz — bu yerda
        # yangi so'rov yuborish ro'yxat sahifasida N+1 yaratardi.
        for enrollment in obj.enrollments.all():
            if enrollment.end_date is None and enrollment.status == "active":
                return {"id": str(enrollment.group_id), "name": enrollment.group.name}
        return None


class ChildWriteSerializer(serializers.ModelSerializer):
    # Filial mijozdan keladi, lekin faqat O'Z tashkilotining filiallaridan
    # (TenantPrimaryKeyRelatedField queryset'ni so'rov paytida cheklaydi).
    branch_id = TenantPrimaryKeyRelatedField(model=Branch, source="branch", required=False)
    # Tarifsiz bolaga hisob-faktura chiqarib bo'lmaydi (docs/03 §13.3),
    # shuning uchun uni biriktirish yo'li API'da bo'lishi shart.
    tariff_id = TenantPrimaryKeyRelatedField(
        model=TariffPlan, source="tariff", required=False, allow_null=True
    )

    class Meta:
        model = Child
        fields = [
            "id",
            "first_name",
            "last_name",
            "middle_name",
            "date_of_birth",
            "gender",
            "enrollment_status",
            "enrolled_on",
            "notes",
            "branch_id",
            "tariff_id",
        ]
        read_only_fields = ["id"]

    def validate_date_of_birth(self, value: Any) -> Any:
        from django.utils import timezone

        if value >= timezone.localdate():
            raise serializers.ValidationError("Tug'ilgan sana o'tgan bo'lishi kerak.")
        return value
