"""
Moliya domeni (docs/03 §13).

Markaziy g'oya (ADR-7, D3): **`ChildLedgerEntry` — yagona moliyaviy
haqiqat manbai.** Hisob-faktura va to'lov — bu *hujjatlar*, ular ledger
yozuvlarini yaratadi. Balans va butun Qarzdorlar moduli ledger'dan
hisoblanadi, alohida jadvalda saqlanmaydi.

Ledger qatorlari HECH QACHON yangilanmaydi va o'chirilmaydi. Xato qarshi
yozuv (`adjustment`/`refund`) bilan tuzatiladi. Bu moliyadagi 1-raqamli
xatoni — jimgina siljishni — imkonsiz qiladi.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy

from apps.core.models import BaseModel, BranchScopedModel

__all__ = [
    "TariffPlan",
    "Discount",
    "Invoice",
    "InvoiceLine",
    "Payment",
    "ChildLedgerEntry",
]


class BillingPeriod(models.TextChoices):
    MONTHLY = "monthly", gettext_lazy("Oylik")
    DAILY = "daily", gettext_lazy("Kunlik")
    TERMLY = "termly", gettext_lazy("Semestrli")


class TariffPlan(BranchScopedModel):
    """Takrorlanuvchi to'lov ta'rifi."""

    name = models.CharField(max_length=80)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    billing_period = models.CharField(
        max_length=15, choices=BillingPeriod.choices, default=BillingPeriod.MONTHLY
    )

    class Meta:
        db_table = "tariff_plan"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "name"],
                condition=models.Q(is_active=True),
                name="uq_tariff_branch_name",
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gte=0), name="ck_tariff_amount_positive"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} — {self.amount}"


class DiscountType(models.TextChoices):
    PERCENT = "percent", gettext_lazy("Foiz")
    FIXED = "fixed", gettext_lazy("Belgilangan summa")


class Discount(BranchScopedModel):
    """Bolaga biriktirilgan takrorlanuvchi chegirma (aka-uka, xodim farzandi)."""

    child = models.ForeignKey("children.Child", on_delete=models.CASCADE, related_name="discounts")
    discount_type = models.CharField(max_length=12, choices=DiscountType.choices)
    value = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=255, blank=True)
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "discount"
        ordering = ["-valid_from"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(value__gte=0), name="ck_discount_value_positive"
            ),
            # Foizli chegirma 100 dan oshsa, hisob-faktura manfiy bo'lardi.
            models.CheckConstraint(
                condition=~models.Q(discount_type="percent") | models.Q(value__lte=100),
                name="ck_discount_percent",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(valid_to__isnull=True) | models.Q(valid_to__gte=models.F("valid_from"))
                ),
                name="ck_discount_dates",
            ),
        ]

    def __str__(self) -> str:
        suffix = "%" if self.discount_type == DiscountType.PERCENT else ""
        return f"{self.value}{suffix}"


class InvoiceStatus(models.TextChoices):
    DRAFT = "draft", gettext_lazy("Qoralama")
    ISSUED = "issued", gettext_lazy("Chiqarilgan")
    PARTIALLY_PAID = "partially_paid", gettext_lazy("Qisman to'langan")
    PAID = "paid", gettext_lazy("To'langan")
    OVERDUE = "overdue", gettext_lazy("Muddati o'tgan")
    CANCELLED = "cancelled", gettext_lazy("Bekor qilingan")


class Invoice(BranchScopedModel):
    """Bir bola uchun bir davrga hisob-faktura."""

    number = models.CharField(max_length=30)
    child = models.ForeignKey("children.Child", on_delete=models.RESTRICT, related_name="invoices")
    tariff = models.ForeignKey(
        "finance.TariffPlan",
        on_delete=models.SET_NULL,
        related_name="invoices",
        null=True,
        blank=True,
    )
    period_year = models.SmallIntegerField()
    period_month = models.SmallIntegerField()

    amount_due = models.DecimalField(max_digits=12, decimal_places=2)
    # To'lovlardan keshlangan (docs/03 §8.2). Haqiqat manbai — `payment`
    # qatorlari va ledger; bu ustun faqat ro'yxatni tez ko'rsatish uchun.
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))

    status = models.CharField(
        max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.ISSUED
    )
    issued_date = models.DateField()
    due_date = models.DateField()

    class Meta:
        db_table = "invoice"
        ordering = ["-period_year", "-period_month", "number"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "number"], name="uq_invoice_number"),
            # Bir bola — bir davr — bitta hisob-faktura. Bu qisman indeks
            # oylik generatsiyani IDEMPOTENT qiladi: vazifa ikki marta
            # ishga tushsa ham ikkinchi marta hisoblanmaydi (docs/03 §13.3).
            models.UniqueConstraint(
                fields=["child", "period_year", "period_month"],
                condition=~models.Q(status="cancelled"),
                name="uq_invoice_child_period",
            ),
            models.CheckConstraint(
                condition=models.Q(amount_due__gte=0), name="ck_invoice_due_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(amount_paid__gte=0), name="ck_invoice_paid_positive"
            ),
            # Ortiqcha to'lov hisob-fakturada emas, ledger'da kredit sifatida
            # qoladi — shuning uchun bu yerda qat'iy cheklov.
            models.CheckConstraint(
                condition=models.Q(amount_paid__lte=models.F("amount_due")),
                name="ck_invoice_paid_not_over",
            ),
            models.CheckConstraint(
                condition=models.Q(due_date__gte=models.F("issued_date")),
                name="ck_invoice_due_after_issue",
            ),
            models.CheckConstraint(
                condition=models.Q(period_month__gte=1, period_month__lte=12),
                name="ck_invoice_period_month",
            ),
        ]
        indexes = [
            models.Index(fields=["child", "status"], name="ix_invoice_child_status"),
            models.Index(
                fields=["organization", "branch", "period_year", "period_month"],
                name="ix_invoice_org_br_period",
            ),
            models.Index(
                fields=["branch", "due_date"],
                condition=models.Q(status__in=["issued", "partially_paid"]),
                name="ix_invoice_overdue",
            ),
        ]

    def __str__(self) -> str:
        return self.number

    @property
    def amount_outstanding(self) -> Decimal:
        return self.amount_due - self.amount_paid


class InvoiceLine(BaseModel):
    """
    Hisob-faktura satri.

    `organization_id` yo'q: satr hisob-fakturaga `CASCADE` bilan bog'langan
    va u orqali tenant'ga tegishli. Bu qoidadan istisno emas — satrning
    o'z endpointi yo'q va u hech qachon mustaqil so'ralmaydi.
    """

    invoice = models.ForeignKey("finance.Invoice", on_delete=models.CASCADE, related_name="lines")
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1"))
    unit_amount = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "invoice_line"
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="ck_invoice_line_qty"),
        ]

    def __str__(self) -> str:
        return f"{self.description} × {self.quantity}"


class PaymentMethod(models.TextChoices):
    CASH = "cash", gettext_lazy("Naqd")
    CARD = "card", gettext_lazy("Karta")
    BANK_TRANSFER = "bank_transfer", gettext_lazy("Bank o'tkazmasi")
    ONLINE = "online", gettext_lazy("Onlayn")


class Payment(BranchScopedModel):
    """
    Pul kelib tushgan hodisa (docs/03 §13.5).

    To'lov **o'zgarmas**: tuzatish `reverse_payment()` orqali qarshi yozuv
    bilan qilinadi, hech qachon `UPDATE`/`DELETE` bilan emas (D3). Kassir
    xato summa kiritsa, uni "tahrirlash" tarixni yo'q qilardi — kim,
    qachon, qanchani qabul qilgani ko'rinmay qolardi.
    """

    invoice = models.ForeignKey(
        "finance.Invoice",
        on_delete=models.RESTRICT,
        related_name="payments",
        null=True,
        blank=True,
        help_text="NULL = hisob-fakturaga bog'lanmagan avans",
    )
    # Denormalizatsiya: bola bo'yicha ko'chirma hisob-fakturaga
    # bog'lanmagan to'lovlarni ham ko'rsatishi kerak.
    child = models.ForeignKey("children.Child", on_delete=models.RESTRICT, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    reference = models.CharField(max_length=100, blank=True)
    paid_at = models.DateTimeField()
    received_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="payments_received",
        null=True,
        blank=True,
    )
    receipt_path = models.CharField(max_length=255, blank=True)

    # Qaytarilgan to'lov: asl qator qoladi, faqat belgilanadi.
    reversed_at = models.DateTimeField(null=True, blank=True)
    reversal_reason = models.CharField(max_length=255, blank=True)

    # Takroriy yuborishdan himoya (P1-003).
    #
    # Hisob-fakturani qulflash ORTIQCHA to'lovni to'xtatadi, lekin
    # TAKRORIY to'lovni emas: kassir tugmani ikki marta bossa yoki
    # tarmoq so'rovni qayta yuborsa, ikkita mustaqil to'lov yozilardi.
    # Avans to'lovda (hisob-fakturasiz) esa umuman hech qanday to'siq
    # yo'q edi — ikki marta bosish bolaning balansini ikki barobar
    # oshirardi.
    #
    # Kalit mijozdan keladi (`Idempotency-Key` sarlavhasi) va u bitta
    # FOYDALANUVCHI HARAKATINI bildiradi, bitta so'rovni emas: qayta
    # yuborilgan so'rov o'sha kalit bilan keladi va mavjud to'lovni
    # qaytaradi.
    idempotency_key = models.CharField(max_length=64, blank=True, editable=False)

    class Meta:
        db_table = "payment"
        ordering = ["-paid_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="ck_payment_amount_positive"
            ),
            # Qisman indeks: kalitsiz to'lovlar (import, seed, eski
            # yozuvlar) cheklovga tushmaydi. Poyga holatida ikkinchi
            # `INSERT` shu yerda to'xtaydi — tekshiruv ilovada emas,
            # BAZADA, ya'ni ikkita so'rov bir vaqtda kelsa ham ishlaydi.
            models.UniqueConstraint(
                fields=["organization", "idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="uq_payment_idempotency",
            ),
        ]
        indexes = [
            models.Index(fields=["child", "-paid_at"], name="ix_payment_child_paid"),
            models.Index(
                fields=["organization", "branch", "-paid_at"], name="ix_payment_org_br_paid"
            ),
            models.Index(fields=["invoice"], name="ix_payment_invoice"),
        ]

    def __str__(self) -> str:
        return f"{self.amount} ({self.method})"

    @property
    def is_reversed(self) -> bool:
        return self.reversed_at is not None


class EntryType(models.TextChoices):
    CHARGE = "charge", gettext_lazy("Hisoblangan")
    PAYMENT = "payment", gettext_lazy("To'lov")
    DISCOUNT = "discount", gettext_lazy("Chegirma")
    ADJUSTMENT = "adjustment", gettext_lazy("Tuzatish")
    REFUND = "refund", gettext_lazy("Qaytarish")


class Direction(models.TextChoices):
    DEBIT = "debit", gettext_lazy("Debet")
    CREDIT = "credit", gettext_lazy("Kredit")


class SourceType(models.TextChoices):
    INVOICE = "invoice", gettext_lazy("Hisob-faktura")
    PAYMENT = "payment", gettext_lazy("To'lov")
    DISCOUNT = "discount", gettext_lazy("Chegirma")
    MANUAL = "manual", gettext_lazy("Qo'lda")


class ChildLedgerEntry(BranchScopedModel):
    """
    Append-only moliyaviy ledger — YAGONA haqiqat manbai (ADR-7, D3).

    Bola balansi = Σ debet − Σ kredit. `> 0` bo'lsa bola qarzdor.

    Bu jadvalda `UPDATE`/`DELETE` **yo'q**. Xato qarshi yozuv bilan
    tuzatiladi. Sabab: yangilanadigan balans ustuni jimgina siljiydi va
    siljish qachon boshlanganini hech kim ayta olmaydi. Ledger'da esa har
    bir tiyin qayerdan kelgani ko'rinadi.

    `SoftDeleteModel` dan meros olsa ham `is_active` ishlatilmaydi — bu
    jadval uchun o'chirish tushunchasi yo'q.
    """

    child = models.ForeignKey(
        "children.Child", on_delete=models.RESTRICT, related_name="ledger_entries"
    )
    entry_type = models.CharField(max_length=15, choices=EntryType.choices)
    direction = models.CharField(max_length=6, choices=Direction.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    source_id = models.UUIDField(null=True, blank=True)

    occurred_at = models.DateTimeField(db_index=True)
    description = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="ledger_entries",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "child_ledger_entry"
        ordering = ["-occurred_at", "-created_at"]
        constraints = [
            # Summa har doim MUSBAT; ishora `direction` dan keladi.
            # Manfiy summaga ruxsat berilsa, bir xil harakatni ikki xil
            # yozish mumkin bo'lardi va yig'indilar taqqoslanmas edi.
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="ck_ledger_amount_positive"
            ),
        ]
        indexes = [
            models.Index(fields=["child", "occurred_at"], name="ix_ledger_child"),
            models.Index(
                fields=["organization", "source_type", "source_id"],
                name="ix_ledger_source",
            ),
        ]

    def __str__(self) -> str:
        sign = "+" if self.direction == Direction.DEBIT else "−"
        return f"{sign}{self.amount} ({self.entry_type})"

    @property
    def signed_amount(self) -> Decimal:
        return self.amount if self.direction == Direction.DEBIT else -self.amount
