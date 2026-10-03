"""Bolalar domeni serializerlari (docs/04 §7)."""

from __future__ import annotations

from decimal import Decimal
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
    telegram_linked = serializers.SerializerMethodField()
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
            # Xabar tili (PLAN 3.4). Bo'sh = bog'chaning sukut tili.
            "language",
            # Telegram holati (PLAN 3.7). `chat_id` ning o'zi
            # BERILMAYDI: ekranga faqat "ulanganmi" kerak, raqamning
            # o'zi esa javobda ortiqcha ma'lumot.
            "telegram_linked",
            "telegram_linked_at",
            "is_active",
        ]
        read_only_fields = ["id", "full_name", "telegram_linked", "telegram_linked_at"]

    def get_telegram_linked(self, obj: Guardian) -> bool:
        return bool((obj.telegram_chat_id or "").strip())


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


class AddGuardianSerializer(serializers.Serializer):
    """
    Bola kartasidan vasiy qo'shish (`POST /children/{id}/guardians`).

    Telefon `PhoneField` dan o'tadi (Q7) — alohida `/guardians` bilan
    BIR XIL qoida. Ilgari bu yo'l xom satrni yozardi: "12345" qabul
    qilinar, "+998 90 123 45 67" esa normalizatsiyasiz saqlanib, o'sha
    ota-ona bo'yicha qidiruvda topilmasdi (yakuniy qabul ssenariysi).
    """

    phone = PhoneField()
    first_name = serializers.CharField(max_length=80, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=80, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    language = serializers.CharField(max_length=2, required=False, allow_blank=True)
    relation = serializers.CharField(max_length=20, required=False, default="other")
    is_primary = serializers.BooleanField(required=False, default=False)
    can_pickup = serializers.BooleanField(required=False, default=True)


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
            "monthly_fee",
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
    # Individual narx — tarif o'rniga (docs/03 §11.1). `min_value` bazadagi
    # `ck_child_monthly_fee_positive` ning API'dagi ko'zgusi: 0 so'm "narx
    # yo'q" bilan adashmasin, narxsiz bola uchun maydon bo'sh qoladi.
    monthly_fee = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
        min_value=Decimal("1"),
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
            "monthly_fee",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Narx manbai BITTA: tarif yoki individual narx.

        Bittasini qo'ygan so'rov ikkinchisini o'zi tozalaydi — mijoz
        "tarifdan individual narxga o'tish" uchun ikkala maydonni ham
        yuborishi shart emas. Ikkalasi ham qiymat bilan kelsa — bu
        noaniqlik, `400` (baza baribir `ck_child_one_price_source` bilan
        to'sadi, lekin u `409` — foydalanuvchi nima noto'g'riligini
        bilmaydi).
        """
        has_tariff = attrs.get("tariff") is not None
        has_fee = attrs.get("monthly_fee") is not None
        if has_tariff and has_fee:
            raise serializers.ValidationError(
                {"monthly_fee": [gettext("Tarif yoki individual narx — faqat bittasini tanlang.")]}
            )
        if has_tariff:
            attrs["monthly_fee"] = None
        elif has_fee:
            attrs["tariff"] = None
        return attrs

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
            raise serializers.ValidationError(gettext("Tugʻilgan sana oʻtgan boʻlishi kerak."))

        min_age = int(get_setting(key="children.min_age") or 0)
        max_age = int(get_setting(key="children.max_age") or 8)
        years = (today - value).days / 365.25
        # Yuqori chegaraga bir yil qo'shiladi: "8 yoshgacha" degani
        # 8 yoshli bola hali bog'chada bo'lishi mumkin degani.
        if not (min_age <= years <= max_age + 1):
            raise serializers.ValidationError(
                gettext("Bola yoshi {min}–{max} oraligʻida boʻlishi kerak.").format(
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
