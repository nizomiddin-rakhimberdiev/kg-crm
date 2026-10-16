"""
Operatsion chiqimlar (docs/03 §16).

Chiqim oylik maosh va ombordan ALOHIDA hisobga olinadi — toza P&L
hisoboti uchun (docs/02 §6). Ularni bir joyga yig'ish "qaysi xarajat
qayerdan?" degan savolni javobsiz qoldirardi.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from pathlib import PurePosixPath
from typing import Any

from django.db import models
from django.utils.translation import gettext_lazy

from apps.core.models import BranchScopedModel

__all__ = ["ExpenseCategory", "Expense", "ExpenseStatus", "ExpenseItem"]


class ExpenseCategory(BranchScopedModel):
    name = models.CharField(max_length=80)
    # Ikki daraja (Bosqich 13.2a): "Oziq-ovqat" → "Go'sht". Uchinchi daraja
    # yo'q — serializer ruxsat bermaydi; hisobot ikki darajada yig'adi.
    parent = models.ForeignKey(
        "self", on_delete=models.RESTRICT, related_name="children", null=True, blank=True
    )
    # Buxgalteriya hisob kodi (brif §9) — buxgalter eksporti uchun.
    account_code = models.CharField(max_length=20, blank=True)

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


def expense_receipt_path(instance: Any, filename: str) -> str:
    """`media/{organization}/receipts/{uuid}.{ext}` — nom taxmin qilinmasin."""
    suffix = PurePosixPath(filename).suffix.lower() or ".jpg"
    return f"{instance.organization_id}/receipts/{uuid.uuid4()}{suffix}"


class ExpenseStatus(models.TextChoices):
    PENDING = "pending", gettext_lazy("Kutilmoqda")
    APPROVED = "approved", gettext_lazy("Tasdiqlangan")
    REJECTED = "rejected", gettext_lazy("Rad etilgan")
    PAID = "paid", gettext_lazy("Toʻlangan")


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
    # Bank komissiyasi shu to'lovdan (Bosqich 12.5) — bitta to'lovga bitta
    # komissiya. `SET_NULL`: chiqim to'lovning bolasi emas, u bankning
    # alohida hujjati; to'lov qaytarilsa ham bank komissiyani qaytarmaydi.
    payment = models.ForeignKey(
        "finance.Payment",
        on_delete=models.SET_NULL,
        related_name="commissions",
        null=True,
        blank=True,
    )

    # --- Bosqich 13.2a: ikki sana va xarajat tabiati ---
    #
    # Tegishli oy — foyda-zarar shu oyga yozadi; pul oqimi esa pul
    # harakati sanasiga. `NULL` — to'langan oy (eski yozuvlar o'zgartirilmaydi:
    # selektorlar `expense_date` oyini oladi).
    period_year = models.PositiveSmallIntegerField(null=True, blank=True)
    period_month = models.PositiveSmallIntegerField(null=True, blank=True)
    # Investitsiya (ta'mir, mebel, konditsioner): operatsion foydani
    # buzmaydi. `amortize_months` berilsa — foyda-zararga shuncha oyga
    # teng bo'lib tushadi; berilmasa — alohida qatorda.
    is_capex = models.BooleanField(default=False)
    amortize_months = models.PositiveSmallIntegerField(null=True, blank=True)
    # Nasiya: xarajat bor, pul hali chiqmagan — yetkazib beruvchiga qarz.
    on_credit = models.BooleanField(default=False)
    supplier = models.ForeignKey(
        "inventory.Supplier",
        on_delete=models.RESTRICT,
        related_name="expenses",
        null=True,
        blank=True,
    )
    due_date = models.DateField(null=True, blank=True)
    # Pul haqiqatan qachon chiqdi. Nasiyada — to'langanda; oddiy chiqimda —
    # `expense_date`. Eski yozuvlarda `NULL` = `expense_date`.
    paid_on = models.DateField(null=True, blank=True)
    # Chek rasmi yoki PDF (Bosqich 13.3a) — "ma'lumot to'liqligi" va
    # "hujjatsiz katta xarajat" nazorati shundan o'qiydi.
    receipt = models.FileField(upload_to=expense_receipt_path, blank=True)

    class Meta:
        db_table = "expense"
        ordering = ["-expense_date", "-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="ck_expense_amount_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(period_month__isnull=True)
                | models.Q(period_month__gte=1, period_month__lte=12),
                name="ck_expense_period_month",
            ),
            # Taqsimlash faqat investitsiyada, 1..120 oy.
            models.CheckConstraint(
                condition=models.Q(amortize_months__isnull=True)
                | models.Q(is_capex=True, amortize_months__gte=1, amortize_months__lte=120),
                name="ck_expense_amortize",
            ),
            # Nasiya — yetkazib beruvchisi bilan.
            models.CheckConstraint(
                condition=models.Q(on_credit=False) | models.Q(supplier__isnull=False),
                name="ck_expense_credit_supplier",
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


class ExpenseItem(BranchScopedModel):
    """
    Chiqim ichidagi bitta qator (PLAN 7.5).

    Mijozning so'zi: "bozorlik" degan 600 000 so'm yetarli emas — nima
    olingani, qancha va qanchadan olingani kerak. Shuning uchun chiqim
    endi qatorlardan iborat: *kartoshka, 50 kg, 3 000 so'm → 150 000*.

    **`line_total` saqlanadi, hisoblanmaydi.** Miqdor × narx har safar
    qayta hisoblansa, yaxlitlash ekranda va hisobotda boshqacha
    chiqishi mumkin; saqlangan qiymat esa chiqim summasi bilan aynan
    mos tushadi. `Expense.amount` — qatorlar yig'indisi, va bu kassaga
    chiqadigan pul (ADR-17).

    Qatorlar IXTIYORIY: eski chiqimlarda ular yo'q va shunday qoladi —
    yozuvni orqaga qarab to'ldirib bo'lmaydi.
    """

    expense = models.ForeignKey("expenses.Expense", on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=120)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit = models.CharField(max_length=10, default="dona")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "expense_item"
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=Decimal("0")), name="ck_expense_item_quantity"
            ),
            models.CheckConstraint(
                condition=models.Q(unit_price__gte=Decimal("0")), name="ck_expense_item_price"
            ),
            models.CheckConstraint(
                condition=models.Q(line_total__gte=Decimal("0")), name="ck_expense_item_total"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} {self.quantity}{self.unit} × {self.unit_price}"


class ExpenseDraft(BranchScopedModel):
    """
    Telegram'dan kelgan chiqim — toifa tanlanguncha (Bosqich 13.3c).

    Bot holatsiz: tugma `x:<qoralama>:<raqam>` ni qaytaradi va qoralama
    taklif qilingan toifalar ro'yxatini saqlaydi. Tugma ikki marta
    bosilsa ham chiqim bitta — `expense` to'lgan bo'ladi.
    """

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="expense_drafts"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.CharField(max_length=255, blank=True)
    photo_file_id = models.CharField(max_length=255, blank=True)
    category_ids = models.JSONField(default=list)
    expense = models.ForeignKey(
        "expenses.Expense",
        on_delete=models.SET_NULL,
        related_name="drafts",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "expense_draft"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="ck_expense_draft_amount")
        ]

    def __str__(self) -> str:
        return f"{self.amount} ({self.user_id})"
