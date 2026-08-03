"""Bildirishnoma serializerlari (docs/04 §15)."""

from __future__ import annotations

from rest_framework import serializers

from apps.notifications.models import Channel, Notification, NotificationTemplate

__all__ = [
    "NotificationTemplateSerializer",
    "NotificationSerializer",
    "SendNotificationSerializer",
]


class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = ["id", "code", "channel", "subject", "body", "branch", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class NotificationSerializer(serializers.ModelSerializer):
    guardian_name = serializers.CharField(source="guardian.full_name", read_only=True, default=None)

    class Meta:
        model = Notification
        fields = [
            "id",
            "template",
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
