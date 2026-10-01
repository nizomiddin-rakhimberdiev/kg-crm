"""Platforma konsoli serializerlari (docs/04 §19)."""

from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from apps.accounts.serializers import validate_password_strength
from apps.core.serializer_fields import PhoneField
from apps.platform.models import GRANT_MAX_HOURS, Lead, LeadStatus, SupportGrant

__all__ = [
    "PlatformLoginSerializer",
    "OrganizationCreateSerializer",
    "ReasonSerializer",
    "ExtendTrialSerializer",
    "SupportGrantRequestSerializer",
    "SupportGrantSerializer",
    "RecordPaymentSerializer",
    "LeadCreateSerializer",
    "LeadSerializer",
]


class PlatformLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    # TOTP — `PLATFORM_2FA_REQUIRED` yoqilganda majburiy (ADR-15). Maydon
    # ixtiyoriy, lekin talab qilinganda uning yo'qligi `TOTP_REQUIRED`
    # bilan rad etiladi — "keyin yoqaman" holati serializer'da emas,
    # autentifikatsiyada yopiladi.
    code = serializers.CharField(min_length=6, max_length=6, required=False, allow_blank=True)


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=3, max_length=500)


class ExtendTrialSerializer(ReasonSerializer):
    days = serializers.IntegerField(min_value=1, max_value=30)


class SupportGrantRequestSerializer(ReasonSerializer):
    hours = serializers.IntegerField(min_value=1, max_value=GRANT_MAX_HOURS, default=2)


class SupportGrantSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    platform_email = serializers.CharField(source="platform_user.email", read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = SupportGrant
        fields = [
            "id",
            "organization",
            "organization_name",
            "platform_email",
            "reason",
            "expires_at",
            "revoked_at",
            "is_active",
            "created_at",
        ]
        read_only_fields = fields


class RecordPaymentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    method = serializers.ChoiceField(
        choices=["bank_transfer", "card", "cash"], default="bank_transfer"
    )
    reference = serializers.CharField(required=False, allow_blank=True, max_length=80)


class OrganizationCreateSerializer(serializers.Serializer):
    """
    Vendor yangi mijoz ochadi (ADR-10).

    Ochiq `/auth/signup` o'rnini bosadi. Farqi tashqi ko'rinishda emas,
    MA'NODA: mijoz endi o'zini o'zi yaratmaydi — uni siz yaratasiz, ya'ni
    har bir tenant sotuv suhbatidan keyin paydo bo'ladi, tasodifiy
    tashrifdan keyin emas.
    """

    organization_name = serializers.CharField(max_length=200)
    contact_email = serializers.EmailField()
    contact_phone = PhoneField(required=False, allow_blank=True)
    full_name = serializers.CharField(max_length=150)
    password = serializers.CharField(validators=[validate_password_strength])

    # Bo'sh qoldirilsa nomdan hosil qilinadi. Vendor uni ATAYLAB tanlay
    # oladi: bu mijozning manzili (`/t/<slug>`) va u bosma materialga,
    # SMS matniga, hisob-faktura havolasiga tushadi.
    slug = serializers.CharField(max_length=50, required=False, allow_blank=True)

    branch_name = serializers.CharField(max_length=120, required=False, allow_blank=True)


class LeadCreateSerializer(serializers.Serializer):
    """Internetdan keladigan minimal zayavka; consent frontendda emas, shu yerda majburiy."""

    name = serializers.CharField(max_length=150, trim_whitespace=True)
    # Normalizatsiya umumiy modulda (Q7) — ilgari u faqat shu yerda
    # bor edi, vasiy va xodim telefonlarida esa yo'q edi.
    phone = PhoneField(max_length=32)
    kindergarten_name = serializers.CharField(max_length=200, trim_whitespace=True)
    children_count = serializers.IntegerField(min_value=1, max_value=10_000)
    city = serializers.CharField(max_length=120, trim_whitespace=True)
    message = serializers.CharField(
        max_length=1_000, required=False, allow_blank=True, trim_whitespace=True
    )
    language = serializers.ChoiceField(choices=["uz", "ru", "en"])
    consent = serializers.BooleanField()
    privacy_policy_version = serializers.RegexField(r"^[a-zA-Z0-9._-]{1,32}$")
    submission_id = serializers.UUIDField()
    # Ko'rinmas honeypot. To'ldirilsa normal validation xatosi qaytadi;
    # botga endpoint xatti-harakatlari haqida qo'shimcha signal bermaymiz.
    website = serializers.CharField(required=False, allow_blank=True, write_only=True, max_length=0)

    def validate_consent(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError(
                "Shaxsiy ma'lumotlarga ishlov berishga rozilik talab qilinadi."
            )
        return value


class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = [
            "id",
            "name",
            "phone",
            "kindergarten_name",
            "children_count",
            "city",
            "message",
            "language",
            "source",
            "status",
            "note",
            "next_call_at",
            "status_changed_at",
            "consented_at",
            "privacy_policy_version",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class LeadStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=LeadStatus.choices)
    note = serializers.CharField(required=False, allow_blank=True, max_length=2_000)
    # Keyingi qo'ng'iroq sanasi (PLAN 3.6). `allow_null` — sotuvchi
    # rejani bekor qilishi ham kerak.
    next_call_at = serializers.DateField(required=False, allow_null=True)
