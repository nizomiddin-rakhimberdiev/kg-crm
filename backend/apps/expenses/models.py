"""
Operatsion chiqimlar (docs/03 §16).

Chiqim oylik maosh va ombordan ALOHIDA hisobga olinadi — toza P&L
hisoboti uchun (docs/02 §6). Ularni bir joyga yig'ish "qaysi xarajat
qayerdan?" degan savolni javobsiz qoldirardi.
"""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy

from apps.core.models import BranchScopedModel

__all__ = ["ExpenseCategory", "Expense", "ExpenseStatus"]


class ExpenseCategory(BranchScopedModel):
    name = models.CharField(max_length=80)

    class Meta:
        db_table = "expense_category"
        ordering = ["name"]
        verbose_name_plural = "expense categories"
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "name"],
                condition=models.Q(is_active=True),
                name="uq_expense_category_branch_name",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class ExpenseStatus(models.TextChoices):
    PENDING = "pending", gettext_lazy("Kutilmoqda")
    APPROVED = "approved", gettext_lazy("Tasdiqlangan")
    REJECTED = "rejected", gettext_lazy("Rad etilgan")
    PAID = "paid", gettext_lazy("To'langan")


class Expense(BranchScopedModel):
    """
    Chiqim yozuvi tasdiqlash oqimi bilan.

    Holatlar: `pending → approved → paid`, yoki `pending → rejected`.
    Rad etilgan chiqim o'chirilmaydi — u nima so'ralgani va nega rad
    etilgani haqidagi yozuv bo'lib qoladi.
    """

    category = models.ForeignKey(
        "expenses.ExpenseCategory", on_delete=models.RESTRICT, related_name="expenses"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    expense_date = models.DateField()
    description = models.CharField(max_length=255, blank=True)

    status = models.CharField(
        max_length=12, choices=ExpenseStatus.choices, default=ExpenseStatus.PENDING
    )
    approved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="expenses_approved",
        null=True,
        blank=True,
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=255, blank=True)

    # Pul QAYSI qopdan chiqdi (ADR-17).
    #
    # Ataylab `null=True`: `pending` holatdagi so'rov hali hech qanday
    # pulni qimirlatmagan va uni kim to'lashini ham bilmasligi mumkin.
    # `paid` bo'lgan lahzada esa servis uni MAJBURIY qiladi — aynan
    # o'shanda kassa yozuvi yoziladi.
    cash_account = models.ForeignKey(
        "cash.CashAccount",
        on_delete=models.RESTRICT,
        related_name="expenses",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "expense"
        ordering = ["-expense_date", "-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="ck_expense_amount_positive"
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "branch", "expense_date"],
                name="ix_expense_org_br_date",
            ),
            models.Index(fields=["status"], name="ix_expense_status"),
        ]

    def __str__(self) -> str:
        return f"{self.amount} ({self.category_id})"
