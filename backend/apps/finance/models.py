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
    "PaymentAllocation",
    "ChildLedgerEntry",
    "MonthClose",
    "Refund",
    "PaymentSettlement",
    "TRANSIT_METHODS",
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


class BenefitKind(models.TextChoices):
    """
    Imtiyoz turi (Bosqich 12.2). Toifa FAQAT shu maydon — rang ham, erkin
    matn ham emas (brif: "imtiyoz toifasi faqat rang bilan belgilanadi").

    `custom` dan boshqa turlarning qiymati yozuvda emas, SOZLAMADA
    (`benefits.*`): bog'cha "xodim farzandi 50%" ni 40% ga o'zgartirsa,
    bu siyosat, va u keyingi oydan barcha shunday bolalarga tegadi.
    `sibling` qo'lda kiritilmaydi — hisoblagich oiladan o'zi chiqaradi.
    """

    SIBLING = "sibling", gettext_lazy("Aka-uka")
    STAFF_CHILD = "staff_child", gettext_lazy("Xodim farzandi")
    LOW_INCOME = "low_income", gettext_lazy("Kam taʼminlangan")
    FULL = "full", gettext_lazy("Toʻliq imtiyoz")
    CUSTOM = "custom", gettext_lazy("Boshqa")


class Discount(BranchScopedModel):
    """
    Bolaga biriktirilgan imtiyoz — turi, sababi va muddati bilan.

    Joyida TAHRIRLANMAYDI (Bosqich 12.2): o'zgarish — eskisini tugatish
    (`valid_to`) va yangisini yozish. Shunda "kim, qachon, qancha va nega"
    tarixi o'zi saqlanadi.
    """

    child = models.ForeignKey("children.Child", on_delete=models.CASCADE, related_name="discounts")
    kind = models.CharField(max_length=20, choices=BenefitKind.choices, default=BenefitKind.CUSTOM)
    # `custom` uchun qiymat shu yerda; boshqa turlarda `benefits.*` sozlamasidan.
    discount_type = models.CharField(max_length=12, choices=DiscountType.choices)
    value = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=255, blank=True)
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

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
    PARTIALLY_PAID = "partially_paid", gettext_lazy("Qisman toʻlangan")
    PAID = "paid", gettext_lazy("Toʻlangan")
    OVERDUE = "overdue", gettext_lazy("Muddati oʻtgan")
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
    # Bosqich 12.1: qator turi (`base`, `benefit`, `proration`, `pause`,
    # `credit`, `correction`) va uni keltirib chiqargan formula —
    # "3 050 000 × 8 / 21 = 1 162 000". "Nega?" va oylik yig'ma shu
    # ikkisini o'qiydi; matndan raqam qidirilmaydi.
    kind = models.CharField(max_length=20, blank=True, default="")
    formula = models.CharField(max_length=255, blank=True, default="")
    # `benefit` qatori uchun: qaysi imtiyoz va uning turi (Bosqich 12.2).
    # "Imtiyozlar" hisoboti shu ikkisidan quriladi — matndan emas.
    benefit_kind = models.CharField(max_length=20, blank=True, default="")
    discount = models.ForeignKey(
        "finance.Discount",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoice_lines",
    )
    # Qayta hisob qatori qaysi arizadan (Bosqich 12.6): oylik yig'ma
    # qayta hisoblarni TURI bo'yicha (ma'lumotnoma — ovqat puli / to'liq,
    # ariza) aynan shu qatorlardan ajratadi, matndan taxmin qilmasdan.
    absence_claim = models.ForeignKey(
        "attendance.AbsenceClaim",
        on_delete=models.SET_NULL,
        related_name="invoice_lines",
        null=True,
        blank=True,
    )
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
    """
    Bog'cha haqiqatan pul oladigan to'rt yo'l (docs/03 §13.5).

    `card` → `terminal` (2026-09-30): mijozning lug'ati *naqd / terminal
    / o'tkazma / Payme-Click*, va "Terminal" deb ko'rsatiladigan `card`
    qiymati — ertami-kechmi hisobotga yetib boradigan mayda yolg'on.
    """

    CASH = "cash", gettext_lazy("Naqd")
    TERMINAL = "terminal", gettext_lazy("Terminal")
    BANK_TRANSFER = "bank_transfer", gettext_lazy("Oʻtkazma")
    CLICK = "click", "Click"
    PAYME = "payme", "Payme"
    # Xodim farzandining to'lovi oyligidan ushlanadi (Bosqich 12.4): pul
    # hech qaysi qopga TUSHMAYDI — u oylik to'lanayotganda kassadan
    # chiqmay qoladi. Shuning uchun `employee` majburiy.
    PAYROLL = "payroll", gettext_lazy("Oylikdan ushlash")
    # Eski birlashgan usul — 2026-10-15 gacha yozilgan to'lovlar uchun.
    # Yangi to'lov uni tanlay olmaydi (`NEW_PAYMENT_METHODS`): hisobot
    # Click va Payme'ni alohida ko'rsatishi kerak.
    ONLINE = "online", gettext_lazy("Payme / Click")


