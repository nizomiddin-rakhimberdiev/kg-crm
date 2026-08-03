"""
Bildirishnomalar (docs/03 §17).

Kanaldan mustaqil markaz: hozir SMS, keyin Telegram/Email. Yangi kanal
qo'shish — yangi **adapter**, tizimni qayta yozish emas (P2, docs/02 §17).
"""

from __future__ import annotations

from django.db import models

from apps.core.models import BranchScopedModel

__all__ = [
    "NotificationTemplate",
    "Notification",
    "Channel",
    "NotificationStatus",
    "TemplateCode",
]


class Channel(models.TextChoices):
    SMS = "sms", "SMS"
    TELEGRAM = "telegram", "Telegram"
    EMAIL = "email", "Email"


class TemplateCode(models.TextChoices):
    """MVP shablonlari — ular signup'da seed qilinadi."""

    PAYMENT_RECEIVED = "payment_received", "To'lov qabul qilindi"
    DEBT_REMINDER = "debt_reminder", "Qarz eslatmasi"
    ABSENCE_NOTICE = "absence_notice", "Kelmagani haqida"
    CUSTOM = "custom", "Erkin xabar"


class NotificationTemplate(BranchScopedModel):
    code = models.CharField(max_length=50, choices=TemplateCode.choices)
    channel = models.CharField(max_length=12, choices=Channel.choices, default=Channel.SMS)
    subject = models.CharField(max_length=150, blank=True)
    body = models.TextField(help_text="{o'zgaruvchi} shaklidagi o'rinbosarlar bilan")
    # Shablon filialga xos bo'lishi SHART EMAS — `NULL` tashkilotning
    # barcha filiallariga tegishli degani. Shu sababli bazaviy sinfdagi
    # majburiy `branch` bu yerda ixtiyoriyga o'zgartiriladi.
    branch = models.ForeignKey(  # type: ignore[assignment]
        "branches.Branch",
        on_delete=models.CASCADE,
        related_name="notification_templates",
        null=True,
        blank=True,
        help_text="NULL = tashkilotning barcha filiallariga",
    )

    class Meta:
        db_table = "notification_template"
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code", "channel", "branch"],
                name="uq_template_code_channel_branch",
            ),
            models.UniqueConstraint(
                fields=["organization", "code", "channel"],
                condition=models.Q(branch__isnull=True),
                name="uq_template_code_channel_global",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} ({self.channel})"


class NotificationStatus(models.TextChoices):
    QUEUED = "queued", "Navbatda"
    SENT = "sent", "Yuborildi"
    DELIVERED = "delivered", "Yetkazildi"
    FAILED = "failed", "Muvaffaqiyatsiz"
    CANCELLED = "cancelled", "Bekor qilindi"


class Notification(BranchScopedModel):
    """
    Bir oluvchi uchun bitta yuborish yozuvi.

    `recipient_address` va `rendered_body` — SNAPSHOT. Vasiy telefonini
    keyin o'zgartirsa yoki shablon tahrirlansa, jurnalda AYNAN nima va
    qayerga yuborilgani ko'rinib turishi kerak: "men bunday xabar
    olmaganman" degan bahsga javob shu yerda.
    """

    template = models.ForeignKey(
        "notifications.NotificationTemplate",
        on_delete=models.SET_NULL,
        related_name="notifications",
        null=True,
        blank=True,
    )
    guardian = models.ForeignKey(
        "children.Guardian",
        on_delete=models.SET_NULL,
        related_name="notifications",
        null=True,
        blank=True,
    )
    channel = models.CharField(max_length=12, choices=Channel.choices)
    recipient_address = models.CharField(max_length=120)
    rendered_body = models.TextField()

    status = models.CharField(
        max_length=12, choices=NotificationStatus.choices, default=NotificationStatus.QUEUED
    )
    provider_message_id = models.CharField(max_length=120, blank=True)
    retry_count = models.SmallIntegerField(default=0)
    error = models.TextField(blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notification"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "status", "-created_at"], name="ix_notification_org_status"
            ),
            models.Index(fields=["guardian", "-created_at"], name="ix_notification_guardian"),
            # Dispatcher'ning ish ro'yxati — faqat navbatdagilar.
            models.Index(
                fields=["scheduled_for"],
                condition=models.Q(status="queued"),
                name="ix_notification_pending",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.channel} → {self.recipient_address} ({self.status})"
