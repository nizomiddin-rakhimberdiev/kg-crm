"""Davomat biznes mantiqi (docs/04 §8)."""

from __future__ import annotations

from datetime import date
from typing import Any

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.translation import gettext

from apps.attendance.models import AttendanceRecord, AttendanceStatus
from apps.children.models import Child, Enrollment, EnrollmentState, Group
from apps.core.exceptions import BusinessRuleViolation

__all__ = ["mark_bulk", "daily_register", "monthly_summary"]


@transaction.atomic
def mark_bulk(
    *,
    organization: Any,
    branch: Any,
    group: Group,
    attendance_date: date,
    records: list[dict[str, Any]],
    recorded_by: Any = None,
    reason: str = "",
) -> list[AttendanceRecord]:
    """
    Bir guruhning bir kunini bitta chaqiruvda belgilaydi.

    Qayta yuborish yozuvlarni YANGILAYDI (upsert): tarbiyachi ertalab
    belgilab, tushdan keyin tuzatishi — normal ish oqimi, xato emas.
    """
    if attendance_date > timezone.localdate():
        raise BusinessRuleViolation(gettext("Kelajakdagi kunga davomat belgilab boʻlmaydi."))

    if group.organization_id != organization.id:
        raise BusinessRuleViolation(gettext("Guruh boshqa tashkilotga tegishli."))

    assert_can_mark(user=recorded_by, group=group, attendance_date=attendance_date, reason=reason)

    # Guruhdagi faol bolalar — faqat shularni belgilash mumkin. Aks holda
    # mijoz istalgan `child_id` yuborib, boshqa guruhning bolasiga yozuv
    # yaratishi mumkin bo'lardi.
    allowed = set(
        Enrollment.objects.filter(
            group=group, status=EnrollmentState.ACTIVE, end_date__isnull=True
        ).values_list("child_id", flat=True)
    )

    valid_statuses = set(AttendanceStatus.values)
    saved: list[AttendanceRecord] = []

    for row in records:
        child_id = row.get("child_id")
        if child_id not in allowed:
            raise BusinessRuleViolation(
                gettext("Bola {child_id} bu guruhda faol emas.").format(child_id=child_id)
            )

        status = row.get("status")
        if status not in valid_statuses:
            raise BusinessRuleViolation(gettext("Nomaʼlum holat: {status}").format(status=status))

        record, _ = AttendanceRecord.objects.update_or_create(
            child_id=child_id,
            attendance_date=attendance_date,
            defaults={
                "organization": organization,
                "branch": branch,
                "group": group,
                "status": status,
                "check_in_at": row.get("check_in_at"),
                "check_out_at": row.get("check_out_at"),
                "reason": row.get("reason", "") or "",
                "recorded_by": recorded_by,
            },
        )
        saved.append(record)

    # Oylik davomat foizi dashboardda — kesh eskirdi.
    from apps.reports.services import invalidate_dashboard_on_commit

    invalidate_dashboard_on_commit(organization_id=organization.id)
    return saved


def daily_register(*, group: Group, attendance_date: date) -> list[dict[str, Any]]:
    """
    Guruhning bir kunlik jurnali.

    Har bir faol bola uchun qator qaytaradi — davomat belgilanmagan bo'lsa
    `status=None`. Frontend to'liq ro'yxatni ko'rsatishi kerak, faqat
    belgilanganlarini emas: tarbiyachiga "kim qoldi?" degan savol javobsiz
    qolmasin.
    """
    children = list(
        Child.objects.filter(
            enrollments__group=group,
            enrollments__status=EnrollmentState.ACTIVE,
            enrollments__end_date__isnull=True,
            is_active=True,
        ).order_by("last_name", "first_name")
    )

    existing = {
        record.child_id: record
        for record in AttendanceRecord.objects.filter(group=group, attendance_date=attendance_date)
    }

    return [
        {
            "child_id": str(child.id),
            "full_name": child.full_name,
            "status": existing[child.id].status if child.id in existing else None,
            "reason": existing[child.id].reason if child.id in existing else "",
            "check_in_at": existing[child.id].check_in_at if child.id in existing else None,
            "record_id": str(existing[child.id].id) if child.id in existing else None,
        }
        for child in children
    ]


