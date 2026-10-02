"""
Xodimlar davomati — kunlik tabel (docs/03 §12.3, 2026-10).

Mijoz so'rovi: oylik hisobotini chiqarish oson bo'lsin. Buxgalter oy
oxirida har bir xodim nechta kun ishlaganini, kasal yoki ta'tilda
bo'lganini bilishi kerak — avval bu qog'ozda yuritilardi.

Bolalar davomatidan farqi — holatlar: kasallik va ta'til ALOHIDA, chunki
oylik maoshda ular turlicha hisoblanadi (bolalarda bitta "sababli"
yetarli edi). Maosh avtomatik o'zgartirilmaydi: tabel — fakt, oylikka
qanday ta'sir qilishi esa buxgalterning qarori.
"""

from __future__ import annotations

from datetime import timedelta

from django.db import models
from django.db.models.functions import Now, TruncDate
from django.utils.translation import gettext_lazy

from apps.core.models import BranchScopedModel

__all__ = ["StaffAttendance", "StaffAttendanceStatus"]


class StaffAttendanceStatus(models.TextChoices):
    PRESENT = "present", gettext_lazy("Keldi")
    ABSENT = "absent", gettext_lazy("Kelmadi")
    SICK = "sick", gettext_lazy("Kasal")
    LEAVE = "leave", gettext_lazy("Ta'tilda")


class StaffAttendance(BranchScopedModel):
    """
    Bir xodim — bir kun — bir yozuv.

    Bolalar davomati kabi o'rniga yoziladi (upsert): kun holati — fakt,
    pul harakati emas. Ertalab "kelmadi" deb belgilangan xodim soat 10 da
    kelsa, uni tuzatish oddiy ish oqimi.
    """

    employee = models.ForeignKey(
        "hr.Employee", on_delete=models.RESTRICT, related_name="attendance_records"
    )
    attendance_date = models.DateField()
    status = models.CharField(max_length=10, choices=StaffAttendanceStatus.choices)
    note = models.CharField(max_length=255, blank=True)
    recorded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="staff_attendance_records",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "staff_attendance"
        ordering = ["-attendance_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "attendance_date"], name="uq_staff_attendance_employee_date"
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=StaffAttendanceStatus.values),
                name="ck_staff_attendance_status",
            ),
            # Bolalar davomatidagi kabi bir kunlik zaxira bilan: aniq qoida
            # (`> bugun` rad etiladi) servisda, filial vaqtida.
            models.CheckConstraint(
                condition=models.Q(attendance_date__lte=TruncDate(Now()) + timedelta(days=1)),
                name="ck_staff_attendance_not_future",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "branch", "attendance_date"],
                name="ix_staff_att_org_br_date",
            ),
            models.Index(fields=["employee", "-attendance_date"], name="ix_staff_att_emp_date"),
        ]

    def __str__(self) -> str:
        return f"{self.employee_id} · {self.attendance_date} · {self.status}"
