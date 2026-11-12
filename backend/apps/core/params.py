"""
So'rov parametrlarini xavfsiz o'qish.

Nega alohida modul: filtr qiymati FOYDALANUVCHIDAN keladi va
`filter(id="abc")` yoki `Decimal("x")` ichkarida `500` beradi. Qolgan
hamma endpoint buzuq qiymatga tushunarli `422` yoki `404` qaytaradi,
va bitta endpointning `500` bilan yiqilishi skanerlaydigan odamga
aynan shu yerda kutilmagan narsa borligini aytib qo'yadi
(docs/04 §2).
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from django.utils.translation import gettext

from apps.core.exceptions import BusinessRuleViolation

__all__ = ["parse_decimal", "parse_int", "parse_uuid", "parse_bool", "require_reason"]

REASON_MIN = 5


def parse_decimal(raw: Any, *, field: str = "") -> Decimal | None:
    """Bo'sh bo'lsa `None`, buzuq bo'lsa tushunarli xato."""
    if raw in (None, "", []):
        return None
    try:
        return Decimal(str(raw))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise BusinessRuleViolation(
            gettext("{field}: raqam notoʻgʻri.").format(field=field or gettext("Qiymat"))
        ) from exc


def parse_int(raw: Any, *, field: str = "") -> int | None:
    if raw in (None, "", []):
        return None
    try:
        return int(str(raw))
    except (ValueError, TypeError) as exc:
        raise BusinessRuleViolation(
            gettext("{field}: raqam notoʻgʻri.").format(field=field or gettext("Qiymat"))
        ) from exc


def parse_date(raw: Any, *, field: str = "") -> date | None:
    """`yyyy-mm-dd` → `date`. Boʻsh boʻlsa `None`, buzuq boʻlsa tushunarli xato."""
    if raw in (None, "", []):
        return None
    try:
        return date.fromisoformat(str(raw))
    except (ValueError, TypeError) as exc:
        raise BusinessRuleViolation(
            gettext("{field}: sana notoʻgʻri.").format(field=field or gettext("Sana"))
        ) from exc


def parse_uuid(raw: Any) -> str | None:
    """
    Buzuq UUID ochiq xato beradi — jimgina tashlab yuborilmaydi.

    Nega ochiq: buzuq filtrni `None` qilib tashlash FILTRNI OLIB
    TASHLAYDI. Ommaviy eslatmada bu "shu guruhga yuboraman" degan
    amalni "hammaga yuboraman" ga aylantirardi — va mudira buni SMS
    ketgandan keyin bilardi.
    """
    if raw in (None, "", []):
        return None
    try:
        return str(uuid.UUID(str(raw)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise BusinessRuleViolation(gettext("Notoʻgʻri identifikator.")) from exc


def parse_bool(raw: Any) -> bool:
    return str(raw).lower() in ("true", "1", "yes", "ha")


def require_reason(raw: Any, *, field: str = "reason") -> str:
    """
    Pul yoki hujjatni bekor qilish sababi — kamida `REASON_MIN` belgi.

    Forma xatosi (`400`), biznes qoidasi emas: sabab — kiritilmagan
    maydon. Bir xil chegara hamma joyda, chunki "xa" sabab emas.
    """
    from rest_framework.exceptions import ValidationError

    reason = str(raw or "").strip()
    if len(reason) < REASON_MIN:
        raise ValidationError(
            {field: gettext("Sababini yozing — kamida {n} ta belgi.").format(n=REASON_MIN)}
        )
    return reason
