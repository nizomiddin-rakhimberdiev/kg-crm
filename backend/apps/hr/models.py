"""
Xodimlar (docs/03 §14.1–14.2).

`Employee` va `User` — **alohida** entitelar (docs/02 §6): oshpaz tizimga
kirmasligi mumkin, lekin oylik oladi; hisobchi esa tizimga kiradi, lekin
bu bog'chaning xodimi bo'lmasligi mumkin. Ularni birlashtirish auth
modelini oylik ma'lumotlari bilan ifloslantirardi.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy

from apps.core.models import BranchScopedModel

__all__ = ["Position", "Employee", "EmploymentStatus"]


class Position(BranchScopedModel):
    """Lavozim (tarbiyachi, oshpaz, farrosh)."""

    title = models.CharField(max_length=80)
    department = models.CharField(max_length=60, blank=True)

    class Meta:
        db_table = "position"
        ordering = ["title"]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "title"],
                condition=models.Q(is_active=True),
                name="uq_position_branch_title",
            ),
        ]

    def __str__(self) -> str:
        return self.title


class EmploymentStatus(models.TextChoices):
    ACTIVE = "active", gettext_lazy("Ishlayapti")
    ON_LEAVE = "on_leave", gettext_lazy("Ta'tilda")
    TERMINATED = "terminated", gettext_lazy("Ishdan bo'shagan")


class Employee(BranchScopedModel):
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    phone = models.CharField(max_length=20, blank=True)

    position = models.ForeignKey(
        "hr.Position",
        on_delete=models.SET_NULL,
        related_name="employees",
        null=True,
        blank=True,
    )
    # Ixtiyoriy login bog'lanishi — kelajakdagi Tarbiyachi portali uchun
    # (docs/02 §22.2). Hozircha ko'p xodimda `NULL`.
    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="employee",
        null=True,
        blank=True,
    )

    employment_status = models.CharField(
        max_length=15, choices=EmploymentStatus.choices, default=EmploymentStatus.ACTIVE
    )
    hire_date = models.DateField()
    termination_date = models.DateField(null=True, blank=True)

    # Oylik bazaviy maosh. Oylik hisoblashda bu qiymat `payroll_item` ga
    # NUSXALANADI — keyin maosh o'zgarsa, o'tgan oylar o'zgarmasligi kerak.
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))

    # Maoshning RASMIY qismi — bankka, kartaga, soliq ushlab qolingan
    # holda (ADR-18). Qolgani (`base_salary − official_salary`) naqd.
    #
    # Nega bitta jami va bitta bo'linish, ikkita mustaqil ustun emas:
    # `base_salary` "bu odam qancha oladi?" degan savolning yagona
    # javobi bo'lib qoladi, ya'ni uni o'qiydigan hech narsa ma'nosini
    # o'zgartirmaydi. Ikkita erkin ustun esa jamini hech kim egalik
    # qilmaydigan yig'indiga aylantirardi — va ular birinchi marta
    # farq qilgan kunda payslip mehnat shartnomasiga zid bo'lardi.
    official_salary = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))

    class Meta:
        db_table = "employee"
        ordering = ["last_name", "first_name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(base_salary__gte=0), name="ck_employee_salary_positive"
            ),
            # Rasmiy qism jamidan oshib ketolmaydi — aks holda naqd qism
            # manfiy bo'lib, payslip ma'nosiz raqam ko'rsatardi.
            models.CheckConstraint(
                condition=models.Q(official_salary__gte=0)
                & models.Q(official_salary__lte=models.F("base_salary")),
                name="ck_employee_official_within_base",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(termination_date__isnull=True)
                    | models.Q(termination_date__gte=models.F("hire_date"))
                ),
                name="ck_employee_termination",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "branch", "employment_status"],
                name="ix_employee_org_br_status",
            ),
        ]

    def __str__(self) -> str:
        return self.full_name

    @property
    def full_name(self) -> str:
        return f"{self.last_name} {self.first_name}"
