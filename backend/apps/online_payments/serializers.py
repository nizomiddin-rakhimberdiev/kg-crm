"""Serializers for the staff side of online payments (PLAN 6.1)."""

from __future__ import annotations

from rest_framework import serializers

from apps.online_payments.models import Provider

__all__ = ["CreateLinkSerializer", "CredentialSerializer"]


class CreateLinkSerializer(serializers.Serializer):
    invoice_id = serializers.UUIDField()


class CredentialSerializer(serializers.Serializer):
    merchant_id = serializers.CharField(max_length=64)
    service_id = serializers.CharField(max_length=32, required=False, allow_blank=True)
    secret = serializers.CharField(max_length=256, write_only=True, trim_whitespace=True)
    sandbox = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs: dict) -> dict:
        provider = self.context.get("provider")
        if provider == Provider.CLICK and not attrs.get("service_id"):
            raise serializers.ValidationError({"service_id": "Click uchun service_id majburiy."})
        return attrs
