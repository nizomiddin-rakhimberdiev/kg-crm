"""
Xodimlar (docs/03 §14.1–14.2).

`Employee` va `User` — **alohida** entitelar (docs/02 §6): oshpaz tizimga
kirmasligi mumkin, lekin oylik oladi; hisobchi esa tizimga kiradi, lekin
bu bog'chaning xodimi bo'lmasligi mumkin. Ularni birlashtirish auth
modelini oylik ma'lumotlari bilan ifloslantirardi.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import models
from django.utils.translation import gettext_lazy

from apps.core.models import BranchScopedModel

__all__ = ["Position", "Employee", "EmploymentStatus", "WorkMode"]


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
    ON_LEAVE = "on_leave", gettext_lazy("Taʼtilda")
    TERMINATED = "terminated", gettext_lazy("Ishdan boʻshagan")


class WorkMode(models.TextChoices):
    """
    Xodimga pul qanday hisoblanadi.

    Bu ro'yxat ataylab QISQA. "To'liq kun", "yarim stavka", "haftada uch
    kun" — bularning hammasi pul nuqtai nazaridan bitta narsa: oylik
    maosh va shu maosh qaysi kunlarga tegishli (`work_days`). Ularni
    alohida tur qilish uchta bir xil hisob-kitobni uchta joyda
    saqlashni anglatardi. Soatbay esa haqiqatan boshqacha: u kelgan
    kunlardan hisoblanadi, maoshdan emas.
    """

    MONTHLY = "monthly", gettext_lazy("Oylik maosh")
    HOURLY = "hourly", gettext_lazy("Soatbay")


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
    # Tizim hisobi bilan bog'lanish (PLAN 2.8).
    #
    # Ikkisi ATAYLAB alohida: hamma xodim tizimga kirmaydi (oshpazga
    # hisob kerak emas), va hamma hisob xodim emas (buxgalter
    # tashqaridan bo'lishi mumkin). Lekin bog'lanish KERAK — usiz
    # "men qaysi guruhning tarbiyachisiman?" degan savolga javob yo'q,
    # ya'ni tarbiyachi roli faqat o'z guruhini ko'ra olmaydi (PLAN 2.6).
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

    # --- Ish grafigi (PLAN 9.1) ---
    #
    # Grafik — bezak emas, PULNING maxraji: haftada uch kun keladigan
    # tarbiyachi oy o'rtasida ishga kirsa, uning proporsiyasi filialning
    # 22 ish kunidan emas, O'ZINING 13 kunidan chiqishi kerak. Ilgari
    # bunday xodim ishga kirgan oyida kamroq olardi va buni hech kim
    # payslipdan tushuntira olmasdi.
    work_mode = models.CharField(max_length=10, choices=WorkMode.choices, default=WorkMode.MONTHLY)
    #: ISO kunlar, vergul bilan: "1,3,5". BO'SH = filial kalendari
    #: (`attendance.working_weekdays`) — ko'pchilik xodim shunday.
    work_days = models.CharField(max_length=20, blank=True)
    #: Soatbay uchun: bir kunda necha soat va soatiga qancha.
    hours_per_day = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal("0"))
    hourly_rate = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
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

    # Qidiruv kaliti (PLAN 2.7) — bola va vasiy bilan bir xil qoida.
    search_key = models.CharField(max_length=255, blank=True, db_index=True)

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
            # Soatbay xodimda soat narxi ham, kunlik soat ham bo'lishi
            # SHART: aks holda oylik hisoblashda uning satri jimgina
            # nol bo'lib chiqardi.
            models.CheckConstraint(
                condition=(
                    ~models.Q(work_mode="hourly")
                    | (models.Q(hourly_rate__gt=0) & models.Q(hours_per_day__gt=0))
                ),
                name="ck_employee_hourly_rate",
            ),
            models.CheckConstraint(
                condition=models.Q(hours_per_day__gte=0) & models.Q(hours_per_day__lte=24),
                name="ck_employee_hours_per_day",
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

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Qidiruv kaliti HAR SAQLASHDA qayta hisoblanadi (PLAN 2.7)."""
        from apps.core.translit import search_key as _key

        self.search_key = _key(f"{self.last_name} {self.first_name} {self.phone}")
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.full_name

    @property
    def full_name(self) -> str:
        return f"{self.last_name} {self.first_name}"

    @property
    def weekdays(self) -> list[int]:
        """Xodimning ish kunlari (ISO 1–7). Bo'sh bo'lsa — filial kalendari."""
        if not self.work_days:
            from apps.attendance.services_absence import working_weekdays

            return sorted(working_weekdays(self.branch))
        return sorted({int(part) for part in self.work_days.split(",") if part.strip().isdigit()})
