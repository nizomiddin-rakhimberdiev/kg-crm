"""
Soliq rejimi presetlari (Bosqich 13.8, brif §9).

Preset — bir bosishda bir nechta sozlamani yozadigan TAYYOR QIYMATLAR, xolos:
keyin har birini alohida o'zgartirish mumkin va hammasi "buxgalter
tasdiqlashi kerak" degan belgi bilan ko'rsatiladi. Huquqiy maslahat emas.

* **PQ-403** — nodavlat maktabgacha ta'lim tashkiloti: 2030-yil 1-yanvargacha
  ijtimoiy soliqdan tashqari barcha soliq va yig'imlardan ozod. Xodim
  oyligidan JShDS 12 % va INPS 0,1 % baribir ushlanadi.
* **Umumiy rejim** — o'sha stavkalar; foyda solig'i bu tizimda hisoblanmaydi.
* **Aylanmadan olinadigan soliq** — daromaddan `tax.turnover_percent`.

Ijtimoiy soliq 12 %; PF-19 (2026) bo'yicha talablarga mos yangi bog'chalar 1
yoki 5 % ni tanlaydi — `payroll.social_tax_rate` ni qo'lda o'zgartirib.
"""

from __future__ import annotations

from typing import Any

from django.utils.translation import gettext, gettext_lazy

from apps.core.exceptions import BusinessRuleViolation

__all__ = ["PRESETS", "apply_preset", "presets"]

_PAYROLL = {
    "payroll.income_tax_rate": 12,
    "payroll.pension_rate": 0.1,
    "payroll.social_tax_rate": 12,
    "tax.dividend_percent": 5,
}

PRESETS: dict[str, tuple[Any, dict[str, Any]]] = {
    "pq403": (
        gettext_lazy("Nodavlat MTT imtiyozi (PQ-403)"),
        {**_PAYROLL, "tax.regime": "pq403", "tax.turnover_percent": 0},
    ),
    "general": (
        gettext_lazy("Umumiy rejim"),
        {**_PAYROLL, "tax.regime": "general", "tax.turnover_percent": 0},
    ),
    "turnover": (
        gettext_lazy("Aylanmadan olinadigan soliq"),
        {**_PAYROLL, "tax.regime": "turnover", "tax.turnover_percent": 4},
    ),
}


def presets() -> dict[str, Any]:
    """
    Rejimlar roʻyxati va HOZIR bazada turgan qiymatlar.

    `current_values` auditdan keyin qoʻshildi (2026-10-30): ekran
    presetning qiymatlarini koʻrsatardi va bogʻcha "12 %" ni oʻqib,
    soliq ushlanyapti deb oʻylardi — bazada esa 0 turardi va oylikda
    hech narsa hisoblanmasdi. Ekran bazadagi haqiqatni koʻrsatishi
    kerak, presetniki esa taklif boʻlib qolishi kerak.
    """
    from apps.settings_app.services import get_setting

    keys = sorted({key for _title, values in PRESETS.values() for key in values})
    return {
        "current": get_setting(key="tax.regime"),
        "note": gettext("Qiymatlar — boshlangʻich; buxgalter tasdiqlashi kerak."),
        "current_values": {key: get_setting(key=key) for key in keys},
        "presets": [
            {"id": key, "title": str(title), "values": values}
            for key, (title, values) in PRESETS.items()
        ],
    }


def apply_preset(*, organization: Any, preset: str) -> dict[str, Any]:
    from apps.settings_app.services import set_setting

    if preset not in PRESETS:
        raise BusinessRuleViolation(
            gettext("Bunday soliq rejimi yoʻq: {preset}").format(preset=preset)
        )
    values = PRESETS[preset][1]
    for key, value in values.items():
        set_setting(organization=organization, key=key, value=value)
    return values
