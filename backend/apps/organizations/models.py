"""
Tenancy ildizi (docs/03 §10.1, ADR-9).

Bitta to'lovchi mijoz = bitta bog'cha biznesi, bir yoki bir nechta filial bilan.
Bazadagi HAR BIR operatsion qator shu yerga ishora qiladi.
"""

from __future__ import annotations

import uuid
from pathlib import PurePosixPath

from django.db import models

from apps.core.models import SoftDeleteModel

__all__ = ["Organization", "organization_logo_path"]


def organization_logo_path(instance: Organization, filename: str) -> str:
    """
    `media/{organization}/brand/{uuid}.{ext}`

    Fayl nomi UUID: yuklangan nom saqlansa, u boshqa mijozning fayl
    nomini taxmin qilish yo'lini ochadi va bir xil nomli fayllar
    to'qnashuviga olib keladi (`accounts.user_photo_path` bilan bir
    xil mantiq). Kengaytma saqlanadi — brauzer uni `Content-Type`
    aniqlashda ishlatadi.
    """
    suffix = PurePosixPath(filename).suffix.lower() or ".png"
    return f"{instance.pk or 'new'}/brand/{uuid.uuid4()}{suffix}"


class Organization(SoftDeleteModel):
    """
    Mijoz tashkiloti — tenancy va billing chegarasi.

    Diqqat: `TenantScopedModel` dan meros OLMAYDI — bu modelning o'zi
    tenancy ildizi, uning ustida boshqa tenant chegarasi yo'q.
    """

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=50, unique=True)

    # Bog'chaning logotipi (PLAN 4.6).
    #
    # Mudira kun bo'yi O'Z bog'chasining nomini va belgisini ko'rib
    # turadi — umumiy qalpoq ikonkasi emas. Bo'sh bo'lsa ekran
    # bog'cha nomining bosh harfini ko'rsatadi, ya'ni logotip
    # YUKLASH shart emas va hech qanday bo'sh joy qolmaydi.
    logo = models.ImageField(upload_to=organization_logo_path, blank=True)

    # Yuridik shaxs ma'lumotlari — hisob-faktura va akt uchun (docs/01 §10).
    legal_name = models.CharField(max_length=255, blank=True)
    tax_id = models.CharField("INN/STIR", max_length=20, blank=True)

    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20, blank=True)

    country = models.CharField(max_length=2, default="UZ")
    locale = models.CharField(max_length=10, default="uz")

    # Trial soati shu paytdan hisoblanadi, ro'yxatdan o'tgan paytdan emas:
    # bog'cha qiymatni faqat ma'lumotlari kiritilgandan keyin sezadi
    # (docs/01 §4.4).
    onboarded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "organization"
        ordering = ["name"]
        verbose_name = "organization"
        verbose_name_plural = "organizations"

    def __str__(self) -> str:
        return self.name
