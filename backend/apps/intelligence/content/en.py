"""Radix Intelligence texts — English (docs/07 §12)."""

from __future__ import annotations

from typing import Any

TITLES = {
    "payment_delay": (
        "Payments for {children_count} children are more than "
        "{overdue_days_threshold} days overdue"
    ),
    "attendance_drop": "Group attendance dropped {drop_points} points below its baseline",
}

RECOMMENDATIONS = {
    "payment_delay.review_debtors": "Review the debtors list and consider sending reminders.",
    "attendance_drop.ask_teacher": "Ask the group's teacher about the reason for the drop.",
}


def title(insight_type: str, evidence: dict[str, Any]) -> str:
    return TITLES[insight_type].format(**evidence)


def recommendation(key: str) -> str:
    return RECOMMENDATIONS[key]
