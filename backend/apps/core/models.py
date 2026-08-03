"""
Umumiy yadro modellari (docs/03 §4 — Standard Base Columns).

Ierarxiya:
    BaseModel          — id (UUID), created_at, updated_at
    SoftDeleteModel    — + is_active (master data uchun, D5)
    TenantScopedModel  — + organization_id (HAR BIR operatsion jadval, P10)

`branch_id` ustuni `branches` app'i bilan birga Sprint 1 da qo'shiladi
(hozir `branch` jadvali mavjud emas, shuning uchun FK yozib bo'lmaydi).
"""

from __future__ import annotations

import uuid

from django.db import models

from apps.core.managers import TenantManager, UnscopedManager

__all__ = ["BaseModel", "SoftDeleteModel", "TenantScopedModel", "BranchScopedModel"]


class BaseModel(models.Model):
    """UUID kalit + vaqt tamg'alari. Barcha jadvallar shundan meros oladi."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(BaseModel):
    """
    Master/reference ma'lumot uchun yumshoq o'chirish (D5).

    Moliyaviy va append-only jadvallar bundan meros OLMAYDI — ular umuman
    o'chirilmaydi (docs/03 §7).
    """

    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        abstract = True


class TenantScopedModel(SoftDeleteModel):
    """
    Tenant chegarasini olib yuruvchi asosiy model (ADR-9, P10).

    `objects` — joriy tashkilot bilan cheklangan (default).
    `all_objects` — filtrsiz; faqat admin/migratsiya/platforma uchun.

    `organization_id` ataylab denormalizatsiya qilingan: `branch` orqali JOIN
    qilinmaydi. Bitta qo'shimcha UUID evaziga har bir filtr bir qadamda
    bajariladi va unutilgan JOIN sabab ma'lumot sizib chiqa olmaydi
    (docs/02 §12.1).
    """

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.RESTRICT,  # docs/03 §21: tenant ildizidan CASCADE yo'q
        related_name="%(app_label)s_%(class)s_set",
        db_index=True,
        editable=False,  # insert'dan keyin o'zgarmaydi (DB trigger ham qo'riqlaydi)
    )

    objects = TenantManager()
    all_objects = UnscopedManager()

    class Meta:
        abstract = True


class BranchScopedModel(TenantScopedModel):
    """
    Tashkilot ichidagi filialga bog'langan model (P6).

    Diqqat — ikki chegara turli tabiatga ega:
    `organization` xavfsizlik chegarasi (hech kim buzib o'tolmaydi),
    `branch` esa biznes doirasi: Org Owner o'z tashkilotining barcha
    filiallarini o'qiydi, qolgan rollar o'z filiali bilan cheklangan.
    Shuning uchun branch filtri baza queryset'da emas, view/selector
    qatlamida qo'llanadi (docs/02 §11.3).
    """

    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.RESTRICT,
        related_name="%(app_label)s_%(class)s_set",
        db_index=True,
    )

    class Meta:
        abstract = True
