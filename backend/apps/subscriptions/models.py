"""
Obuna va hisoblash domeni (docs/03 §20, ADR-11).

⚠️ **Bu domen `finance` bilan hech qanday jadvalni bo'lishmaydi.**
Ikkalasida ham "plan", "invoice" va "payment" bor, lekin ular butunlay
boshqa narsa (docs/01 §4.6):

    finance       — bog'cha → ota-ona (bola uchun to'lov)
    subscriptions — vendor  → bog'cha  (tizimdan foydalanish uchun)

Shuning uchun bu yerdagi har bir sinf nomi `Subscription` bilan
boshlanadi yoki `Usage` bilan — import qilganda qaysi domendaligi
ko'rinib tursin.

Asosiy tamoyil D3 bilan bir xil: **hisob o'zgaruvchan hisoblagichdan
emas, o'zgarmas dalildan kelib chiqadi.** "Nega hisob shuncha?" degan
savolga javob `usage_snapshot` da, va u hech qachon tahrirlanmaydi.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy

from apps.core.models import BaseModel, TenantScopedModel

__all__ = [
    "SubscriptionPlan",
    "SubscriptionOnlineTransaction",
    "SubscriptionStatus",
    "PaymentTerm",
    "Subscription",
    "MeasurementMethod",
    "UsageSnapshot",
    "SubscriptionInvoiceStatus",
    "SubscriptionInvoice",
    "SubscriptionPaymentMethod",
    "SubscriptionPayment",
]


class SubscriptionPlan(BaseModel):
    """
    Vendor katalogi — narx ta'rifi.

    `organization_id` YO'Q: bu ikkita istisnodan biri (docs/03 §6.2), chunki
    plan mijozning ma'lumoti emas, vendorning narxnomasi.

    **Planlar versiyalanadi, tahrirlanmaydi.** Narx o'zgarsa yangi qator
    qo'shiladi va eskisi yopiladi; mavjud obunalar o'zi sotib olgan
    versiyaga ishora qilib qoladi. Tirik plan qatorini joyida tahrirlash
    o'tmishdagi HAR BIR hisob-fakturani orqaga qaytib o'zgartirardi —
    UZS inflyatsiyasi sharoitida bu ayniqsa xavfli (docs/01 §10).
    """

    code = models.CharField(max_length=40)
    name = models.CharField(max_length=100)
    currency = models.CharField(max_length=3, default="UZS")

    base_price = models.DecimalField(max_digits=12, decimal_places=2)
    # `included_children` bir vaqtning o'zida MINIMAL hisob ham: undan kam
    # bolasi bor tashkilot ham bazani to'laydi (docs/01 §4.2).
    included_children = models.SmallIntegerField()
    overage_step_children = models.SmallIntegerField()
    overage_step_price = models.DecimalField(max_digits=12, decimal_places=2)

    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "subscription_plan"
        ordering = ["code", "-valid_from"]
        constraints = [
            models.UniqueConstraint(fields=["code", "valid_from"], name="uq_plan_code_valid_from"),
            models.CheckConstraint(
                condition=models.Q(base_price__gte=Decimal("0")), name="ck_plan_base_price"
            ),
            models.CheckConstraint(
                condition=models.Q(included_children__gt=0), name="ck_plan_included_children"
            ),
            models.CheckConstraint(
                condition=models.Q(overage_step_children__gt=0), name="ck_plan_step_children"
            ),
            models.CheckConstraint(
                condition=models.Q(overage_step_price__gte=Decimal("0")),
                name="ck_plan_step_price",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} ({self.valid_from})"


class SubscriptionStatus(models.TextChoices):
    TRIALING = "trialing", gettext_lazy("Sinov davri")
    PENDING_PAYMENT = "pending_payment", gettext_lazy("Toʻlov kutilmoqda")
    ACTIVE = "active", gettext_lazy("Faol")
    PAST_DUE = "past_due", gettext_lazy("Muddati oʻtgan")
    SUSPENDED = "suspended", gettext_lazy("Toʻxtatilgan")
    CANCELLED = "cancelled", gettext_lazy("Bekor qilingan")


# Yozish taqiqlanadigan holatlar. Ma'lumot HECH QACHON o'chirilmaydi va
# yashirilmaydi — mijoz o'z moliyaviy tarixini ko'rib turadi va istalgan
# payt qaytib kelishi mumkin (docs/03 §20.6).
READ_ONLY_STATUSES: tuple[str, ...] = (
    SubscriptionStatus.SUSPENDED,
    SubscriptionStatus.CANCELLED,
)


class PaymentTerm(models.TextChoices):
    MONTHLY = "monthly", gettext_lazy("Oylik")
    SEMIANNUAL = "semiannual", gettext_lazy("Yarim yillik")
    ANNUAL = "annual", gettext_lazy("Yillik")


# Muddat → chegirma foizi (docs/01 §4.3). Bu **standart taklif**;
# obunaga u sotib olish paytida NUSXA qilinadi va keyin bu yerdagi
# raqam o'zgarsa ham mavjud shartnomalarga tegmaydi.
TERM_DISCOUNTS: dict[str, Decimal] = {
    PaymentTerm.MONTHLY: Decimal("0"),
    PaymentTerm.SEMIANNUAL: Decimal("15"),
    PaymentTerm.ANNUAL: Decimal("25"),
}

# Muddat → oldindan to'lanadigan oylar soni.
TERM_MONTHS: dict[str, int] = {
    PaymentTerm.MONTHLY: 1,
    PaymentTerm.SEMIANNUAL: 6,
    PaymentTerm.ANNUAL: 12,
}

TRIAL_DAYS = 15
# To'lov ko'chib kelguncha kutish muddati. Mijozlar yuridik shaxs va
# bank o'tkazmasi kunlab ketadi — kirish o'rtada uzilib qolmasligi kerak
# (docs/01 §4.4).
GRACE_DAYS = 7


class Subscription(TenantScopedModel):
    """Bitta tashkilotning tijorat shartnomasi. Tashkilotga bittadan."""

    plan = models.ForeignKey(
        SubscriptionPlan, on_delete=models.RESTRICT, related_name="subscriptions"
    )
    status = models.CharField(
        max_length=20, choices=SubscriptionStatus.choices, default=SubscriptionStatus.TRIALING
    )
    payment_term = models.CharField(
        max_length=20, choices=PaymentTerm.choices, default=PaymentTerm.MONTHLY
    )
    # Chegirma obunaga NUSXA qilinadi, muddatdan hisoblanmaydi: vendor
    # keyin "yillik" nimaga arziyotganini o'zgartirsa, mavjud
    # shartnomalarga tegmasin (docs/03 §20.2).
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))

    trial_started_at = models.DateTimeField(null=True, blank=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True)

    current_period_start = models.DateField()
    current_period_end = models.DateField()
    # Oldindan to'lov qamragan bolalar soni (faqat prepaid muddatlarda).
    committed_children = models.SmallIntegerField(null=True, blank=True)

    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "subscription"
        ordering = ["-created_at"]
        constraints = [
            # Tashkilotga bitta tirik obuna. Bekor qilinganlar tarixda
            # qoladi, shuning uchun indeks qisman.
            models.UniqueConstraint(
                fields=["organization"],
                condition=~models.Q(status=SubscriptionStatus.CANCELLED),
                name="uq_subscription_active_org",
            ),
            models.CheckConstraint(
                condition=models.Q(current_period_end__gt=models.F("current_period_start")),
                name="ck_subscription_period",
            ),
            models.CheckConstraint(
                condition=models.Q(trial_ends_at__isnull=True)
                | models.Q(trial_started_at__isnull=False),
                name="ck_subscription_trial_dates",
            ),
            models.CheckConstraint(
                condition=models.Q(discount_percent__gte=Decimal("0"))
                & models.Q(discount_percent__lte=Decimal("100")),
                name="ck_subscription_discount",
            ),
            models.CheckConstraint(
                condition=models.Q(committed_children__isnull=True)
                | models.Q(committed_children__gte=0),
                name="ck_subscription_committed",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.organization_id} — {self.status}"

    @property
    def is_read_only(self) -> bool:
        return self.status in READ_ONLY_STATUSES


class MeasurementMethod(models.TextChoices):
    DAILY_PEAK = "daily_peak", gettext_lazy("Kunlik eng yuqori")
    MANUAL_ADJUSTMENT = "manual_adjustment", gettext_lazy("Qoʻlda tuzatish")


class UsageSnapshot(TenantScopedModel):
    """
    Hisoblash DALILI — append-only (P11).

    "Nega hisob shuncha?" degan savolga javob shu yerda va u hech qachon
    o'chirilmaydi.

    **Nega eng yuqori ko'rsatkich, oy oxiridagi son emas?** Oy oxiridagi
    o'lchovni aldash juda oson: 30-kuni bolalarni nofaol qilib, 1-kuni
    qaytarish kifoya. Kunlik vazifa esa eng yuqori nuqtani yozib boradi,
    ya'ni raqam HAQIQATDA iste'mol qilingan xizmatni aks ettiradi.

    Davr ochiq turganda `peak_children` faqat O'SADI — bu tarixni
    qayta yozish emas, o'lchovning o'zi. Davr yopilgach (`closed_at`)
    qator butunlay muzlaydi va uni bazadagi trigger himoya qiladi.
    Tuzatish kerak bo'lsa — yangi `manual_adjustment` qatori, majburiy
    izoh bilan (D3 bilan bir xil intizom).
    """

    subscription = models.ForeignKey(
        Subscription, on_delete=models.RESTRICT, related_name="usage_snapshots"
    )
    period_year = models.SmallIntegerField()
    period_month = models.SmallIntegerField()

    peak_children = models.IntegerField(default=0)
    peak_observed_at = models.DateTimeField()
    billable_children = models.IntegerField(default=0)

    measurement_method = models.CharField(
        max_length=30, choices=MeasurementMethod.choices, default=MeasurementMethod.DAILY_PEAK
    )
    note = models.TextField(blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "usage_snapshot"
        ordering = ["-period_year", "-period_month"]
        constraints = [
            # Indeks QISMAN: davr uchun bitta o'lchov qatori bo'ladi,
            # lekin tuzatishlar qo'shimcha qator sifatida keladi va ular
            # bir xil davrga tegishli bo'lishi mumkin.
            models.UniqueConstraint(
                fields=["subscription", "period_year", "period_month"],
                condition=models.Q(measurement_method=MeasurementMethod.DAILY_PEAK),
                name="uq_usage_snapshot_period",
            ),
            models.CheckConstraint(
                condition=models.Q(period_month__gte=1) & models.Q(period_month__lte=12),
                name="ck_usage_period_month",
            ),
            models.CheckConstraint(
                condition=models.Q(peak_children__gte=0), name="ck_usage_peak_children"
            ),
            # Qo'lda tuzatish IZOHSIZ bo'lmaydi: "kim va nega o'zgartirdi"
            # javobsiz qolsa, dalilning ma'nosi yo'qoladi.
            models.CheckConstraint(
                condition=~models.Q(measurement_method=MeasurementMethod.MANUAL_ADJUSTMENT)
                | ~models.Q(note=""),
                name="ck_usage_adjustment_note",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "-period_year", "-period_month"],
                name="ix_usage_org_period",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.period_year}-{self.period_month:02d}: {self.billable_children}"


class SubscriptionInvoiceStatus(models.TextChoices):
    ISSUED = "issued", gettext_lazy("Yozilgan")
    PAID = "paid", gettext_lazy("Toʻlangan")
    OVERDUE = "overdue", gettext_lazy("Muddati oʻtgan")
    CANCELLED = "cancelled", gettext_lazy("Bekor qilingan")


class SubscriptionInvoice(TenantScopedModel):
    """
    Vendor tashkilotga yozgan hisob.

    Summalar ataylab denormalizatsiya qilingan. Hisob-faktura —
    **yuridik hujjat**: u uch yildan keyin ham AYNAN xuddi shunday
    ko'rinishi kerak, hatto plan versiyasi, dalil talqini yoki chegirma
    siyosati o'zgargan bo'lsa ham. Eski hisobni bugungi ma'lumotdan
    qayta hisoblash — xato, imkoniyat emas.
    """

    subscription = models.ForeignKey(
        Subscription, on_delete=models.RESTRICT, related_name="invoices"
    )
    usage_snapshot = models.ForeignKey(
        UsageSnapshot,
        on_delete=models.RESTRICT,
        related_name="invoices",
        null=True,
        blank=True,
    )
    # Raqam vendor bo'ylab global — mijozlar bo'yicha emas. Bu bitta
    # ketma-ketlik, chunki hujjatni yozayotgan taraf bitta: vendor.
    number = models.CharField(max_length=30, unique=True)

    issued_at = models.DateField()
    due_at = models.DateField()
    period_start = models.DateField()
    period_end = models.DateField()

    billable_children = models.IntegerField(default=0)
    base_amount = models.DecimalField(max_digits=12, decimal_places=2)
    overage_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="UZS")

    status = models.CharField(
        max_length=20,
        choices=SubscriptionInvoiceStatus.choices,
        default=SubscriptionInvoiceStatus.ISSUED,
    )

    class Meta:
        db_table = "subscription_invoice"
        ordering = ["-issued_at", "-number"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(due_at__gte=models.F("issued_at")),
                name="ck_sub_invoice_due",
            ),
            models.CheckConstraint(
                condition=models.Q(period_end__gte=models.F("period_start")),
                name="ck_sub_invoice_period",
            ),
            models.CheckConstraint(
                condition=models.Q(total_amount__gte=Decimal("0")),
                name="ck_sub_invoice_total_positive",
            ),
            # Arifmetika BAZADA tekshiriladi: yig'indi mos kelmaydigan
            # hisob-faktura umuman yozilmasin.
            models.CheckConstraint(
                condition=models.Q(
                    total_amount=models.F("base_amount")
                    + models.F("overage_amount")
                    - models.F("discount_amount")
                ),
                name="ck_subscription_invoice_total",
            ),
            # Bitta davr — bitta hisob (PLAN 11.7).
            #
            # `CELERY_TASK_ACKS_LATE` va `REJECT_ON_WORKER_LOST` birga
            # vazifani qayta yetkazadi: ishchi hisob yozilgandan KEYIN,
            # davr surilishidan OLDIN yiqilsa, qayta urinish ikkinchi
            # hisobni yozardi va mijoz ikki marta toʻlar edi. Servis
            # endi uchala qadamni bitta tranzaksiyada bajaradi, lekin
            # oxirgi tutqich BAZADA boʻlishi kerak (invariant 8):
            # tuition `invoice` da `uq_invoice_child_period` bor,
            # obunada esa hech narsa yoʻq edi.
            #
            # Bekor qilingani chetda: xato yozilgan hisobni bekor qilib,
            # toʻgʻrisini yozish yoʻli ochiq qolsin.
            models.UniqueConstraint(
                fields=["subscription", "period_start"],
                condition=~models.Q(status="cancelled"),
                name="uq_sub_invoice_period",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "-issued_at"], name="ix_sub_invoice_org_issued"),
        ]

    def __str__(self) -> str:
        return f"{self.number} — {self.total_amount}"


class SubscriptionPaymentMethod(models.TextChoices):
    BANK_TRANSFER = "bank_transfer", gettext_lazy("Bank oʻtkazmasi")
    CARD = "card", gettext_lazy("Karta")
    CASH = "cash", gettext_lazy("Naqd")
    # Paid by the kindergarten through Radix's own Payme / Click merchant (PLAN 6.4).
    ONLINE = "online", gettext_lazy("Payme / Click")


class SubscriptionPayment(TenantScopedModel):
    """Hisob bo'yicha tushum — append-only."""

    subscription_invoice = models.ForeignKey(
        SubscriptionInvoice, on_delete=models.RESTRICT, related_name="payments"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(
        max_length=20,
        choices=SubscriptionPaymentMethod.choices,
        default=SubscriptionPaymentMethod.BANK_TRANSFER,
    )
    reference = models.CharField(max_length=80, blank=True)
    received_at = models.DateTimeField()
    recorded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="subscription_payments",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "subscription_payment"
        ordering = ["-received_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=Decimal("0")), name="ck_sub_payment_amount"
            ),
            # docs/03 §20.5 always promised this CHECK; it arrived with
            # `online` (PLAN 6.4). Every existing row uses one of these.
            models.CheckConstraint(
                condition=models.Q(method__in=["bank_transfer", "card", "cash", "online"]),
                name="ck_sub_payment_method",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.amount} ({self.method})"


class SubscriptionOnlineTransaction(TenantScopedModel):
    """
    A Payme / Click transaction on Radix's merchant for a subscription
    invoice (PLAN 6.4). The provider-side record; the money itself is the
    `SubscriptionPayment` it points to once performed.

    Same state numbers as the tuition side (`online_payments.TxnState`), and
    the same protocol code — but its own table: subscription billing and
    tuition never share tables (invariant 9). Metadata plane: the webhook
    finds the invoice by its global number under `platform_context()`.
    """

    subscription_invoice = models.ForeignKey(
        SubscriptionInvoice, on_delete=models.RESTRICT, related_name="online_transactions"
    )
    provider = models.CharField(max_length=10)
    provider_txn_id = models.CharField(max_length=64)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    state = models.SmallIntegerField(default=1)
    reason = models.SmallIntegerField(null=True, blank=True)
    payment = models.ForeignKey(
        SubscriptionPayment,
        on_delete=models.RESTRICT,
        related_name="online_transactions",
        null=True,
        blank=True,
    )
    provider_time = models.BigIntegerField(null=True, blank=True)
    performed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "subscription_online_transaction"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_txn_id"], name="uq_sub_online_txn_provider_id"
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gt=Decimal("0")), name="ck_sub_online_txn_amount"
            ),
            models.CheckConstraint(
                condition=models.Q(provider__in=["payme", "click"]),
                name="ck_sub_online_txn_provider",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.provider}:{self.provider_txn_id} ({self.state})"
