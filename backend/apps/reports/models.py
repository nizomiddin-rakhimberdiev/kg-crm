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

__all__ = ["ExportStatus", "ReportExport", "ReportSnapshot", "REPORT_TYPES"]

# Eksport qilinadigan hisobot turlari — ro'yxat YOPIQ. Ochiq bo'lsa,
# mijoz yuborgan matn bevosita funksiya nomiga aylanardi.
REPORT_TYPES: tuple[str, ...] = (
    "revenue",
    "expenses",
    "payroll",
    "attendance",
    "debtors",
    "profit-loss",
    "staff-attendance",
    # Eski "oylik to'lov jadvali" ko'rinishi (Bosqich 12.6).
    "monthly",
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


class ReportSnapshot(TenantScopedModel):
    """
    Oylik hisobot paketining O'ZGARMAS nusxasi (Bosqich 13.5, brif §8).

    JSON + nazorat summasi. Keyin ma'lumot o'zgarsa, jonli paketning
    summasi boshqacha chiqadi — "o'zgarish bor" — va yangi versiya
    yaratiladi; eskisi o'chmaydi. Topshirish/qabul holati — `ReportReview`
    da (13.6); nusxaning o'zi bazada muzlatilgan (`kg_guard_snapshot_frozen`).
    """

    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.RESTRICT,
        related_name="report_snapshots",
        null=True,
        blank=True,
    )
    period_year = models.PositiveSmallIntegerField()
    period_month = models.PositiveSmallIntegerField()
    version = models.PositiveIntegerField()
    data = models.JSONField()
    checksum = models.CharField(max_length=64)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="report_snapshots",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "report_snapshot"
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "branch", "period_year", "period_month", "version"],
                name="uq_report_snapshot_version",
                nulls_distinct=False,
            ),
        ]

    def __str__(self) -> str:
        return f"{self.period_year}-{self.period_month:02d} v{self.version}"


# --- Boshqaruv: topshirish, savollar, qabul (Bosqich 13.6, ADR-42) ---


class ReviewStatus(models.TextChoices):
    DRAFT = "draft", gettext_lazy("Qoralama")
    SUBMITTED = "submitted", gettext_lazy("Topshirildi")
    QUESTION = "question", gettext_lazy("Savol bor")
    RETURNED = "returned", gettext_lazy("Qaytarildi")
    RESUBMITTED = "resubmitted", gettext_lazy("Qayta topshirildi")
    ACCEPTED = "accepted", gettext_lazy("Qabul qilindi")


class ReportReview(TenantScopedModel):
    """
    Bir oy (va filial) hisobotining jarayoni — raqamlar EMAS.

    Raqamlar `ReportSnapshot` da, o'zgarmas. Bu yerda faqat holat: kim
    topshirdi, qaysi versiyani, muddat qachon, eslatma ketdimi. Tarix —
    `ReportEvent` da, qatorlar o'chmaydi. "Tekshiruvdan o'tdi" saqlanmaydi:
    u jonli shart (hamma qizil izohli), har ochilishda hisoblanadi.
    """

    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.RESTRICT,
        related_name="report_reviews",
        null=True,
        blank=True,
    )
    period_year = models.PositiveSmallIntegerField()
    period_month = models.PositiveSmallIntegerField()
    status = models.CharField(
        max_length=12, choices=ReviewStatus.choices, default=ReviewStatus.DRAFT
    )
    snapshot = models.ForeignKey(
        ReportSnapshot,
        on_delete=models.RESTRICT,
        related_name="reviews",
        null=True,
        blank=True,
    )
    submitted_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    late_notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "report_review"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "branch", "period_year", "period_month"],
                name="uq_report_review_period",
                nulls_distinct=False,
            ),
            models.CheckConstraint(
                condition=models.Q(period_month__gte=1, period_month__lte=12),
                name="ck_report_review_month",
            ),
        ]


class ReviewEventKind(models.TextChoices):
    NOTE = "note", gettext_lazy("Izoh")
    SUBMIT = "submit", gettext_lazy("Topshirdi")
    QUESTION = "question", gettext_lazy("Savol")
    ANSWER = "answer", gettext_lazy("Javob")
    ACCEPT = "accept", gettext_lazy("Qabul qildi")
    RETURN = "return", gettext_lazy("Qaytardi")
    APPROVE = "approve", gettext_lazy("Tasdiqladi")


class ReportEvent(TenantScopedModel):
    """
    Jarayon tarixi — faqat qo'shiladi (brif §8: "hammasi tarixda qoladi").

    `path` — raqam manzili (`revenue.chain.collected`), tekshiruv
    (`checks:month_closed`) yoki "Diqqat" bandi (`attention:<qoida>:<obyekt>`).
    Savolga javob `parent` orqali o'sha joyda turadi.
    """

    review = models.ForeignKey(ReportReview, on_delete=models.RESTRICT, related_name="events")
    kind = models.CharField(max_length=10, choices=ReviewEventKind.choices)
    path = models.CharField(max_length=200, blank=True)
    text = models.TextField(blank=True)
    parent = models.ForeignKey(
        "self", on_delete=models.RESTRICT, related_name="replies", null=True, blank=True
    )
    snapshot = models.ForeignKey(
        ReportSnapshot, on_delete=models.RESTRICT, related_name="+", null=True, blank=True
    )
    author = models.ForeignKey(
        "accounts.User", on_delete=models.RESTRICT, related_name="report_events"
    )

    class Meta:
        db_table = "report_event"
        ordering = ["created_at"]
        indexes = [models.Index(fields=["review", "created_at"], name="ix_report_event_review")]


