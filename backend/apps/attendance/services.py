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
    # What the register said before — the absence alert goes only on a
    # change TO absent, never on a re-save of the same answer (P6-5).
    before = dict(
        AttendanceRecord.objects.filter(attendance_date=attendance_date, group=group).values_list(
            "child_id", "status"
        )
    )
    newly_absent: list[Any] = []

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
        if status == AttendanceStatus.ABSENT and before.get(child_id) != AttendanceStatus.ABSENT:
            newly_absent.append(child_id)

    if newly_absent:
        from django.db import transaction

        from apps.notifications.services import notify_absence

        transaction.on_commit(
            lambda: notify_absence(child_ids=newly_absent, on_date=attendance_date)
        )

    # Oylik davomat foizi dashboardda — kesh eskirdi.
    from apps.reports.services import invalidate_dashboard_on_commit

    invalidate_dashboard_on_commit(organization_id=organization.id)
    return saved


def day_summary(*, user: Any, attendance_date: date) -> dict[str, Any]:
    """
    Bir kunning BUTUN bog'cha bo'yicha yig'masi (mijoz so'rovi, 2026-10-23).

    Davomat ekranida "Keldi / Sababli / Kelmagan" faqat tanlangan
    guruhning pastida, kichkina yozuvda turardi. Mudiraning birinchi
    savoli esa boshqa: "bugun nechta bola keldi?" — ya'ni butun
    bog'cha bo'yicha, va u ekranning TEPASIDA bo'lishi kerak.

    **"Hammasi" — foydalanuvchining o'z ko'lami** (ADR-21): guruhga
    biriktirilgan tarbiyachi faqat o'z guruhlarini ko'radi, ya'ni
    uning "hammasi" — o'sha guruhlar. Shuning uchun guruhlar ro'yxati
    `restrict_groups` dan o'tadi.

    **Belgilanmagan — "kelmagan" EMAS** (ADR-19): ikkisi boshqa narsa,
    va aynan shu farq ekranni ishonchli qiladi.
    """
    from apps.children.scope import restrict_groups

    groups = list(restrict_groups(Group.objects.all(), user).order_by("name"))
    if not groups:
        return {
            "date": attendance_date.isoformat(),
            "total": 0,
            "marked": 0,
            "present": 0,
            "absent": 0,
            "excused": 0,
            "unmarked": 0,
            "groups": [],
        }

    # Bolalar soni — guruh bo'yicha, BITTA so'rovda.
    roster: dict[Any, int] = dict(
        Child.objects.filter(
            enrollments__group__in=groups,
            enrollments__status=EnrollmentState.ACTIVE,
            enrollments__end_date__isnull=True,
            is_active=True,
        )
        .values_list("enrollments__group_id")
        .annotate(total=Count("id", distinct=True))
    )

    # Belgilangan yozuvlar — guruh va holat bo'yicha, yana bitta so'rov.
    counts: dict[tuple[Any, str], int] = {
        (row["group_id"], row["status"]): row["n"]
        for row in AttendanceRecord.objects.filter(
            group__in=groups, attendance_date=attendance_date
        )
        .values("group_id", "status")
        .annotate(n=Count("id"))
    }

    rows: list[dict[str, Any]] = []
    for group in groups:
        total = roster.get(group.id, 0)
        present = counts.get((group.id, AttendanceStatus.PRESENT), 0)
        absent = counts.get((group.id, AttendanceStatus.ABSENT), 0)
        excused = counts.get((group.id, AttendanceStatus.EXCUSED), 0)
        marked = present + absent + excused
        rows.append(
            {
                "id": str(group.id),
                "name": group.name,
                "total": total,
                "marked": marked,
                "present": present,
                "absent": absent,
                "excused": excused,
                "unmarked": max(total - marked, 0),
            }
        )

    return {
        "date": attendance_date.isoformat(),
        "total": sum(row["total"] for row in rows),
        "marked": sum(row["marked"] for row in rows),
        "present": sum(row["present"] for row in rows),
        "absent": sum(row["absent"] for row in rows),
        "excused": sum(row["excused"] for row in rows),
        "unmarked": sum(row["unmarked"] for row in rows),
        "groups": rows,
    }


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
