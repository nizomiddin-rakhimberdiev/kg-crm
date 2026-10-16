"""
Pul qoplari va ularning o'zgarmas harakat jurnali (docs/03 §13a, ADR-17).

Bu — loyihadagi UCHINCHI append-only jurnal. Birinchisi oilaning qarzini
(`child_ledger_entry`), ikkinchisi ombor qoldig'ini (`stock_movement`)
yuritadi; bu esa "qaysi qopda qancha pul bor?" degan savolga javob beradi.

Uchalasida ham bir xil shart: **qoldiq hech qachon saqlanmaydi.** U har
safar yozuvlardan hisoblanadi, shuning uchun noto'g'ri bo'lishi mumkin
emas. Xato qarshi yozuv bilan tuzatiladi, `UPDATE` bilan emas (D3).
"""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy

from apps.core.models import BranchScopedModel

__all__ = [
    "CashAccount",
    "CashAccountKind",
    "CashCount",
    "CashHandover",
    "CashMovement",
    "HandoverStatus",
    "MoneyOperation",
    "OperationKind",
    "MovementDirection",
    "MovementSource",
]


class CashAccountKind(models.TextChoices):
    CASH = "cash", gettext_lazy("Naqd kassa")
    TERMINAL = "terminal", gettext_lazy("Terminal")
    BANK = "bank", gettext_lazy("Bank hisobi")
    EWALLET = "ewallet", gettext_lazy("Elektron hamyon")


class CashAccount(BranchScopedModel):
    """
    Bog'cha haqiqatan ushlab turadigan bitta pul qopi.

    Filial yaratilganda to'rttasi avtomatik ochiladi — har bir to'lov
    usuliga bittadan. Bog'cha ularni qayta nomlashi, qo'shishi yoki
    o'chirib qo'yishi mumkin.
    """

    name = models.CharField(max_length=80)
    kind = models.CharField(max_length=12, choices=CashAccountKind.choices)

    # Shu usuldagi to'lov sukut bo'yicha SHU qopga tushadi.
    #
    # `NULL` — "hech qachon avtomatik tanlanmaydi": bog'cha qo'shimcha
    # qop ochishi mumkin (masalan "Direktor seyfi"), unga esa hech qanday
    # to'lov usuli o'zi kelib tushmasligi kerak.
    handles_method = models.CharField(max_length=20, blank=True, default="")

    class Meta:
        db_table = "cash_account"
        ordering = ["kind", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "name"],
                condition=models.Q(is_active=True),
                name="uq_cash_account_branch_name",
            ),
            # Bitta usulga bitta manzil. Ikkita qop `cash` ni da'vo qilsa,
            # "bu to'lov qayerga tushdi?" degan savol tanga tashlashga
            # aylanardi — va u pul haqidagi savol.
            models.UniqueConstraint(
                fields=["branch", "handles_method"],
                condition=models.Q(is_active=True) & ~models.Q(handles_method=""),
                name="uq_cash_account_method",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class MovementDirection(models.TextChoices):
    IN = "in", gettext_lazy("Kirim")
    OUT = "out", gettext_lazy("Chiqim")


class MovementSource(models.TextChoices):
    PAYMENT = "payment", gettext_lazy("Toʻlov")
    PAYMENT_REVERSAL = "payment_reversal", gettext_lazy("Toʻlov qaytarildi")
    EXPENSE = "expense", gettext_lazy("Chiqim")
    PAYROLL = "payroll", gettext_lazy("Oylik maosh")
    ADVANCE = "advance", gettext_lazy("Avans")
    TRANSFER = "transfer", gettext_lazy("Qoplar orasida oʻtkazma")
    OPENING = "opening", gettext_lazy("Boshlangʻich qoldiq")
    MANUAL = "manual", gettext_lazy("Qoʻlda tuzatish")
    # Kun yopilishidagi sanoq farqi — kamomad yoki ortiqcha, SABABI bilan
    # (Bosqich 12.5). "Tenglashtiruvchi qator" emas: manbasi `cash_count`.
    COUNT = "count", gettext_lazy("Sanoq farqi")
    # Bosqich 13.2b: xarajat ham, tushum ham bo'lmagan pul harakatlari —
    # manbasi `money_operation` (turi o'sha yerda).
    OPERATION = "operation", gettext_lazy("Moliyaviy operatsiya")
    # Ota-onaga avansni qaytarish — manbasi `finance.Refund`.
    REFUND = "refund", gettext_lazy("Ota-onaga qaytarish")


class CashMovement(BranchScopedModel):
    """
    Pulning bir qopga kirgani yoki undan chiqqani — O'ZGARMAS yozuv.

    Har bir yozuv uni keltirib chiqargan hujjat bilan BITTA
    tranzaksiyada yoziladi. To'lovi bor, harakati yo'q holat — bu
    jimgina noto'g'ri qoldiq degani, va tranzaksiya buni imkonsiz qiladi.
    """

    cash_account = models.ForeignKey(
        "cash.CashAccount", on_delete=models.RESTRICT, related_name="movements"
    )
    direction = models.CharField(max_length=3, choices=MovementDirection.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)

    source_type = models.CharField(max_length=20, choices=MovementSource.choices)
    # Yumshoq polimorfizm — `child_ledger_entry.source_id` bilan bir xil
    # yondashuv: to'lov/chiqim/oylik qatorining id'si.
    source_id = models.UUIDField(null=True, blank=True)
    # O'tkazmaning ikki oyog'i shu qiymat bilan bog'lanadi.
    transfer_group = models.UUIDField(null=True, blank=True)

    # Pul QACHON harakat qilgani — qachon kiritilgani emas.
    occurred_at = models.DateTimeField()
    description = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="cash_movements",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "cash_movement"
        ordering = ["-occurred_at", "-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="ck_cash_movement_amount_positive"
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "cash_account", "occurred_at"],
                name="ix_cash_mv_org_acc_date",
            ),
            models.Index(fields=["source_type", "source_id"], name="ix_cash_mv_source"),
        ]

    def __str__(self) -> str:
        sign = "+" if self.direction == MovementDirection.IN else "−"
        return f"{sign}{self.amount} {self.cash_account_id}"


