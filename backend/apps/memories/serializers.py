"""Radix AI serializerlari (docs/08 §6). Tashqi ID'lar faqat joriy tenant ichida."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.utils.translation import gettext
from rest_framework import serializers

from apps.children.models import Child, Guardian
from apps.core.fields import TenantPrimaryKeyRelatedField
from apps.memories import services
from apps.memories.crypto import encrypt_text
from apps.memories.models import (
    Camera,
    CameraConnection,
    CameraEvent,
    ChatKind,
    DayScheduleItem,
    EventKind,
    EventSeverity,
    FaceConsent,
    MemoryPhoto,
    PhotoTag,
    TelegramChat,
)

__all__ = [
    "MemoryPhotoSerializer",
    "PhotoTagSerializer",
    "FaceConsentSerializer",
    "DayScheduleItemSerializer",
    "CameraSerializer",
    "CameraTokenRequestSerializer",
    "CameraEventSerializer",
    "TelegramChatSerializer",
    "PairingRequestSerializer",
    "ManualTagSerializer",
    "ImageUploadSerializer",
]

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


class ImageUploadSerializer(serializers.Serializer):
    image = serializers.ImageField()
    caption = serializers.CharField(required=False, allow_blank=True, max_length=200)

    def validate_image(self, value: Any) -> Any:
        if value.size > settings.MEMORIES_MAX_UPLOAD_BYTES:
            raise serializers.ValidationError(gettext("Rasm hajmi juda katta."))
        if getattr(value, "content_type", "") not in ALLOWED_IMAGE_TYPES:
            raise serializers.ValidationError(
                gettext("Faqat JPEG, PNG yoki WebP rasm qabul qilinadi.")
            )
        return value


class PhotoTagSerializer(serializers.ModelSerializer):
    child_name = serializers.CharField(source="child.first_name", read_only=True)

    class Meta:
        model = PhotoTag
        fields = ["id", "photo", "child", "child_name", "confidence", "box", "status", "sent_at"]
        read_only_fields = fields


class MemoryPhotoSerializer(serializers.ModelSerializer):
    # Rasm fayliga TO'G'RIDAN-TO'G'RI havola yo'q: u autentifikatsiyali
    # endpoint orqali beriladi (bola rasmlari ochiq URL'da turmasin).
    image_url = serializers.SerializerMethodField()
    tags = PhotoTagSerializer(many=True, read_only=True)

    class Meta:
        model = MemoryPhoto
        fields = [
            "id",
            "branch",
            "image_url",
            "taken_at",
            "source",
            "status",
            "faces_detected",
            "caption",
            "tags",
            "created_at",
        ]
        read_only_fields = fields

    def get_image_url(self, obj: MemoryPhoto) -> str:
        return f"/api/v1/memory-photos/{obj.id}/image"


class ManualTagSerializer(serializers.Serializer):
    child_id = TenantPrimaryKeyRelatedField(model=Child, source="child")


class FaceConsentSerializer(serializers.ModelSerializer):
    child_id = TenantPrimaryKeyRelatedField(model=Child, source="child", write_only=True)
    guardian_id = TenantPrimaryKeyRelatedField(model=Guardian, source="guardian", write_only=True)
    child_name = serializers.CharField(source="child.first_name", read_only=True)
    guardian_name = serializers.CharField(source="guardian.full_name", read_only=True)
    samples = serializers.SerializerMethodField()

    class Meta:
        model = FaceConsent
        fields = [
            "id",
            "child",
            "child_id",
            "child_name",
            "guardian",
            "guardian_id",
            "guardian_name",
            "given_at",
            "revoked_at",
            "samples",
        ]
        read_only_fields = ["id", "child", "guardian", "given_at", "revoked_at"]

    def get_samples(self, obj: FaceConsent) -> int:
        return obj.child.face_samples.count()


class DayScheduleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = DayScheduleItem
        fields = [
            "id",
            "branch",
            "kind",
            "on_date",
            "at_time",
            "title",
            "details",
            "notify",
            "notified_at",
        ]
        read_only_fields = ["id", "branch", "notified_at"]


class CameraSerializer(serializers.ModelSerializer):
    # Oqim manzili login/parol saqlaydi: faqat yoziladi, shifrlanadi, qaytmaydi.
    stream_url = serializers.CharField(
        write_only=True, required=False, allow_blank=True, max_length=500
    )
    has_stream = serializers.SerializerMethodField()
    has_token = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()
    has_preview = serializers.SerializerMethodField()

    class Meta:
        model = Camera
        fields = [
            "id",
            "branch",
            "name",
            "location",
            "stream_url",
            "has_stream",
            "has_token",
            "is_online",
            "connection",
            "preview_enabled",
            "has_preview",
            "preview_at",
            "last_seen_at",
            "is_active",
        ]
        read_only_fields = ["id", "branch", "last_seen_at", "connection", "preview_at"]

    def get_has_preview(self, obj: Camera) -> bool:
        return bool(obj.preview and obj.preview_enabled)

    def get_has_stream(self, obj: Camera) -> bool:
        return bool(obj.stream_url)

    def get_has_token(self, obj: Camera) -> bool:
        return bool(obj.ingest_token_hash)

    def get_is_online(self, obj: Camera) -> bool:
        return services.camera_is_online(obj)

    def validate_stream_url(self, value: str) -> str:
        if value and not value.lower().startswith(("rtsp://", "rtsps://", "http://", "https://")):
            raise serializers.ValidationError(
                gettext("Manzil rtsp:// yoki http(s):// bilan boshlanishi kerak.")
            )
        return value

    def create(self, validated_data: dict[str, Any]) -> Camera:
        validated_data["stream_url"] = encrypt_text(validated_data.get("stream_url", ""))
        return super().create(validated_data)  # type: ignore[no-any-return]

    def update(self, instance: Camera, validated_data: dict[str, Any]) -> Camera:
        if "stream_url" in validated_data:
            validated_data["stream_url"] = encrypt_text(validated_data["stream_url"])
        return super().update(instance, validated_data)  # type: ignore[no-any-return]


class CameraEventSerializer(serializers.ModelSerializer):
    camera_id = TenantPrimaryKeyRelatedField(
        model=Camera, source="camera", write_only=True, required=False, allow_null=True
    )
    camera_name = serializers.CharField(source="camera.name", read_only=True, default=None)
    snapshot_url = serializers.SerializerMethodField()
    snapshot = serializers.ImageField(write_only=True, required=False)

    class Meta:
        model = CameraEvent
        fields = [
            "id",
            "branch",
            "camera",
            "camera_id",
            "camera_name",
            "kind",
            "severity",
            "status",
            "snapshot",
            "snapshot_url",
            "note",
            "occurred_at",
            "alerted_at",
        ]
        read_only_fields = ["id", "branch", "camera", "status", "alerted_at"]
        extra_kwargs = {"occurred_at": {"required": False}}

    def get_snapshot_url(self, obj: CameraEvent) -> str | None:
        return f"/api/v1/camera-events/{obj.id}/snapshot" if obj.snapshot else None

    def validate_snapshot(self, value: Any) -> Any:
        if value.size > settings.MEMORIES_MAX_UPLOAD_BYTES:
            raise serializers.ValidationError(gettext("Rasm hajmi juda katta."))
        return value


class TelegramChatSerializer(serializers.ModelSerializer):
    guardian_name = serializers.CharField(source="guardian.full_name", read_only=True, default=None)

    class Meta:
        model = TelegramChat
        # `chat_id` ataylab yo'q: u Telegram ichki identifikatori, panelga kerak emas.
        fields = [
            "id",
            "branch",
            "kind",
            "guardian",
            "guardian_name",
            "language",
            "title",
            "created_at",
        ]
        read_only_fields = fields


class PairingRequestSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=ChatKind.choices)
    guardian_id = TenantPrimaryKeyRelatedField(
        model=Guardian, source="guardian", required=False, allow_null=True
    )
    branch_id = serializers.UUIDField(required=False)


class CameraSignalSerializer(serializers.Serializer):  # type: ignore[type-arg]
    """Edge-worker signali: `kind` yo'q bo'lsa — faqat heartbeat."""

    kind = serializers.ChoiceField(choices=EventKind.choices, required=False)
    severity = serializers.ChoiceField(
        choices=EventSeverity.choices, required=False, default=EventSeverity.WARNING
    )
    note = serializers.CharField(required=False, allow_blank=True, max_length=400, default="")
    snapshot = serializers.FileField(required=False, allow_empty_file=False)


class CameraTokenRequestSerializer(serializers.Serializer):  # type: ignore[type-arg]
    connection = serializers.ChoiceField(
        choices=CameraConnection.choices, required=False, default=CameraConnection.EDGE
    )
