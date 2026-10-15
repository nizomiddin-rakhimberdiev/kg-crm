"""
Kunlik davomat (docs/03 §12).

Yuqori hajmli jadval: 200 bolali bog'chada yiliga ~44 000 qator. O'sish
bilan oy bo'yicha partitsiyalash nomzodi (docs/03 §27).
"""

from __future__ import annotations

from datetime import timedelta

from django.db import models
from django.db.models.functions import Now, TruncDate
from django.utils.translation import gettext_lazy

from apps.core.models import BranchScopedModel

__all__ = ["AttendanceRecord", "AttendanceStatus"]


class AttendanceStatus(models.TextChoices):
    """
    Kunlik davomat holati.

    "Kechikdi" ataylab yo'q: davomat uchun kun yakunida javob beriladigan
    savol — bola bog'chada bo'ldimi yoki yo'qmi. Kechikish esa hisob-kitobga
    (to'lov, ovqat, guruh sig'imi) hech qanday ta'sir qilmasdi, lekin har
    kuni har bir bola uchun qo'shimcha qaror talab qilardi. Kelgan bola —
    `present`; kelish vaqti kerak bo'lsa, `check_in_at` da turadi.
    """

    PRESENT = "present", gettext_lazy("Keldi")
    ABSENT = "absent", gettext_lazy("Kelmagan")
    EXCUSED = "excused", gettext_lazy("Sababli")


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
            #
            # Cheklov bir kunlik ZAXIRA bilan: `Now()` Postgres'da UTC
            # beradi, filial vaqti esa o'zining zonasida (`branch.timezone`,
            # masalan UTC+5). Yarim tundan keyin lokal sana UTC sanadan bir
            # kun oldinda bo'ladi va qat'iy taqqoslash har kuni ertalab
            # to'g'ri yozuvni rad etardi.
            #
            # Bu qo'pol sanitar tekshiruv: u "kelasi oy" kabi xatoni
            # ushlaydi. ANIQ qoida (`> bugun` rad etiladi) servis va
            # serializer qatlamida, filial vaqt zonasi ma'lum bo'lgan
            # joyda qo'llanadi.
            models.CheckConstraint(
                condition=models.Q(attendance_date__lte=TruncDate(Now()) + timedelta(days=1)),
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


# Kelmagan kunlar uchun qaytarish va bayram kalendari alohida faylda
# (ADR-19) — ular davomat bilan BIR MODULDA yashaydi, lekin bir-biridan
# hech narsa o'qimaydi, va shu ajratish aynan shuni ko'rsatib turadi.
from apps.attendance.models_absence import (  # noqa: E402
    AbsenceClaim,
    AbsenceKind,
    ClaimKind,
    ClaimStatus,
    Holiday,
    RefundMode,
)

__all__ = [
    *__all__,
    "AbsenceClaim",
    "AbsenceKind",
    "ClaimKind",
    "ClaimStatus",
    "Holiday",
    "RefundMode",
]

# Xodimlar davomati (tabel) — alohida faylda: bolalar jurnali bilan bir
# modulda (bir xil "davomat" ruxsati), lekin bir-biridan hech narsa o'qimaydi.
from apps.attendance.models_staff import StaffAttendance, StaffAttendanceStatus  # noqa: E402

__all__ = [*__all__, "StaffAttendance", "StaffAttendanceStatus"]
