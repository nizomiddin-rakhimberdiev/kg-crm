"""Audit jurnali serializerlari (docs/04 §17)."""

from __future__ import annotations

from rest_framework import serializers

from apps.audit import labels as audit_labels
from apps.audit.models import AuditLog

__all__ = ["AuditLogSerializer"]


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.full_name", read_only=True, default=None)
    # Nom — UUID'ning o'rniga (PLAN 4.4). Jurnal "kim nima qildi?"
    # degan savol uchun bor, va `child: "4f3c9e21-…"` bu savolga
    # javob bermaydi: har bir UUID'ni qo'lda qidirish kerak bo'ladi.
    #
    # Nomlar ro'yxat darajasida BIR SO'ROVDA olinadi
    # (`get_serializer_context` → `labels`), shuning uchun bu yerda
    # faqat kontekstdan o'qiladi.
    entity_label = serializers.SerializerMethodField()
    changes_labels = serializers.SerializerMethodField()

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
            "entity_label",
            "changes",
            "changes_labels",
            "ip",
        ]
        # Jurnal faqat qo'shiladi (D3). Tahrirlanadigan audit — audit emas.
        read_only_fields = fields

    def _labels(self) -> dict[str, dict[str, str]]:
        return self.context.get("labels") or {}

    def get_entity_label(self, obj: AuditLog) -> str:
        if not obj.entity_id:
            return ""
        return self._labels().get(obj.entity_type, {}).get(str(obj.entity_id), "")

    def get_changes_labels(self, obj: AuditLog) -> dict[str, str]:
        """
        `{kalit: nom}` — faqat hal qilinganlar.

        Hal qilinmagan qiymat javobda UMUMAN bo'lmaydi: bo'sh satr
        yuborish ekranda "nomi yo'q" degan taassurot berardi, holbuki
        yozuv o'chirilgan yoki tur ro'yxatda yo'q.
        """
        labels = self._labels()
        out: dict[str, str] = {}
        for key, value in (obj.changes or {}).items():
            if not isinstance(value, str):
                continue
            # Kalit turni o'zi aytmasligi mumkin (`from`, `employee_id`) —
            # qoidalar `labels.entity_for_key()` da (audit, 2026-10-21).
            target = audit_labels.entity_for_key(obj.entity_type, key)
            if target is None:
                continue
            name = labels.get(target, {}).get(value)
            if name:
                out[key] = name
        return out
