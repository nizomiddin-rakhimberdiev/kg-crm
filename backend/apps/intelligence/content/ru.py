"""Radix Intelligence matnlari — Ruscha (docs/07 §12)."""

from __future__ import annotations

from typing import Any

TITLES = {
    "payment_delay": (
        "По {children_count} детям оплата задерживается более {overdue_days_threshold} дней"
    ),
    "attendance_drop": (
        "Посещаемость группы снизилась на {drop_points} п.п. относительно своей нормы"
    ),
}

RECOMMENDATIONS = {
    "payment_delay.review_debtors": (
        "Просмотрите список должников и рассмотрите отправку напоминания."
    ),
    "attendance_drop.ask_teacher": "Уточните причину снижения у воспитателя группы.",
}


def title(insight_type: str, evidence: dict[str, Any]) -> str:
    return TITLES[insight_type].format(**evidence)


def recommendation(key: str) -> str:
    return RECOMMENDATIONS[key]
