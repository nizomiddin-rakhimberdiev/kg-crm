"""
Radix AI — xotira, yuz tanish, Telegram va kamera (docs/08).

Biometrik ma'lumot (yuz vektori) — eng nozik ma'lumot. Qoidalar:
  * vektor faqat shifrlangan holda saqlanadi (`crypto.py`);
  * yuz faqat vasiyning ROZILIGI bor bola uchun tanib olinadi;
  * rozilik bekor qilinsa, vektorlar o'chiriladi (`services.revoke_consent`).
"""

from __future__ import annotations

import uuid
from pathlib import PurePosixPath

from django.db import models
from django.utils.translation import gettext_lazy

from apps.core.models import BranchScopedModel, TenantScopedModel

__all__ = [
    "CameraConnection",
    "FaceConsent",
    "FaceSample",
    "MemoryPhoto",
    "PhotoTag",
    "TelegramChat",
    "PairingToken",
    "DayScheduleItem",
    "Camera",
    "CameraEvent",
]


def _build_path(instance: models.Model, filename: str, kind: str) -> str:
    suffix = PurePosixPath(filename).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".jpg"
    # UUID nom: yuklangan nom saqlansa, boshqa mijoz fayl nomini taxmin qila oladi.
    return f"{instance.organization_id}/{kind}/{uuid.uuid4()}{suffix}"  # type: ignore[attr-defined]


def photo_upload_path(instance: models.Model, filename: str) -> str:
    return _build_path(instance, filename, "memories")


def preview_upload_path(instance: models.Model, filename: str) -> str:
    return _build_path(instance, filename, "camera-previews")


def event_upload_path(instance: models.Model, filename: str) -> str:
    return _build_path(instance, filename, "camera-events")


class FaceConsent(BranchScopedModel):
    """Vasiyning bola yuzini tanishga yozma roziligi (bolaga bitta faol)."""

    child = models.ForeignKey(
        "children.Child", on_delete=models.RESTRICT, related_name="face_consents"
    )
    guardian = models.ForeignKey(
        "children.Guardian", on_delete=models.RESTRICT, related_name="face_consents"
    )
    given_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "face_consent"
        ordering = ["-given_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["child"],
                condition=models.Q(revoked_at__isnull=True),
                name="uq_face_consent_one_active",
            )
        ]


class FaceSample(BranchScopedModel):
    """Bolaning bitta yuz vektori (shifrlangan)."""

    child = models.ForeignKey(
        "children.Child", on_delete=models.RESTRICT, related_name="face_samples"
    )
    embedding = models.BinaryField(help_text="Fernet bilan shifrlangan float32 vektor")
    model_version = models.CharField(max_length=40)

    class Meta:
        db_table = "face_sample"
        ordering = ["-created_at"]


class PhotoSource(models.TextChoices):
    TELEGRAM = "telegram", gettext_lazy("Telegram guruhi")
    UPLOAD = "upload", gettext_lazy("Yuklangan")


class PhotoStatus(models.TextChoices):
    PENDING = "pending", gettext_lazy("Kutilmoqda")
    PROCESSED = "processed", gettext_lazy("Qayta ishlandi")
    FAILED = "failed", gettext_lazy("Xato")


class MemoryPhoto(BranchScopedModel):
    image = models.ImageField(upload_to=photo_upload_path)
    taken_at = models.DateTimeField(db_index=True)
    source = models.CharField(
        max_length=12, choices=PhotoSource.choices, default=PhotoSource.UPLOAD
    )
    status = models.CharField(
        max_length=12, choices=PhotoStatus.choices, default=PhotoStatus.PENDING
    )
    faces_detected = models.PositiveSmallIntegerField(default=0)
    # Barcha topilgan yuzlar (x, y, w, h; 0..1) — begona bolalarni xiralashtirish uchun.
    face_boxes = models.JSONField(default=list, blank=True)
    caption = models.CharField(max_length=200, blank=True)
    uploaded_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    telegram_message_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "memory_photo"
        ordering = ["-taken_at"]


class TagStatus(models.TextChoices):
    SUGGESTED = "suggested", gettext_lazy("Taklif")
    CONFIRMED = "confirmed", gettext_lazy("Tasdiqlangan")
    REJECTED = "rejected", gettext_lazy("Rad etilgan")


class PhotoTag(BranchScopedModel):
    photo = models.ForeignKey(MemoryPhoto, on_delete=models.CASCADE, related_name="tags")
    child = models.ForeignKey(
        "children.Child", on_delete=models.RESTRICT, related_name="photo_tags"
    )
    confidence = models.FloatField()
    # x, y, w, h — rasm o'lchamiga nisbatan 0..1 (begona bolalar yuzini xiralashtirish uchun).
    box = models.JSONField(default=list)
    status = models.CharField(max_length=12, choices=TagStatus.choices, default=TagStatus.SUGGESTED)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "photo_tag"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["photo", "child"], name="uq_photo_tag_photo_child"),
            models.CheckConstraint(
                condition=models.Q(confidence__gte=0, confidence__lte=1), name="ck_photo_tag_conf"
            ),
        ]


