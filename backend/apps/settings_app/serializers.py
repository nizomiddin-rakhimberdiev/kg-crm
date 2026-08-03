"""Sozlama serializerlari (docs/04 §16)."""

from __future__ import annotations

from rest_framework import serializers

from apps.settings_app.models import SystemSetting

__all__ = ["SystemSettingSerializer", "SetSettingSerializer"]


class SystemSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSetting
        fields = ["id", "key", "value", "branch", "description", "created_at"]
        read_only_fields = ["id", "created_at"]


class SetSettingSerializer(serializers.Serializer):
    # `JSONField` — qiymat skalyar, ro'yxat yoki obyekt bo'lishi mumkin
    # (docs/03 §18.1); shakl oldindan belgilanmaydi.
    value = serializers.JSONField()
    branch_id = serializers.UUIDField(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True, max_length=255)