class HandoverStatus(models.TextChoices):
    PENDING = "pending", gettext_lazy("Tasdiq kutilmoqda")
    CONFIRMED = "confirmed", gettext_lazy("Qabul qilindi")
    REJECTED = "rejected", gettext_lazy("Rad etildi")


class CashHandover(BranchScopedModel):
    """
    Naqd pulni qo'ldan qo'lga topshirish — kassir → mas'ul shaxs (Bosqich 12.5).

    Qopdagi pul O'ZGARMAYDI: u bitta "Naqd kassa"da turibdi, faqat uni
    ushlab turgan odam almashadi. Shuning uchun bu `cash_movement` emas,
    alohida yozuv. Qabul qiluvchi tasdiqlamaguncha pul topshiruvchida
    hisoblanadi — "berdim" va "oldim" ikki odamning ikki so'zi.
    """

    cash_account = models.ForeignKey(
        "cash.CashAccount", on_delete=models.RESTRICT, related_name="handovers"
    )
    from_user = models.ForeignKey(
        "accounts.User", on_delete=models.RESTRICT, related_name="cash_handed_over"
    )
    to_user = models.ForeignKey(
        "accounts.User", on_delete=models.RESTRICT, related_name="cash_received"
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    note = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=10, choices=HandoverStatus.choices, default=HandoverStatus.PENDING
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "cash_handover"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="ck_cash_handover_amount_positive"
            ),
            models.CheckConstraint(
                condition=~models.Q(from_user=models.F("to_user")),
                name="ck_cash_handover_two_people",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.amount}: {self.from_user_id} → {self.to_user_id}"


class CashCount(BranchScopedModel):
    """
    Kun yopilishi — jismoniy sanoq tizimdagi qoldiq bilan (Bosqich 12.5).

    Farq bo'lsa, u SABABI bilan `count` harakati bo'lib yoziladi va qop
    sanoqqa tenglashadi. Excel'dagi "tenglashtiruvchi qator"dan farqi:
    kim, qachon, qancha kam yoki ortiq sanagani va nega — hammasi shu
    yerda qoladi.
    """

    cash_account = models.ForeignKey(
        "cash.CashAccount", on_delete=models.RESTRICT, related_name="counts"
    )
    counted_on = models.DateField()
    system_balance = models.DecimalField(max_digits=14, decimal_places=2)
    counted = models.DecimalField(max_digits=14, decimal_places=2)
    # counted − system_balance: manfiy — kamomad, musbat — ortiqcha.
    difference = models.DecimalField(max_digits=14, decimal_places=2)
    reason = models.CharField(max_length=255, blank=True)
    # Kupyuralar bo'yicha sanoq (Bosqich 13.3b): {"200000": 5, ...}.
    # Ixtiyoriy; berilsa `counted` — aynan shularning yig'indisi.
    denominations = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="cash_counts",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "cash_count"
        ordering = ["-counted_on", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["cash_account", "counted_on"], name="uq_cash_count_account_day"
            ),
            models.CheckConstraint(
                condition=models.Q(counted__gte=0), name="ck_cash_count_counted"
            ),
            # Farq bor — sabab bor. Bazada ham, chunki "tenglashtiruvchi
            # qator" aynan sababsiz farq edi.
            models.CheckConstraint(
                condition=models.Q(difference=0) | ~models.Q(reason=""),
                name="ck_cash_count_reason",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.counted_on}: {self.counted} ({self.difference:+})"


