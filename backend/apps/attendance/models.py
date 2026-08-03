"""
Kunlik davomat (docs/03 §12).

Yuqori hajmli jadval: 200 bolali bog'chada yiliga ~44 000 qator. O'sish
bilan oy bo'yicha partitsiyalash nomzodi (docs/03 §27).
"""

from __future__ import annotations

from django.db import models
from django.db.models.functions import Now

from apps.core.models import BranchScopedModel

__all__ = ["AttendanceRecord", "AttendanceStatus"]


class AttendanceStatus(models.TextChoices):
    PRESENT = "present", "Keldi"
    ABSENT = "absent", "Kelmagan"
    EXCUSED = "excused", "Sababli"
    LATE = "late", "Kechikdi"


class AttendanceRecord(BranchScopedModel):
    """
    Bir bola — bir kun — bir yozuv.

    Bu **yagona** operatsion jadval bo'lib, unda o'rniga yozish (UPDATE)
    ruxsat etiladi: kunning holati bitta fakt, pul harakati emas. Kassir
    ertalab "kelmagan" deb belgilab, soat 10 da bola kelganda uni
    tuzatishi normal ish oqimi — bu tuzatish uchun qarshi yozuv yaratish
    ledger mantig'ini noto'g'ri joyga ko'chirish bo'lardi (docs/03 §12.1).
    """

    child = models.ForeignKey(
        "children.Child", on_delete=models.CASCADE, related_name="attendance_records"
    )
    # Yozuv paytidagi guruh. `SET NULL`: guruh o'chirilsa ham davomat
    # tarixi qoladi — u boshqa maqsadda (hisobot, moliya) kerak bo'ladi.
    group = models.ForeignKey(
        "children.Group",
        on_delete=models.SET_NULL,
        related_name="attendance_records",
        null=True,
        blank=True,
    )
    attendance_date = models.DateField()
    status = models.CharField(max_length=15, choices=AttendanceStatus.choices)
    check_in_at = models.DateTimeField(null=True, blank=True)
    check_out_at = models.DateTimeField(null=True, blank=True)
    reason = models.CharField(max_length=255, blank=True)
    recorded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="attendance_records",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "attendance_record"
        ordering = ["-attendance_date", "child__last_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["child", "attendance_date"], name="uq_attendance_child_date"
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(check_out_at__isnull=True)
                    | models.Q(check_in_at__isnull=True)
                    | models.Q(check_out_at__gte=models.F("check_in_at"))
                ),
                name="ck_attendance_checkout",
            ),
            # Kelajakdagi kunga davomat belgilash — deyarli har doim
            # sana maydonidagi xato.
            models.CheckConstraint(
                condition=models.Q(attendance_date__lte=Now()),
                name="ck_attendance_not_future",
            ),
        ]
        indexes = [
            models.Index(fields=["child", "-attendance_date"], name="ix_attendance_child_date"),
            models.Index(
                fields=["organization", "branch", "attendance_date"],
                name="ix_attendance_org_br_date",
            ),
            models.Index(fields=["group", "attendance_date"], name="ix_attendance_group_date"),
        ]

    def __str__(self) -> str:
        return f"{self.child_id} · {self.attendance_date} · {self.status}"
