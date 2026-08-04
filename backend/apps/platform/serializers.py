"""Platforma konsoli serializerlari (docs/04 §19)."""

from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from apps.platform.models import GRANT_MAX_HOURS, SupportGrant

__all__ = [
    "PlatformLoginSerializer",
    "ReasonSerializer",
    "ExtendTrialSerializer",
    "SupportGrantRequestSerializer",
    "SupportGrantSerializer",
    "RecordPaymentSerializer",
]


class PlatformLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    # TOTP MAJBURIY — ixtiyoriy maydon "keyin yoqaman" degan holatni
    # mumkin qilardi (ADR-10).
    code = serializers.CharField(min_length=6, max_length=6)


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
