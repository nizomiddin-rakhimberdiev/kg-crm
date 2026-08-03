"""
Tizim sozlamalari (docs/03 §18).

JSONB kalit-qiymat: yangi sozlama qo'shish migratsiya talab qilmaydi.
Feature flag'lar ham shu yerda — kelajakdagi modullarni sxemani
o'zgartirmasdan yoqib/o'chirish uchun.
"""

from __future__ import annotations

from django.db import models

from apps.core.models import TenantScopedModel

__all__ = ["SystemSetting"]


class SystemSetting(TenantScopedModel):
    """
    Sozlama qiymati.

    Aniqlash tartibi: filialga xos qiymat global (branch=NULL) qiymatni
    ustidan qoplaydi. Shu sababli ikkita alohida unikal cheklov kerak —
    Postgres'da `NULL` qiymatlar bir-biriga teng emas, ya'ni oddiy
    `UNIQUE (key, branch)` global qatorlarning takrorlanishiga yo'l
    qo'yardi.
    """

    key = models.CharField(max_length=80)
    value = models.JSONField()
    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.CASCADE,
        related_name="settings",
        null=True,
        blank=True,
    )
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "system_setting"
        ordering = ["key"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "key", "branch"], name="uq_setting_key_branch"
            ),
            models.UniqueConstraint(
                fields=["organization", "key"],
                condition=models.Q(branch__isnull=True),
                name="uq_setting_key_global",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.key}={self.value}"
