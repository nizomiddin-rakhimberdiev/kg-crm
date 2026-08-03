"""
Filial — tashkilot ichidagi operatsion doira (docs/03 §10.2).

Bu tenancy chegarasi EMAS (ADR-9): mijozning o'z Org Owner'i barcha
filiallarini o'qiy oladi. Tenancy chegarasi — `organization`.
"""

from __future__ import annotations

from django.db import models

from apps.core.models import TenantScopedModel

__all__ = ["Branch"]


class Branch(TenantScopedModel):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    currency = models.CharField(max_length=3, default="UZS")
    timezone = models.CharField(max_length=40, default="Asia/Tashkent")

    class Meta:
        db_table = "branch"
        ordering = ["name"]
        constraints = [
            # Kod tashkilot ICHIDA unikal, global emas: ikki turli bog'cha
            # bemalol `MAIN` ishlatishi mumkin (docs/03 §6.2).
            models.UniqueConstraint(fields=["organization", "code"], name="uq_branch_org_code"),
        ]
        verbose_name_plural = "branches"

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"
