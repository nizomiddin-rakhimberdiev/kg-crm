"""Bildirishnoma serializerlari (docs/04 §15)."""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.notifications.models import Channel, Notification, NotificationTemplate

__all__ = [
    "NotificationTemplateSerializer",
    "TemplatePreviewSerializer",
    "NotificationSerializer",
    "SendNotificationSerializer",
]


class NotificationTemplateSerializer(serializers.ModelSerializer):
    # Muharrirdagi hisoblagich (PLAN 3.4): belgilar, kodlash va necha
    # SMS bo'lagi. Hisob SERVERDA: narx shu bo'laklar bo'yicha
    # to'lanadi va ikkita hisob ertami-kechmi ajraladi.
    length = serializers.SerializerMethodField()
    variables = serializers.SerializerMethodField()

    class Meta:
        model = NotificationTemplate
        fields = [
            "id",
            "code",
            "channel",
            "language",
            "subject",
            "body",
            "branch",
            "is_active",
            "length",
            "variables",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "length", "variables"]

    def get_length(self, obj: NotificationTemplate) -> dict[str, Any]:
        from apps.notifications.segments import measure, sms_safe

        measured = measure(sms_safe(obj.body))
        return {
            "encoding": measured.encoding,
            "characters": measured.characters,
            "parts": measured.parts,
            "limit": measured.limit,
        }

    def get_variables(self, obj: NotificationTemplate) -> list[str]:
        from apps.notifications.services import TEMPLATE_VARIABLES

        return list(TEMPLATE_VARIABLES.get(obj.code, ()))


class TemplatePreviewSerializer(serializers.Serializer):
    """Muharrirdagi "Ko'rib chiqish" — yuborilmaydi, faqat ko'rsatiladi."""

    body = serializers.CharField()
    variables = serializers.DictField(required=False, default=dict)


class NotificationSerializer(serializers.ModelSerializer):
    guardian_name = serializers.CharField(source="guardian.full_name", read_only=True, default=None)

    class Meta:
        model = Notification
        fields = [
            "id",
            "template",
            # Xabar turi — shablon o'chirilgan bo'lsa ham jurnalda
            # ko'rinib turishi kerak (PLAN 3.7).
            "template_code",
            "guardian",
            "guardian_name",
            "channel",
            "recipient_address",
            "rendered_body",
            "status",
            "provider_message_id",
            "retry_count",
            "error",
            "scheduled_for",
            "sent_at",
            "created_at",
        ]
        # Jurnal faqat o'qish uchun: yuborilgan xabarni keyin tahrirlash
        # "men bunday xabar olmaganman" bahsiga javobni yo'q qilardi.
        read_only_fields = fields


class SendNotificationSerializer(serializers.Serializer):
    template_code = serializers.CharField(max_length=50)
    channel = serializers.ChoiceField(choices=Channel.choices, default=Channel.SMS)
    guardian_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
    variables = serializers.DictField(required=False, default=dict)
    body_override = serializers.CharField(required=False, allow_blank=True)