#: Yangi to'lov uchun tanlanadigan usullar — eski `online` siz.
NEW_PAYMENT_METHODS = [
    (value, label) for value, label in PaymentMethod.choices if value != PaymentMethod.ONLINE
]


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

    # --- Bosqich 12.4: kim to'ladi, nega shu sana, nega shu oy ---
    #
    # To'lovchi — bolaning vasiysi. Ism ham SURATGA olinadi: vasiy keyin
    # o'chirilsa ham kvitansiya "kim to'lagan" degan savolga javob beradi.
    payer = models.ForeignKey(
        "children.Guardian",
        on_delete=models.SET_NULL,
        related_name="payments",
        null=True,
        blank=True,
    )
    payer_name = models.CharField(max_length=255, blank=True)
    # `payroll` usulida — oyligidan ushlanadigan xodim.
    employee = models.ForeignKey(
        "hr.Employee",
        on_delete=models.RESTRICT,
        related_name="tuition_payments",
        null=True,
        blank=True,
    )
    # 60 kundan (sozlama) eski sana — faqat sabab bilan.
    backdate_reason = models.CharField(max_length=255, blank=True)
    # Kassir eng eski qarzni chetlab o'tib boshqa oyni tanlasa.
    allocation_reason = models.CharField(max_length=255, blank=True)

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

    # Bitta kassir HARAKATIDA yozilgan qatorlar shu kalitni bo'lishadi
    # (docs/03 §13.5a).
    #
    # Ota-ona 1 400 000 ni naqd, 100 000 ni terminalda to'lasa — bu
    # bitta hodisa va ikkita to'lov. Usulni qatorning bir qismi deb
    # qoldirish `daily_cash_summary`, usul diagrammasi va kassa
    # qoplarining hammasini o'zgarishsiz ishlatadi; to'plam esa faqat
    # EKRANGA kerak: "menga o'sha bitta harakatni ko'rsat".
    batch_id = models.UUIDField(null=True, blank=True, editable=False)

    class Meta:
        db_table = "payment"
        ordering = ["-paid_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="ck_payment_amount_positive"
            ),
            # docs/03 §13.5 buni talab qilardi, lekin u hech qachon
            # bazaga qo'yilmagan edi: `method` faqat serializer
            # darajasida tekshirilardi, ya'ni servis orqali kelgan
            # noto'g'ri qiymat jimgina yozilaverardi.
            models.CheckConstraint(
                condition=models.Q(
                    method__in=[
                        "cash",
                        "terminal",
                        "bank_transfer",
                        "click",
                        "payme",
                        "payroll",
                        "online",
                    ]
                ),
                name="ck_payment_method_known",
            ),
            # Oylikdan ushlash — xodimsiz bo'lmaydi, xodim esa faqat shu
            # usulda (boshqa usulda u ma'nosiz va hisobotni chalg'itadi).
            models.CheckConstraint(
                condition=(
                    models.Q(method="payroll", employee__isnull=False)
                    | (~models.Q(method="payroll") & models.Q(employee__isnull=True))
                ),
                name="ck_payment_payroll_employee",
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
            # Qisman indeks: to'plamsiz (eski va yakka) to'lovlar
            # indeksni shishirmasin — ular ko'pchilikni tashkil qiladi.
            models.Index(
                fields=["batch_id"],
                name="ix_payment_batch",
                condition=models.Q(batch_id__isnull=False),
            ),
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


class PaymentAllocation(BranchScopedModel):
    """
    Qaysi pul qaysi hisob-fakturani yopgani (PLAN 1.2, Q1).

    **Nega bu jadval kerak bo'ldi.** Ilgari bog'lanish `payment.invoice`
    ustunida edi, ya'ni bitta to'lov faqat BITTA hisob-fakturaga tegishli
    bo'la olardi. Haqiqatda esa ota-ona bir marta 3 000 000 keltiradi va
    u ikki oyni yopadi; yoki fakturadan oldin avans to'laydi va pul
    keyinchalik yozilgan hujjatga tegishli bo'lib qoladi.
    Bog'lanish yo'qligi sabab avans hech qaysi fakturaning
    `amount_paid` iga tushmasdi — va shu sababli To'lovlar doskasi bilan
    Qarzdorlar ro'yxati bitta bola uchun ikki xil raqam ko'rsatardi
    (`docs/big-update/PLAN.md` §2).

    **O'zgarmas emas, lekin o'chirilmaydi ham.** Ledger pul HARAKATINI
    yozadi va u haqiqatan o'zgarmas. Taqsimot esa *bog'lanish*: to'lov
    qaytarilsa yoki hisob-faktura bekor qilinsa, pul o'sha hujjatni
    yopmay qo'yadi va yana avansga aylanadi. Shuning uchun qator
    `released_at` bilan bo'shatiladi — tarix qoladi, hisobdan chiqadi.

    `invoice.amount_paid` — shu yerdagi faol qatorlar yig'indisi. U kesh,
    haqiqat esa shu jadval (`_refresh_invoice_payment_state`).
    """

    payment = models.ForeignKey(
        "finance.Payment", on_delete=models.RESTRICT, related_name="allocations"
    )
    invoice = models.ForeignKey(
        "finance.Invoice", on_delete=models.RESTRICT, related_name="allocations"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    allocated_at = models.DateTimeField()

    # Bo'shatilgan taqsimot: to'lov qaytarildi yoki hisob-faktura bekor
    # qilindi. Qator qoladi — "bu pul bir vaqtlar shu fakturani yopgan
    # edi" degan fakt hisobotda kerak bo'ladi.
    released_at = models.DateTimeField(null=True, blank=True)
    release_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "payment_allocation"
        ordering = ["allocated_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="ck_allocation_amount_positive"
            ),
            # Bitta to'lov bitta fakturaga BIR marta taqsimlanadi. Qisman
            # indeks: bo'shatilgan qator yangisiga to'sqinlik qilmaydi.
            models.UniqueConstraint(
                fields=["payment", "invoice"],
                condition=models.Q(released_at__isnull=True),
                name="uq_allocation_payment_invoice",
            ),
        ]
        indexes = [
            models.Index(
                fields=["invoice"],
                condition=models.Q(released_at__isnull=True),
                name="ix_allocation_invoice",
            ),
            models.Index(
                fields=["payment"],
                condition=models.Q(released_at__isnull=True),
                name="ix_allocation_payment",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.amount} → {self.invoice_id}"

    @property
    def is_released(self) -> bool:
        return self.released_at is not None


class EntryType(models.TextChoices):
    CHARGE = "charge", gettext_lazy("Hisoblangan")
    PAYMENT = "payment", gettext_lazy("Toʻlov")
    DISCOUNT = "discount", gettext_lazy("Chegirma")
    ADJUSTMENT = "adjustment", gettext_lazy("Tuzatish")
    REFUND = "refund", gettext_lazy("Qaytarish")


class Direction(models.TextChoices):
    DEBIT = "debit", gettext_lazy("Debet")
    CREDIT = "credit", gettext_lazy("Kredit")


class InvoiceWriteOff(BranchScopedModel):
    """
    Qarzni kechirish — faqat shu yozuv orqali (Bosqich 12.3, brif §3).

    Excel'da qarz qo'lda 0 qilinardi va yashirin qarz paydo bo'lardi.
    Tizimda qarzni qo'lda o'zgartirishning yo'li yo'q; kechirish — hujjat:
    summa, SABAB va kim qilgani. Fakturada minus qator (`kind=write_off`)
    va ledgerda kredit yozuvi bilan birga, bitta tranzaksiyada yoziladi.
    Append-only: bekor qilish kerak bo'lsa — yangi hujjat.
    """

    invoice = models.ForeignKey(
        "finance.Invoice", on_delete=models.RESTRICT, related_name="write_offs"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=255)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        db_table = "invoice_write_off"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="ck_invoice_write_off_amount"
            ),
        ]


