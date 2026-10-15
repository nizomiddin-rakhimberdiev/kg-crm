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

__all__ = ["PayrollPayout", "PayoutPart", "PayrollRun", "PayrollItem", "PayrollStatus"]


class PayrollStatus(models.TextChoices):
    DRAFT = "draft", gettext_lazy("Qoralama")
    FINALIZED = "finalized", gettext_lazy("Yakunlangan")
    PAID = "paid", gettext_lazy("Toʻlangan")


class PayrollRun(BranchScopedModel):
    """
    Bir davr uchun oylik hisoblash sikli.

    Holatlar: `draft → finalized → paid`. Odatdagi yo'l oldinga, lekin
    ORQAGA qaytish ham bor — `reopen_run()` hisoblashni qoralamaga
    qaytaradi, sabab so'raydi va audit jurnaliga yozadi.

    Nega bir tomonlama emas: hisoblash — HUJJAT, o'zgarmas pul yozuvi
    emas. "Xatoni keyingi oyda tuzating" degan qoida buxgalteriyada
    to'g'ri, lekin oylikni hali bermagan bog'cha uchun javob emas —
    birinchi mijozda aynan shu holat chiqdi. O'zgarmaslik qoidasi (D3)
    o'z kuchida qoladigan joy — pul yozuvlari: `child_ledger_entry`,
    `stock_movement`, `employee_advance`. Ular qayta ochishda
    TEGILMAYDI.
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
    # Ish beruvchi soliqlari (Q10) — xodim qo'liga tegmaydigan, lekin
    # bog'cha to'laydigan summa. Foyda-zararda oylik xarajati aynan
    # `total_gross + total_social_tax` bo'ladi.
    total_social_tax = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))

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
    # Oy davomida BERIB YUBORILGAN pul. `deduction` dan alohida: ushlab
    # qolish — jarima yoki hisob-kitob, avans esa xodim allaqachon olgan
    # maoshning bir qismi. Ularni bitta ustunga qo'shish payslipni
    # tushunarsiz qilardi ("nega 3 mln ushlab qolindi?").
    advance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    # Farzandining bog'cha to'lovi — oyligidan ushlangan (Bosqich 12.4).
    # Alohida ustun: payslip "jarima" emas, "bog'cha to'lovi" deb aytsin.
    # Manba — `payment.method = payroll` qatorlari, davr bo'yicha.
    tuition = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    # Ish beruvchi ijtimoiy solig'i — rasmiy qismdan hisoblanadi va
    # xodimdan USHLANMAYDI (Q10).
    tax_social = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    # --- Rasmiy qism (ADR-18): bankka, soliq ushlab qolingan holda ---
    #
    # Stavkalar Sozlamalardan olinadi, lekin natija SHU YERGA
    # suratga olinadi: martda o'zgargan stavka fevralning payslipini
    # jimgina qayta yozmasligi kerak.
    official_base = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    tax_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    tax_pension = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    official_net = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))

    # --- Naqd qism: qolgan maosh + bonus − ushlab qolish − avans ---
    #
    # Ikkita sof summa ATAYLAB alohida turadi, erta qo'shilmaydi:
    # ular BOSHQA qoplardan chiqadi (docs/03 §13a), va bitta `net`
    # bank hisobini kassadan ajrata olmaydi.
    cash_net = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))

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


class PayoutPart(models.TextChoices):
    OFFICIAL = "official", gettext_lazy("Rasmiy (bank)")
    CASH = "cash", gettext_lazy("Naqd")


class PayrollPayout(BranchScopedModel):
    """
    Oylikdan HAQIQATAN chiqqan pul (docs/03 §14.4a, ADR-17).

    `payroll_item` — hisoblangan hujjat; bu esa pulning o'zi. Bittasi
    ikkinchisining o'rnini bosa olmaydi: hisoblash qayta ochilishi
    mumkin, chiqib ketgan pul esa qayta ochilmaydi.

    Shuning uchun `payroll_run` ga `RESTRICT` bilan bog'langan —
    `CASCADE` bo'lsa, qayta ochish paytida chiqib ketgan pulning izi
    jimgina o'chib ketardi.
    """

    payroll_run = models.ForeignKey(
        "payroll.PayrollRun", on_delete=models.RESTRICT, related_name="payouts"
    )
    payroll_item = models.ForeignKey(
        "payroll.PayrollItem",
        on_delete=models.RESTRICT,
        related_name="payouts",
        null=True,
        blank=True,
    )
    cash_account = models.ForeignKey(
        "cash.CashAccount", on_delete=models.RESTRICT, related_name="payroll_payouts"
    )
    part = models.CharField(max_length=10, choices=PayoutPart.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_on = models.DateField()
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="payroll_payouts",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "payroll_payout"
        ordering = ["-paid_on", "-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="ck_payroll_payout_amount_positive"
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "paid_on"], name="ix_payroll_payout_org_date"),
        ]

    def __str__(self) -> str:
        return f"{self.amount} ({self.part})"


class EmployeeAdvance(BranchScopedModel):
    """
    Oy davomida xodimga berilgan avans.

    Nega alohida jadval, `PayrollItem.advance` maydonining o'zi emas: avans
    oylik hisoblashdan OLDIN beriladi (masalan 15-kuni), hisoblash esa oy
    oxirida yaratiladi. Har bir berilgan pul o'z sanasi va izohi bilan
    yozilib turishi kerak — "kim, qachon, qancha oldi" degan savol oy
    oxirida emas, o'sha kuni javob topadi.

    Davr bo'yicha bog'lanadi (`paid_on` oyi), maxsus bog'lovchi ustun
    orqali emas: shunda qayta hisoblash idempotent bo'ladi va hisoblash
    o'chirib qayta yaratilsa ham avanslar joyida qoladi.
    """

    employee = models.ForeignKey("hr.Employee", on_delete=models.RESTRICT, related_name="advances")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_on = models.DateField()
    # Avans QAYSI qopdan chiqqani (ADR-29). Ilgari u hamisha naqd
    # kassadan yechilardi va buni hech kim tanlamasdi — ya'ni "pul
    # qayerdan ketdi?" degan savolga javob yo'q edi. Eski qatorlarda
    # bo'sh: ularning harakati naqd kassada turibdi, uni o'zgartirmaymiz.
    cash_account = models.ForeignKey(
        "cash.CashAccount",
        on_delete=models.RESTRICT,
        related_name="advances",
        null=True,
        blank=True,
    )
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="created_advances",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "employee_advance"
        ordering = ["-paid_on"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=Decimal("0")), name="ck_advance_amount_positive"
            ),
        ]
        indexes = [
            models.Index(fields=["employee", "paid_on"], name="ix_advance_employee_date"),
        ]

    def __str__(self) -> str:
        return f"{self.employee_id} — {self.amount} ({self.paid_on})"
