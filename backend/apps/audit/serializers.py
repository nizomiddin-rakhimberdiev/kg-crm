"""Audit jurnali serializerlari (docs/04 §17)."""

from __future__ import annotations

from rest_framework import serializers

from apps.audit.models import AuditLog

__all__ = ["AuditLogSerializer"]


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.full_name", read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "created_at",
            "actor",
            "actor_name",
            "actor_email",
            "action",
            "entity_type",
            "entity_id",
            "changes",
            "ip",
        ]
        # Jurnal faqat qo'shiladi (D3). Tahrirlanadigan audit — audit emas.
        read_only_fields = fields