class SourceType(models.TextChoices):
    INVOICE = "invoice", gettext_lazy("Hisob-faktura")
    PAYMENT = "payment", gettext_lazy("Toʻlov")
    DISCOUNT = "discount", gettext_lazy("Chegirma")
    MANUAL = "manual", gettext_lazy("Qoʻlda")
    REFUND = "refund", gettext_lazy("Qaytarish")


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


class MonthClose(BranchScopedModel):
    """
    Yopilgan oy (Bosqich 12.6, brif §6).

    Yopilgandan keyin o'sha oy uchun faktura chiqarilmaydi va bekor
    qilinmaydi, pauza qo'yilmaydi; kechikkan qayta hisob esa KEYINGI oy
    fakturasiga tuzatish qatori bo'lib tushadi. To'lov va hisobdan
    chiqarish o'zi tuzatish hujjati — ular yopilgan oy qarziga ham
    qo'llanadi. Qayta ochish yo'q: yopish — kelishuv.

    `snapshot` — yopilgan paytdagi yig'ma: keyin "o'shanda nima edi?"
    degan savolga javob.
    """

    period_year = models.PositiveSmallIntegerField()
    period_month = models.PositiveSmallIntegerField()
    closed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="months_closed",
        null=True,
        blank=True,
    )
    snapshot = models.JSONField(default=dict)

    class Meta:
        db_table = "month_close"
        ordering = ["-period_year", "-period_month"]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "period_year", "period_month"], name="uq_month_close_period"
            ),
            models.CheckConstraint(
                condition=models.Q(period_month__gte=1, period_month__lte=12),
                name="ck_month_close_month",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.period_year}-{self.period_month:02d}"


