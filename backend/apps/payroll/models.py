"""
Oylik maosh (docs/03 §14.3–14.4).

Oylik hisoblash — bu **davriy va qaytarilmas** jarayon: yakunlangan
hisoblash o'zgarmaydi. Sabab moliyaviy ledger bilan bir xil: xodim
"o'tgan oyda menga qancha hisoblangan edi?" deb so'raganda javob bir
xil bo'lishi kerak, kim qachon so'rashidan qat'i nazar.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy

from apps.core.models import BranchScopedModel

__all__ = ["PayrollRun", "PayrollItem", "PayrollStatus"]


class PayrollStatus(models.TextChoices):
    DRAFT = "draft", gettext_lazy("Qoralama")
    FINALIZED = "finalized", gettext_lazy("Yakunlangan")
    PAID = "paid", gettext_lazy("To'langan")


class PayrollRun(BranchScopedModel):
    """
    Bir davr uchun oylik hisoblash sikli.

    Holatlar bir tomonlama: `draft → finalized → paid`. Orqaga qaytish
    yo'q — yakunlangandan keyin xato topilsa, keyingi oyda tuzatuvchi
    bonus/ushlab qolish bilan hal qilinadi. Bu ledger'dagi qarshi yozuv
    bilan bir xil mantiq (D3).
    """

    period_year = models.SmallIntegerField()
    period_month = models.SmallIntegerField()
    status = models.CharField(
        max_length=15, choices=PayrollStatus.choices, default=PayrollStatus.DRAFT
    )

    # Satrlardan keshlangan yig'indilar (docs/03 §8.2). Manba —
    # `payroll_item` qatorlari; ular har safar qayta hisoblanadi.
    total_gross = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    total_deductions = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    total_net = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))

    finalized_at = models.DateTimeField(null=True, blank=True)
    finalized_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="payroll_runs_finalized",
        null=True,
        blank=True,
    )
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "payroll_run"
        ordering = ["-period_year", "-period_month"]
        constraints = [
            # Bir filial — bir davr — bitta hisoblash. Ikkinchi hisoblash
            # xodimga ikki marta oylik to'lash xavfini yaratardi.
            models.UniqueConstraint(
                fields=["branch", "period_year", "period_month"],
                name="uq_payroll_run_branch_period",
            ),
            models.CheckConstraint(
                condition=models.Q(period_month__gte=1, period_month__lte=12),
                name="ck_payroll_period_month",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.period_year}-{self.period_month:02d} ({self.status})"

    @property
    def is_editable(self) -> bool:
        return self.status == PayrollStatus.DRAFT


class PayrollItem(BranchScopedModel):
    """
    Bir xodimning bir hisoblashdagi satri.

    `base_amount` — xodim maoshining SNAPSHOT'i, joriy qiymatiga havola
    emas. Maosh keyin oshsa, o'tgan oylarning hisoblashi o'zgarmasligi
    kerak — aks holda "o'tgan oy menga qancha hisoblangan edi?" degan
    savolga javob vaqt o'tishi bilan o'zgarardi.
    """

    payroll_run = models.ForeignKey(
        "payroll.PayrollRun", on_delete=models.CASCADE, related_name="items"
    )
    employee = models.ForeignKey(
        "hr.Employee", on_delete=models.RESTRICT, related_name="payroll_items"
    )

    base_amount = models.DecimalField(max_digits=12, decimal_places=2)
    bonus = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    deduction = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    gross = models.DecimalField(max_digits=12, decimal_places=2)
    net = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "payroll_item"
        ordering = ["employee__last_name", "employee__first_name"]
        constraints = [
            models.UniqueConstraint(fields=["payroll_run", "employee"], name="uq_payroll_item"),
            models.CheckConstraint(
                condition=models.Q(base_amount__gte=0), name="ck_payroll_item_base"
            ),
            models.CheckConstraint(condition=models.Q(bonus__gte=0), name="ck_payroll_item_bonus"),
            models.CheckConstraint(
                condition=models.Q(deduction__gte=0), name="ck_payroll_item_deduction"
            ),
            # Sof maosh manfiy bo'lolmaydi: ushlab qolish yalpi maoshdan
            # oshsa, xodim bog'chaga qarzdor bo'lib qolardi — bu oylik
            # hisoblashda ifodalanmaydigan holat.
            models.CheckConstraint(
                condition=models.Q(net__gte=0), name="ck_payroll_item_net_positive"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.employee_id}: {self.net}"
