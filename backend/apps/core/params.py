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
from decimal import Decimal, InvalidOperation
from typing import Any

from django.utils.translation import gettext

from apps.core.exceptions import BusinessRuleViolation

__all__ = ["parse_decimal", "parse_int", "parse_uuid", "parse_bool"]


def parse_decimal(raw: Any, *, field: str = "") -> Decimal | None:
    """Bo'sh bo'lsa `None`, buzuq bo'lsa tushunarli xato."""
    if raw in (None, "", []):
        return None
    try:
        return Decimal(str(raw))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise BusinessRuleViolation(
            gettext("{field}: raqam noto'g'ri.").format(field=field or gettext("Qiymat"))
        ) from exc


def parse_int(raw: Any, *, field: str = "") -> int | None:
    if raw in (None, "", []):
        return None
    try:
        return int(str(raw))
    except (ValueError, TypeError) as exc:
        raise BusinessRuleViolation(
            gettext("{field}: raqam noto'g'ri.").format(field=field or gettext("Qiymat"))
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
        raise BusinessRuleViolation(gettext("Noto'g'ri identifikator.")) from exc


def parse_bool(raw: Any) -> bool:
    return str(raw).lower() in ("true", "1", "yes", "ha")
