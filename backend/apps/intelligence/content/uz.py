"""
Radix Intelligence matnlari — O'zbekcha (docs/07 §12). RU va EN nusxalari ru.py, en.py da.

Faqat buyruq chiqishi va (V2) bildirishnoma uchun. Dashboard matni
frontend'ning o'z content qatlamida — API gap emas, kalit+evidence beradi.
Til qoidasi: FAKT, bashorat emas ("kechikmoqda", "to'lamaydi" emas).
"""

from __future__ import annotations

from typing import Any

TITLES = {
    "payment_delay": (
        "{children_count} ta bola bo‘yicha to‘lov {overdue_days_threshold} kundan ortiq kechikmoqda"
    ),
    "attendance_drop": "Guruhda davomat o‘z bazasiga nisbatan {drop_points} punktga pasaydi",
}

RECOMMENDATIONS = {
    "payment_delay.review_debtors": (
        "Qarzdorlar ro‘yxatini ko‘rib, eslatma yuborishni ko‘rib chiqing."
    ),
    "attendance_drop.ask_teacher": "Guruh tarbiyachisi bilan pasayish sababini aniqlang.",
}


def title(insight_type: str, evidence: dict[str, Any]) -> str:
    return TITLES[insight_type].format(**evidence)


def recommendation(key: str) -> str:
    return RECOMMENDATIONS[key]