def monthly_summary(
    *, organization_id: Any, year: int, month: int, group: Group | None = None
) -> list[dict[str, Any]]:
    """Oylik yig'ma: bola bo'yicha holatlar soni."""
    queryset = AttendanceRecord.objects.filter(
        organization_id=organization_id,
        attendance_date__year=year,
        attendance_date__month=month,
    )
    if group is not None:
        queryset = queryset.filter(group=group)

    # Bitta so'rovda agregatsiya — Python'da sikl bilan hisoblash
    # 200 bola × 22 kun da sezilarli sekinlashuv beradi (docs/02 §21.1).
    rows = (
        queryset.values("child_id", "child__first_name", "child__last_name")
        .annotate(
            present=Count("id", filter=Q(status=AttendanceStatus.PRESENT)),
            absent=Count("id", filter=Q(status=AttendanceStatus.ABSENT)),
            excused=Count("id", filter=Q(status=AttendanceStatus.EXCUSED)),
            total=Count("id"),
        )
        .order_by("child__last_name", "child__first_name")
    )

    return [
        {
            "child_id": str(row["child_id"]),
            "full_name": f"{row['child__last_name']} {row['child__first_name']}",
            "present": row["present"],
            "absent": row["absent"],
            "excused": row["excused"],
            "total": row["total"],
            "attendance_rate": (
                round(row["present"] / row["total"] * 100, 1) if row["total"] else 0.0
            ),
        }
        for row in rows
    ]


# --- Kim qaysi kunni belgilay oladi (PLAN 2.6) ---


def teacher_edit_window(branch: Any = None) -> int:
    """Tarbiyachi necha kun orqaga qaytib belgilay oladi."""
    from apps.settings_app.services import get_setting

    return int(get_setting(key="attendance.teacher_edit_days", branch=branch) or 0)


def assert_can_mark(*, user: Any, group: Group, attendance_date: date, reason: str = "") -> None:
    """
    Shu odam shu guruhning shu kunini belgilay oladimi?

    Ikki tekshiruv:

    1. **Guruh** — guruhga biriktirilgan tarbiyachi faqat o'z guruhini
       belgilaydi. Olti guruhli bog'chada u beshtasining davomatiga
       tegishi kerak emas.

    2. **Sana** — tarbiyachi uchun oyna tor (sukut: bugun va kecha).
       O'tgan oyning davomatini jimgina o'zgartirish qayta hisobga
       (ADR-19) va hisobotga ta'sir qiladi. Direktor va egasi istalgan
       sanani o'zgartiradi, lekin SABAB bilan — u auditga yoziladi.

    `user` berilmagan bo'lsa (import, fon vazifasi) tekshiruv
    o'tkazilmaydi: u yerda odam yo'q va chegaraning ma'nosi ham yo'q.
    """
    if user is None:
        return

    from apps.children.scope import can_touch_group, is_group_restricted

    if not can_touch_group(user, group):
        raise BusinessRuleViolation(
            gettext("Bu guruh sizga biriktirilmagan — davomatni belgilay olmaysiz.")
        )

    if not is_group_restricted(user):
        # Direktor/egasi: istalgan sana, lekin eski kunga sabab bilan.
        window = teacher_edit_window(getattr(group, "branch", None))
        if (timezone.localdate() - attendance_date).days > window and not reason.strip():
            raise BusinessRuleViolation(
                gettext("Oʻtgan kun davomatini oʻzgartirish uchun sabab yozing.")
            )
        return

    window = teacher_edit_window(getattr(group, "branch", None))
    if (timezone.localdate() - attendance_date).days > window:
        raise BusinessRuleViolation(
            gettext(
                "Tarbiyachi faqat oxirgi {days} kun davomatini belgilaydi. "
                "Eski kun uchun direktorga murojaat qiling."
            ).format(days=window + 1)
        )
