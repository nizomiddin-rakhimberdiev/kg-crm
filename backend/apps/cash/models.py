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
    "CashMovement",
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