class Refund(BranchScopedModel):
    """
    Ota-onaga avansni qaytarish (Bosqich 13.2b) — o'zgarmas hujjat.

    Qaytariladigan pul — aniq to'lovning hali hech qaysi fakturani yopmagan
    qismi; shuning uchun `payment` ga bog'lanadi va `payment_unallocated`
    uni ayiradi: qaytarilgan pul keyingi fakturaga ikkinchi marta
    taqsimlanmaydi. Bitta tranzaksiyada: ledger DEBET + qopdan `out`.
    """

    payment = models.ForeignKey(
        "finance.Payment", on_delete=models.RESTRICT, related_name="refunds"
    )
    child = models.ForeignKey("children.Child", on_delete=models.RESTRICT, related_name="refunds")
    cash_account = models.ForeignKey(
        "cash.CashAccount", on_delete=models.RESTRICT, related_name="refunds"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    refunded_on = models.DateField()
    reason = models.CharField(max_length=255)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="refunds_made",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "refund"
        ordering = ["-refunded_on", "-created_at"]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="ck_refund_amount"),
            models.CheckConstraint(condition=~models.Q(reason=""), name="ck_refund_reason"),
        ]

    def __str__(self) -> str:
        return f"{self.amount} → {self.child_id}"


#: Pul bankka darhol emas, to'lov tizimi orqali keladigan usullar.
#: `online` — 2026-10-15 gacha yozilgan eski Payme/Click.
TRANSIT_METHODS: tuple[str, ...] = ("terminal", "click", "payme", "online")


class PaymentSettlement(BranchScopedModel):
    """
    Yo'ldagi pul bankka tushdi (Bosqich 13.2c).

    Terminal/Click/Payme to'lovi bank qopiga darhol yoziladi (u bog'chaning
    puli), lekin "yo'lda" hisoblanadi — shu yozuv paydo bo'lguncha. Bank
    ko'chirmasi importi (13.3) ularni o'zi yaratadi; hozircha qo'lda.
    Bitta to'lov — bitta tushum.
    """

    payment = models.OneToOneField(
        "finance.Payment", on_delete=models.RESTRICT, related_name="settlement"
    )
    settled_on = models.DateField()
    reference = models.CharField(max_length=120, blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="settlements",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "payment_settlement"
        ordering = ["-settled_on"]

    def __str__(self) -> str:
        return f"{self.payment_id} @ {self.settled_on}"
