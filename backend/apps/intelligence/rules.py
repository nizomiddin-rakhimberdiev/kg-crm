"""
Qoidalar — SOF funksiyalar (docs/07 §4).

Bazaga, so'rovga, vaqtga bog'liq emas: oddiy qiymatlarni oladi, `InsightDraft`
yoki `None` qaytaradi. Shuning uchun har bir chegara qiymatini sinash
arzon — va aynan chegaralar (14/15/16 kun, 9.9/10/10.1 punkt) eng xavfli
joylar.

Til qoidasi (docs/07 §7) shu yerda boshlanadi: draft'da BASHORAT yo'q,
faqat hisoblangan fakt — `children_count`, `max_days_overdue`,
`drop_points`. Matn keyin content qatlamida tuziladi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from apps.intelligence.thresholds import AttendanceDropThresholds, PaymentDelayThresholds

DEFAULT_PAYMENT_DELAY = PaymentDelayThresholds()
DEFAULT_ATTENDANCE_DROP = AttendanceDropThresholds()

__all__ = [
    "InsightDraft",
    "OverdueChild",
    "GroupAttendance",
    "payment_delay",
    "attendance_drop",
]

EVIDENCE_VERSION = 1
EVIDENCE_ROW_CAP = 50


@dataclass(frozen=True)
class InsightDraft:
    """Servis qatlamiga uzatiladigan, bazaga hali yozilmagan insight."""

    type: str
    severity: str
    subject_type: str
    subject_id: UUID
    evidence: dict[str, Any]
    recommendation_key: str
    deep_link: str
    evidence_version: int = EVIDENCE_VERSION


# --- I-1 · payment_delay ---


@dataclass(frozen=True)
class OverdueChild:
    child_id: UUID
    group_id: UUID | None
    overdue_amount: Decimal
    days_overdue: int  # eng eski to'lanmagan faktura bo'yicha
    invoices: int


def payment_delay(
    *,
    branch_id: UUID,
    as_of: date,
    active_children: int,
    overdue: list[OverdueChild],
    thresholds: PaymentDelayThresholds = DEFAULT_PAYMENT_DELAY,
) -> InsightDraft | None:
    """
    Hard rule: `due_date < as_of - overdue_days` bo'lgan ochiq fakturalar,
    bola bo'yicha guruhlangan. `overdue` ro'yxati ALLAQACHON shu chegaraga
    filtrlangan bo'lishi kutiladi — qoida buni qayta tekshiradi, chunki
    chegara bu yerda, selectorda emas.
    """
    rows = [row for row in overdue if row.days_overdue > thresholds.overdue_days]
    if not rows:
        return None

    rows.sort(key=lambda row: (-row.days_overdue, -row.overdue_amount))
    count = len(rows)
    max_days = rows[0].days_overdue
    critical_by_share = max(
        thresholds.critical_min_subjects, int(active_children * thresholds.critical_share)
    )
    severity = (
        "critical"
        if max_days >= thresholds.critical_days or count >= critical_by_share
        else "warning"
    )

    return InsightDraft(
        type="payment_delay",
        severity=severity,
        subject_type="branch",
        subject_id=branch_id,
        evidence={
            "as_of": as_of.isoformat(),
            "overdue_days_threshold": thresholds.overdue_days,
            "children_count": count,
            "active_children": active_children,
            # "Nega jiddiy?" — UI chegaralarni takrorlamasin, raqam shu yerda.
            "critical_days_threshold": thresholds.critical_days,
            "critical_children_threshold": critical_by_share,
            "total_overdue": str(sum((row.overdue_amount for row in rows), Decimal("0"))),
            "average_days_overdue": round(sum(row.days_overdue for row in rows) / count),
            "max_days_overdue": max_days,
            "children": [
                {
                    "child_id": str(row.child_id),
                    "group_id": str(row.group_id) if row.group_id else None,
                    "overdue_amount": str(row.overdue_amount),
                    "days_overdue": row.days_overdue,
                    "invoices": row.invoices,
                }
                for row in rows[:EVIDENCE_ROW_CAP]
            ],
        },
        recommendation_key="payment_delay.review_debtors",
        deep_link=f"/debtors?overdue_days={thresholds.overdue_days}",
    )


# --- I-2 · attendance_drop ---


@dataclass(frozen=True)
class GroupAttendance:
    group_id: UUID
    active_children: int
    recent_days: int  # yozuvli ish kunlari soni
    recent_present: int
    recent_absent: int
    recent_excused: int
    baseline_days: int
    baseline_present: int
    baseline_absent: int
    baseline_excused: int
    extra: dict[str, Any] = field(default_factory=dict)


def _rate(present: int, absent: int, excused: int) -> float | None:
    total = present + absent + excused
    return None if total == 0 else round(present * 100.0 / total, 1)


def attendance_drop(
    *,
    as_of: date,
    group: GroupAttendance,
    thresholds: AttendanceDropThresholds = DEFAULT_ATTENDANCE_DROP,
) -> InsightDraft | None:
    """
    Pattern: so'nggi oynadagi davomat o'z bazasiga nisbatan sezilarli
    pasaygan. Baza yetarli bo'lmasa — sukut ("o'rganmoqda"), taxmin emas.
    Yozuvsiz kunlar "yo'q" deb HISOBLANMAYDI (docs/07 §4).
    """
    if group.active_children < thresholds.min_group_size:
        return None
    if group.baseline_days < thresholds.min_baseline_days:
        return None

    recent = _rate(group.recent_present, group.recent_absent, group.recent_excused)
    baseline = _rate(group.baseline_present, group.baseline_absent, group.baseline_excused)
    if recent is None or baseline is None:
        return None

    drop = round(baseline - recent, 1)
    if drop < thresholds.drop_warning:
        return None

    return InsightDraft(
        type="attendance_drop",
        severity="critical" if drop >= thresholds.drop_critical else "warning",
        subject_type="group",
        subject_id=group.group_id,
        evidence={
            "as_of": as_of.isoformat(),
            "group_id": str(group.group_id),
            "active_children": group.active_children,
            "recent": {
                "days": group.recent_days,
                "rate": recent,
                "present": group.recent_present,
                "absent": group.recent_absent,
                "excused": group.recent_excused,
            },
            "baseline": {"days": group.baseline_days, "rate": baseline},
            "drop_points": drop,
        },
        recommendation_key="attendance_drop.ask_teacher",
        deep_link=f"/attendance?group={group.group_id}&range={thresholds.recent_days}d",
    )