class ReportShareLink(TenantScopedModel):
    """
    Bank, investor yoki buxgalter uchun havola — faqat o'qish, muddatli.

    Havola o'zgarmas NUSXANI ochadi, jonli ma'lumotni emas: bankka
    ko'rsatilgan raqam ertaga storno bo'lsa ham o'sha raqam bo'lib qoladi.
    Token bazada faqat xesh sifatida; tokenning o'zida tashkilot bor
    (ADR-23 usuli) — ochiq so'rovda tenant konteksti yo'q.
    """

    snapshot = models.ForeignKey(
        ReportSnapshot, on_delete=models.RESTRICT, related_name="share_links"
    )
    token_hash = models.CharField(max_length=64, unique=True)
    label = models.CharField(max_length=120)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    opened_count = models.PositiveIntegerField(default=0)
    last_opened_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.RESTRICT, related_name="report_share_links"
    )

    class Meta:
        db_table = "report_share_link"
        ordering = ["-created_at"]


# --- Reja (Bosqich 13.7) ---


class BudgetKind(models.TextChoices):
    REVENUE = "revenue", gettext_lazy("Daromad")
    OTHER_INCOME = "other_income", gettext_lazy("Boshqa daromad")
    PAYROLL = "payroll", gettext_lazy("Ish haqi")
    CATEGORY = "category", gettext_lazy("Xarajat toifasi")


class BudgetLine(TenantScopedModel):
    """
    Oylik reja — bitta qator. Bu hujjat emas, ledger ham emas: reja
    o'zgartiriladi. Fakt har doim modul selektorlaridan (`money.profit_and_loss`)
    olinadi — reja raqamni "to'g'rilay" olmaydi.
    """

    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.RESTRICT,
        related_name="budget_lines",
        null=True,
        blank=True,
    )
    period_year = models.PositiveSmallIntegerField()
    period_month = models.PositiveSmallIntegerField()
    kind = models.CharField(max_length=14, choices=BudgetKind.choices)
    category = models.ForeignKey(
        "expenses.ExpenseCategory",
        on_delete=models.RESTRICT,
        related_name="budget_lines",
        null=True,
        blank=True,
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    updated_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "budget_line"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "organization",
                    "branch",
                    "period_year",
                    "period_month",
                    "kind",
                    "category",
                ],
                name="uq_budget_line",
                nulls_distinct=False,
            ),
            models.CheckConstraint(condition=models.Q(amount__gte=0), name="ck_budget_amount"),
            models.CheckConstraint(
                condition=models.Q(period_month__gte=1, period_month__lte=12),
                name="ck_budget_month",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(kind="category", category__isnull=False)
                    | (~models.Q(kind="category") & models.Q(category__isnull=True))
                ),
                name="ck_budget_category",
            ),
        ]


# --- Soliq taqvimi (Bosqich 13.8) ---


class TaxKind(models.TextChoices):
    INCOME_TAX = "income_tax", gettext_lazy("JShDS (daromad soligʻi)")
    PENSION = "pension", gettext_lazy("INPS (pensiya badali)")
    SOCIAL_TAX = "social_tax", gettext_lazy("Ijtimoiy soliq")
    DIVIDEND_TAX = "dividend_tax", gettext_lazy("Dividend soligʻi")
    TURNOVER_TAX = "turnover_tax", gettext_lazy("Aylanmadan olinadigan soliq")


class TaxObligation(TenantScopedModel):
    """
    Bitta soliq majburiyati: qaysi oy uchun, qancha, qachongacha.

    Summa hujjatlardan hisoblanadi (oylik hisobi, egaga to'lov, daromad) va
    to'lanmaguncha yangilanadi; to'langanda `operation` — haqiqiy
    `tax_payment` pul harakati — bilan qotadi. Holat saqlanmaydi:
    to'langan / muddati yaqin / o'tgan — sanadan hisoblanadi.
    """

    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.RESTRICT,
        related_name="tax_obligations",
        null=True,
        blank=True,
    )
    kind = models.CharField(max_length=14, choices=TaxKind.choices)
    period_year = models.PositiveSmallIntegerField()
    period_month = models.PositiveSmallIntegerField()
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    operation = models.OneToOneField(
        "cash.MoneyOperation",
        on_delete=models.RESTRICT,
        related_name="tax_obligation",
        null=True,
        blank=True,
    )
    reminded_at = models.DateTimeField(null=True, blank=True)
    overdue_notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "tax_obligation"
        ordering = ["due_date", "kind"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "branch", "kind", "period_year", "period_month"],
                name="uq_tax_obligation",
                nulls_distinct=False,
            ),
            models.CheckConstraint(condition=models.Q(amount__gte=0), name="ck_tax_amount"),
        ]