class OperationKind(models.TextChoices):
    """
    Pul harakatining turi (Bosqich 13.2b, brif §3.2).

    Hech biri xarajat emas va hech biri ota-ona to'lovi emas: shuning uchun
    alohida hujjat. O'tkazma (`cash.transfer`) va sanoq farqi (`cash_count`)
    o'z joyida qoladi.
    """

    OTHER_INCOME = "other_income", gettext_lazy("Boshqa daromad")
    OWNER_DRAW = "owner_draw", gettext_lazy("Egasiga toʻlov")
    OWNER_CONTRIBUTION = "owner_contribution", gettext_lazy("Egadan kiritma")
    LOAN_IN = "loan_in", gettext_lazy("Kredit olindi")
    LOAN_REPAY = "loan_repay", gettext_lazy("Kredit qaytarildi")
    TAX_PAYMENT = "tax_payment", gettext_lazy("Soliq toʻlovi")


#: Turi → pul yo'nalishi.
OPERATION_DIRECTION: dict[str, str] = {
    OperationKind.OTHER_INCOME: "in",
    OperationKind.OWNER_DRAW: "out",
    OperationKind.OWNER_CONTRIBUTION: "in",
    OperationKind.LOAN_IN: "in",
    OperationKind.LOAN_REPAY: "out",
    OperationKind.TAX_PAYMENT: "out",
}

#: Turi → ruxsat etilgan aniqlik (bo'sh — aniqlik yo'q).
OPERATION_SUBTYPES: dict[str, tuple[str, ...]] = {
    OperationKind.OTHER_INCOME: ("subsidy", "club", "rent", "other"),
    OperationKind.OWNER_DRAW: ("dividend", "draw"),
    OperationKind.OWNER_CONTRIBUTION: ("",),
    OperationKind.LOAN_IN: ("",),
    OperationKind.LOAN_REPAY: ("",),
    OperationKind.TAX_PAYMENT: ("dividend_tax", "social_tax", "income_tax", "other"),
}


class MoneyOperation(BranchScopedModel):
    """
    Xarajat bo'lmagan pul harakati — hujjat (Bosqich 13.2b).

    Pul harakati (`cash_movement`) shu hujjat bilan BITTA tranzaksiyada
    yoziladi (invariant 12). Hujjat o'zgarmaydi: xato — teskari operatsiya.

    * Egasiga to'lov xarajat EMAS: foyda-zararga kirmaydi, pul oqimida
      alohida qator. Dividendda soliq (`tax.dividend_percent`) shu yerda
      hisoblanadi va `tax_payment` bilan yopilguncha majburiyat bo'ladi.
    * Egadan kiritma va kredit — tushum EMAS.
    * Boshqa daromad (subsidiya, to'garak, ijara) — daromad, tegishli oyi bilan.
    """

    kind = models.CharField(max_length=20, choices=OperationKind.choices)
    subtype = models.CharField(max_length=20, blank=True)
    cash_account = models.ForeignKey(
        "cash.CashAccount", on_delete=models.RESTRICT, related_name="operations"
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    occurred_on = models.DateField()
    # Daromad uchun tegishli oy (boshqa turlarda — pul oyi).
    period_year = models.PositiveSmallIntegerField()
    period_month = models.PositiveSmallIntegerField()
    counterparty = models.CharField(max_length=120, blank=True)
    reason = models.CharField(max_length=255)
    # Dividend soliqi — majburiyat (to'languncha).
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="money_operations",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "money_operation"
        ordering = ["-occurred_on", "-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="ck_money_operation_amount"
            ),
            models.CheckConstraint(
                condition=models.Q(tax_amount__gte=0), name="ck_money_operation_tax"
            ),
            models.CheckConstraint(
                condition=models.Q(period_month__gte=1, period_month__lte=12),
                name="ck_money_operation_month",
            ),
            models.CheckConstraint(
                condition=~models.Q(reason=""), name="ck_money_operation_reason"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.kind} {self.amount}"
