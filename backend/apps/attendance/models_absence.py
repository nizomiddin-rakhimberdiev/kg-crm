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

from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy

from apps.core.models import BranchScopedModel, TenantScopedModel

__all__ = ["AbsenceClaim", "ClaimKind", "ClaimStatus", "Holiday"]


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
    MEDICAL = "medical", gettext_lazy("Shifokor maʼlumotnomasi")
    PARENTAL = "parental", gettext_lazy("Ota-ona arizasi")


class ClaimStatus(models.TextChoices):
    PENDING = "pending", gettext_lazy("Kutilmoqda")
    APPROVED = "approved", gettext_lazy("Tasdiqlangan")
    REJECTED = "rejected", gettext_lazy("Rad etilgan")
    APPLIED = "applied", gettext_lazy("Hisob-fakturaga tushdi")


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
    kind = models.CharField(max_length=10, choices=ClaimKind.choices)
    date_from = models.DateField()
    date_to = models.DateField()
    document_no = models.CharField(max_length=60, blank=True)
    note = models.CharField(max_length=255, blank=True)

    status = models.CharField(
        max_length=10, choices=ClaimStatus.choices, default=ClaimStatus.PENDING
    )

    # Tasdiqlashdagi surat.
    billable_days = models.SmallIntegerField(default=0)
    daily_rate = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    credit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))

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