class ChatKind(models.TextChoices):
    GROUP = "group", gettext_lazy("Bog'cha guruhi")
    PARENT = "parent", gettext_lazy("Ota-ona")
    STAFF = "staff", gettext_lazy("Rahbar")


class TelegramChat(TenantScopedModel):
    """
    Telegram chat → tashkilot yo'nalishi.

    Bu METADATA jadvali: webhook kelganda tenant HALI noma'lum, uni
    aynan shu jadval aniqlaydi (RLS: `org OR platform`).
    """

    branch = models.ForeignKey("branches.Branch", on_delete=models.RESTRICT, related_name="+")
    chat_id = models.BigIntegerField(unique=True)
    kind = models.CharField(max_length=10, choices=ChatKind.choices)
    guardian = models.ForeignKey(
        "children.Guardian", on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    language = models.CharField(max_length=2, default="uz")
    title = models.CharField(max_length=120, blank=True)

    class Meta:
        db_table = "telegram_chat"
        ordering = ["kind", "title"]


class PairingToken(TenantScopedModel):
    """Bir martalik ulash havolasi (`t.me/bot?start=<org>.<secret>`). Xesh saqlanadi."""

    token_hash = models.CharField(max_length=64, unique=True)
    kind = models.CharField(max_length=10, choices=ChatKind.choices)
    branch = models.ForeignKey("branches.Branch", on_delete=models.RESTRICT, related_name="+")
    guardian = models.ForeignKey(
        "children.Guardian", on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "telegram_pairing"


class ScheduleKind(models.TextChoices):
    MENU = "menu", gettext_lazy("Menyu")
    MEAL = "meal", gettext_lazy("Ovqatlanish")
    ACTIVITY = "activity", gettext_lazy("Mashg'ulot")


class DayScheduleItem(BranchScopedModel):
    """Kun tartibi: menyu, ovqat vaqti, mashg'ulot. `notify_at` da ota-onaga yuboriladi."""

    kind = models.CharField(max_length=10, choices=ScheduleKind.choices)
    on_date = models.DateField(db_index=True)
    at_time = models.TimeField(null=True, blank=True)
    title = models.CharField(max_length=160)
    details = models.CharField(max_length=500, blank=True)
    notify = models.BooleanField(default=True)
    notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "day_schedule_item"
        ordering = ["on_date", "at_time", "title"]


class CameraConnection(models.TextChoices):
    EDGE = "edge", gettext_lazy("Edge-worker (RTSP)")
    WEBHOOK = "webhook", gettext_lazy("Webhook (NVR / bulut)")


class Camera(BranchScopedModel):
    name = models.CharField(max_length=80)
    location = models.CharField(max_length=120, blank=True)
    # Oqim manzili login/parolni o'z ichiga oladi — shifrlangan, javobda hech qachon qaytmaydi.
    stream_url = models.TextField(blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    # Ulanish tokenining xeshi (SHA-256). Token o'zi faqat berilgan zahoti bir marta ko'rinadi.
    ingest_token_hash = models.CharField(max_length=64, blank=True, db_index=True)
    connection = models.CharField(
        max_length=10, choices=CameraConnection.choices, default=CameraConnection.EDGE
    )
    # Kuzatuv kadri. Standart O'CHIQ: bolalar tasviri uchun egasi ongli ravishda yoqadi.
    preview_enabled = models.BooleanField(default=False)
    preview = models.ImageField(upload_to=preview_upload_path, blank=True)
    preview_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "camera"
        ordering = ["name"]


class EventKind(models.TextChoices):
    STAFF_VIOLATION = "staff_violation", gettext_lazy("Xodim qoidabuzarligi")
    CHILD_DISTRESS = "child_distress", gettext_lazy("Bola yig'layapti / kayfiyati yo'q")
    SAFETY = "safety", gettext_lazy("Xavfsizlik")
    OTHER = "other", gettext_lazy("Boshqa")


class EventSeverity(models.TextChoices):
    INFO = "info", gettext_lazy("Ma'lumot")
    WARNING = "warning", gettext_lazy("Ogohlantirish")
    CRITICAL = "critical", gettext_lazy("Jiddiy")


class EventStatus(models.TextChoices):
    NEW = "new", gettext_lazy("Yangi")
    ACKNOWLEDGED = "acknowledged", gettext_lazy("Ko'rildi")
    DISMISSED = "dismissed", gettext_lazy("Noto'g'ri signal")


class CameraEvent(BranchScopedModel):
    camera = models.ForeignKey(
        Camera, on_delete=models.SET_NULL, null=True, blank=True, related_name="events"
    )
    kind = models.CharField(max_length=20, choices=EventKind.choices)
    severity = models.CharField(
        max_length=10, choices=EventSeverity.choices, default=EventSeverity.WARNING
    )
    status = models.CharField(max_length=14, choices=EventStatus.choices, default=EventStatus.NEW)
    snapshot = models.ImageField(upload_to=event_upload_path, blank=True)
    note = models.CharField(max_length=400, blank=True)
    occurred_at = models.DateTimeField(db_index=True)
    alerted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "camera_event"
        ordering = ["-occurred_at"]
