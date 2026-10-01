"""Bolalar domeni serializerlari (docs/04 §7)."""

from __future__ import annotations

from typing import Any

from django.utils.translation import gettext
from rest_framework import serializers

from apps.branches.models import Branch
from apps.children.models import (
    Child,
    ChildGuardian,
    Enrollment,
    EnrollmentStatus,
    Group,
    Guardian,
)
from apps.core.fields import TenantPrimaryKeyRelatedField
from apps.core.serializer_fields import PhoneField
from apps.finance.models import TariffPlan
from apps.hr.models import Employee

__all__ = [
    "ChildSerializer",
    "ChildWriteSerializer",
    "GuardianSerializer",
    "GroupSerializer",
    "EnrollmentSerializer",
    "ChildGuardianSerializer",
    "ChildStatusSerializer",
]


class GuardianSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    # Q7: saqlashda normalizatsiya. Noto'g'ri raqam SMS'ni JIMGINA
    # yo'qotadi — bildirishnoma "yuborildi" bo'lib turadi, ota-ona esa
    # hech narsa olmaydi.
    phone = PhoneField()

    class Meta:
        model = Guardian
        fields = [
            "id",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "email",
            # SMS tili (PLAN 3.4). Bo'sh = bog'chaning sukut tili.
            "language",
            "is_active",
        ]
        read_only_fields = ["id", "full_name"]


class GroupSerializer(serializers.ModelSerializer):
    # Tarbiyachi (PLAN 2.6) — u guruhni ko'rishi va davomatini
    # belgilashi uchun biriktiriladi.
    teacher_id = TenantPrimaryKeyRelatedField(
        model=Employee, source="teacher", required=False, allow_null=True
    )
    teacher_name = serializers.CharField(source="teacher.full_name", read_only=True, default=None)

    class Meta:
        model = Group
        fields = [
            "teacher_id",
            "teacher_name",
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
    # ModelSerializer buni majburiy qilib qo'yadi (modelda NOT NULL, default yo'q),
    # lekin view uni `.get()` bilan o'qiydi va `services.enroll_child()`
    # ko'rsatilmasa bugungi sanani qo'yadi. Majburiy qoldirilsa, "bolani guruhga
    # yoz" degan oddiy amal 400 bilan tugaydi.
    start_date = serializers.DateField(required=False)

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
            "allergies",
            "medical_notes",
            "guardians",
            "current_group",
            "status_changed_on",
            "status_reason",
            "archived_at",
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
            "allergies",
            "medical_notes",
            "branch_id",
            "tariff_id",
        ]
        read_only_fields = ["id"]

    def validate_date_of_birth(self, value: Any) -> Any:
        """
        Sana o'tgan va yosh oralig'ida bo'lishi kerak (PLAN 2.4).

        Kelajakdagi sana allaqachon rad etilardi, 30 yoshli "bola" esa
        yo'q edi. Bu shunchaki chiroysiz ma'lumot emas: yosh guruhga
        biriktirishda va hisobotlarda ishlatiladi.

        Chegara sozlamada: bog'chalar turlicha — ba'zilari 2 yoshdan,
        ba'zilari 7 yoshgacha oladi.
        """
        from django.utils import timezone

        from apps.settings_app.services import get_setting

        today = timezone.localdate()
        if value >= today:
            raise serializers.ValidationError(gettext("Tug'ilgan sana o'tgan bo'lishi kerak."))

        min_age = int(get_setting(key="children.min_age") or 0)
        max_age = int(get_setting(key="children.max_age") or 8)
        years = (today - value).days / 365.25
        # Yuqori chegaraga bir yil qo'shiladi: "8 yoshgacha" degani
        # 8 yoshli bola hali bog'chada bo'lishi mumkin degani.
        if not (min_age <= years <= max_age + 1):
            raise serializers.ValidationError(
                gettext("Bola yoshi {min}–{max} oralig'ida bo'lishi kerak.").format(
                    min=min_age, max=max_age
                )
            )
        return value


class ChildStatusSerializer(serializers.Serializer):
    """
    Holat o'zgarishi — sana va sabab MAJBURIY (Q5).

    Ikkalasi ixtiyoriy bo'lsa, ular to'ldirilmasdi va keyin
    "qachondan buyon?" degan savol javobsiz qolardi. Bu savol esa har
    doim pul bilan birga keladi.
    """

    enrollment_status = serializers.ChoiceField(choices=EnrollmentStatus.choices)
    status_changed_on = serializers.DateField()
    status_reason = serializers.CharField(max_length=255, trim_whitespace=True)
