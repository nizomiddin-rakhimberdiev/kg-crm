"""
Umumiy serializer maydonlari.

`TenantPrimaryKeyRelatedField` `core/fields.py` da qoladi — u tenant
chegarasiga tegishli va alohida o'qiladi.
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.core.phone import PhoneFormatError, normalise_phone

__all__ = ["PhoneField"]


class PhoneField(serializers.CharField):
    """
    O'zbekiston telefon raqami — saqlashda normalizatsiya qilinadi (Q7).

    Har bir serializerda `validate_phone` yozish o'rniga shu maydon:
    takrorlangan tekshiruv ertami-kechmi bir joyda unutilardi, va
    auditda aynan shunday bo'lgan — lid formasida tekshiruv bor edi,
    vasiy va xodimda esa yo'q.
    """

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("max_length", 20)
        kwargs.setdefault("trim_whitespace", True)
        super().__init__(**kwargs)

    def to_internal_value(self, data: Any) -> str:
        value = super().to_internal_value(data)
        try:
            return normalise_phone(value)
        except PhoneFormatError as exc:
            raise serializers.ValidationError(str(exc)) from exc
