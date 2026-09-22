"""
Eksport ishlari (docs/04 §14.2).

Nega jadval kerak: eksport uzoq davom etishi mumkin va so'rov ichida
bajarilsa, katta hisobotda brauzer kutib qoladi yoki uzilib ketadi.
Shuning uchun ish yozuv sifatida yaratiladi, fonda bajariladi va mijoz
uning holatini so'raydi.

Fayl `FileField` orqali saqlanadi — ya'ni Django'ning **storage
abstraksiyasi** ortida. Bugun u serverdagi papka; ertaga S3 bo'lganda
faqat `DEFAULT_FILE_STORAGE` o'zgaradi va bu kod tegilmaydi. Kechiktirib
kelingan PDF kvitansiya va oylik varaqasi ham xuddi shu joyni kutayotgan
edi.
"""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy

from apps.core.models import TenantScopedModel

__all__ = ["ExportStatus", "ReportExport", "REPORT_TYPES"]

# Eksport qilinadigan hisobot turlari — ro'yxat YOPIQ. Ochiq bo'lsa,
# mijoz yuborgan matn bevosita funksiya nomiga aylanardi.
REPORT_TYPES: tuple[str, ...] = (
    "revenue",
    "expenses",
    "payroll",
    "attendance",
    "debtors",
    "profit-loss",
)


class ExportStatus(models.TextChoices):
    QUEUED = "queued", gettext_lazy("Navbatda")
    RUNNING = "running", gettext_lazy("Bajarilmoqda")
    READY = "ready", gettext_lazy("Tayyor")
    FAILED = "failed", gettext_lazy("Xato")


class ReportExport(TenantScopedModel):
    """Bitta eksport so'rovi va uning natijasi."""

    report_type = models.CharField(max_length=30, choices=[(t, t) for t in REPORT_TYPES])
    params = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20, choices=ExportStatus.choices, default=ExportStatus.QUEUED
    )
    file = models.FileField(upload_to="exports/%Y/%m/", blank=True)
    row_count = models.IntegerField(default=0)
    error = models.TextField(blank=True)
    requested_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="report_exports",
        null=True,
        blank=True,
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "report_export"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="ix_export_org_created"),
        ]

    def __str__(self) -> str:
        return f"{self.report_type} ({self.status})"
