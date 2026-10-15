"""
Hujjat bilan tasdiqlangan kelmaslik va bayram kalendari (ADR-19).

Eng muhim qaror shu faylda: **da'vo davomat jadvalidan KELIB CHIQMAYDI.**
Agar hisob-kitob davomatdan o'qiganida, uxlab qolgan bola ham chegirma
olib ketardi va bog'chaning daromadi o'z-o'zidan, jimgina kamayardi —
registr belgilayotgan tarbiyachi buni bilmagan holda pul harakatlantirgan
bo'lardi.

Pul faqat dalil asosida harakat qiladi, shuning uchun da'vo o'zining
yozuvi: hujjat turi, kunlar oralig'i, tasdiqlash va u bergan raqam.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from pathlib import PurePosixPath

from django.db import models
from django.utils.translation import gettext_lazy

from apps.core.models import BranchScopedModel, TenantScopedModel

__all__ = ["AbsenceClaim", "AbsenceKind", "ClaimKind", "ClaimStatus", "Holiday", "RefundMode"]


class Holiday(TenantScopedModel):
    """
    Bog'cha yopiq kun.

    **Tashkilot darajasida, filialda emas:** bayram milliy, va uch
    filialli tashkilotga Navro'zni uch marta yozdirish — uchta har xil
    javob olish demak.

    Ro'yxat oldindan to'ldirilmaydi: diniy bayramlar har yili siljiydi
    va qarorlar atrofdagi ish kunlarini ko'chiradi. Kodga yozilgan
    ro'yxat keyingi bahorda noto'g'ri bo'lardi va buni hech kim
    ota-ona o'ziga tegishli bo'lmagan kun uchun pul olgunicha
    sezmasdi.
    """

    holiday_date = models.DateField()
    name = models.CharField(max_length=80)

    class Meta:
        db_table = "holiday"
        ordering = ["-holiday_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "holiday_date"], name="uq_holiday_org_date"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.holiday_date} — {self.name}"


class ClaimKind(models.TextChoices):
    """Tizim bilan keladigan ikki tur — kodlari. Qolganlari `AbsenceKind` da."""

    MEDICAL = "medical", gettext_lazy("Shifokor maʼlumotnomasi")
    PARENTAL = "parental", gettext_lazy("Ota-ona arizasi")


class RefundMode(models.TextChoices):
    FULL_RATE = "full_rate", gettext_lazy("Toʻliq kunlik stavka")
    FIXED_PER_DAY = "fixed_per_day", gettext_lazy("Kuniga qatʼiy summa")
    NONE = "none", gettext_lazy("Qaytarilmaydi")


class AbsenceKind(TenantScopedModel):
    """
    Qayta hisob turi va uning qoidasi (Bosqich 12.3, brif §2).

    Ilgari ikki qotirilgan tur bor edi va ikkalasi to'liq stavka qaytarardi.
    Endi tur — tashkilotning MA'LUMOTI: qaytarish usuli, kuniga summa,
    minimal kunlar va "shuncha kundan boshlab to'liq stavka" chegarasi.

    Maʼlumotnoma qoidasi shu ikki maydonning birikmasi: `fixed_per_day`
    (ovqat puli) + `full_rate_from_days = 3`. 1–2 kun — ovqat puli; 3 va undan
    ko'p — HAMMA kunlar uchun to'liq stavka.

    `daily_amount` bo'sh bo'lsa — `contracts.daily_meal_fee` sozlamasi
    (shartnoma shablonidagi o'sha ovqat puli: ikkinchi nusxa bo'lmasin).
    """

    code = models.SlugField(max_length=40)
    name = models.CharField(max_length=80)
    refund_mode = models.CharField(max_length=15, choices=RefundMode.choices)
    daily_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    min_days = models.PositiveSmallIntegerField(default=1)
    full_rate_from_days = models.PositiveSmallIntegerField(null=True, blank=True)
    requires_document = models.BooleanField(default=False)

    class Meta:
        db_table = "absence_kind"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                condition=models.Q(is_active=True),
                name="uq_absence_kind_code",
            ),
            models.CheckConstraint(
                condition=models.Q(daily_amount__isnull=True) | models.Q(daily_amount__gte=0),
                name="ck_absence_kind_amount",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class ClaimStatus(models.TextChoices):
    PENDING = "pending", gettext_lazy("Kutilmoqda")
    APPROVED = "approved", gettext_lazy("Tasdiqlangan")
    REJECTED = "rejected", gettext_lazy("Rad etilgan")
    APPLIED = "applied", gettext_lazy("Hisob-fakturaga tushdi")


def absence_document_path(instance: AbsenceClaim, filename: str) -> str:
    """
    `media/{organization}/absence/{uuid}.{ext}`

    Fayl nomi UUID: yuklangan nom saqlansa, boshqa oilaning hujjat
    nomini taxmin qilish yo'li ochilardi, va bir xil nomli fayllar
    ("spravka.pdf" — hamma shunday nomlaydi) to'qnashardi.
    Kengaytma qoladi: brauzer `Content-Type` ni shundan aniqlaydi.
    """
    suffix = PurePosixPath(filename).suffix.lower() or ".pdf"
    return f"{instance.organization_id}/absence/{uuid.uuid4()}{suffix}"


class AbsenceClaim(BranchScopedModel):
    """
    Kelmagan kunlar uchun to'lovdan qaytarish da'vosi (docs/03 §12.2).

    Raqamlar TASDIQLASH paytida muzlatiladi — yaratishda ham,
    qo'llashda ham emas: keyingi oy o'zgargan tarif allaqachon
    berilgan chegirmani qimirlatmasligi kerak.
    """

    child = models.ForeignKey(
        "children.Child", on_delete=models.RESTRICT, related_name="absence_claims"
    )
    # `AbsenceKind.code` — tur endi ma'lumot, ro'yxat emas (Bosqich 12.3).
    kind = models.CharField(max_length=40)
    date_from = models.DateField()
    date_to = models.DateField()
    document_no = models.CharField(max_length=60, blank=True)
    # Spravka yoki arizaning o'zi (PLAN 7.7).
    #
    # Hujjat raqami yetarli emas edi: bir yildan keyin "shu kunlar
    # nega bekor qilingan?" degan savolga javob faqat qog'oz papkada
    # qolardi. ADR-19 bo'yicha pulni AYNAN hujjat harakatga keltiradi,
    # shuning uchun hujjatning o'zi ham shu yerda turishi mantiqan
    # to'g'ri. Ixtiyoriy: bog'cha arizani qog'ozda saqlashni afzal
    # ko'rsa, oqim avvalgidek ishlaydi.
    document_file = models.FileField(upload_to=absence_document_path, blank=True)
    note = models.CharField(max_length=255, blank=True)

    status = models.CharField(
        max_length=10, choices=ClaimStatus.choices, default=ClaimStatus.PENDING
    )

    # Tasdiqlashdagi surat.
    billable_days = models.SmallIntegerField(default=0)
    daily_rate = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    credit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    # Qaysi qoida bilan hisoblangan: `full_rate` · `fixed_per_day` · `none`.
    # Faktura qatoridagi formula va "Nega?" shundan.
    basis = models.CharField(max_length=15, blank=True, default="")

    approved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="absence_claims_approved",
        null=True,
        blank=True,
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=255, blank=True)

    # Qaysi hisob-faktura uni yutdi — ikki marta qo'llashni imkonsiz qiladi.
    applied_invoice = models.ForeignKey(
        "finance.Invoice",
        on_delete=models.RESTRICT,
        related_name="absence_credits",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="absence_claims_created",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "absence_claim"
        ordering = ["-date_from"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(date_to__gte=models.F("date_from")),
                name="ck_absence_claim_dates",
            ),
            models.CheckConstraint(
                condition=models.Q(billable_days__gte=0) & models.Q(credit_amount__gte=0),
                name="ck_absence_claim_amounts",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "child", "date_from"], name="ix_claim_org_child_from"
            ),
            models.Index(
                fields=["organization", "status"],
                name="ix_claim_org_pending",
                condition=models.Q(status="approved"),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.child_id}: {self.date_from}…{self.date_to}"
