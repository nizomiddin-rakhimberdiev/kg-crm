"""
O'zbekiston telefon raqami — yagona normalizatsiya (Q7, PLAN 2.4).

Auditda vasiy telefoni sifatida "12345", tizim hisobiniki sifatida "45"
qabul qilingan edi. Bu shunchaki chiroyli bo'lmagan ma'lumot emas:
noto'g'ri raqam SMS'ni **jimgina** yo'qotadi — bildirishnoma
"yuborildi" bo'lib turadi, ota-ona esa hech narsa olmaydi va buni
hech kim sezmaydi.

Saqlash shakli bitta: `+998XXXXXXXXX` (E.164). Odam qanday yozsa ham —
"90 123 45 67", "(90) 123-45-67", "998901234567" — bazada bitta
ko'rinish bo'ladi, aks holda qidiruv va dublikat tekshiruvi
ishlamasdi.

Validatsiya **ikki qatlamda**: bu modul (format) va `serializers`
(maydon). Model darajasida `CHECK` qo'yilmadi — mavjud tenantlarda
allaqachon noto'g'ri raqamlar bor va migratsiya ularni o'chirib
yuborardi. Ular uchun `report_bad_phones` buyrug'i bor: u faqat
HISOBOT beradi, hech narsani o'zgartirmaydi.
"""

from __future__ import annotations

import re

from django.utils.translation import gettext

__all__ = ["normalise_phone", "is_valid_phone", "PhoneFormatError", "PHONE_HINT"]

#: Operator kodi + raqam: 9 ta raqam, mamlakat kodisiz.
_NATIONAL_LENGTH = 9
_COUNTRY = "998"
_FULL_LENGTH = len(_COUNTRY) + _NATIONAL_LENGTH

PHONE_HINT = "+998 XX XXX XX XX"


class PhoneFormatError(ValueError):
    """Raqam O'zbekiston formatiga mos emas."""


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def normalise_phone(value: str) -> str:
    """
    Har qanday yozilishni `+998XXXXXXXXX` ga keltiradi.

    Bo'sh qiymat bo'sh qaytadi: telefon hamma joyda majburiy emas
    (import qilingan bola vasiysiz bo'lishi mumkin), lekin BERILGAN
    bo'lsa — to'g'ri bo'lishi shart.
    """
    raw = (value or "").strip()
    if not raw:
        return ""

    digits = _digits(raw)
    if len(digits) == _NATIONAL_LENGTH:
        digits = _COUNTRY + digits
    # "8 90 123 45 67" — eski odat, mamlakat kodi o'rniga shaharlararo 8.
    elif len(digits) == _NATIONAL_LENGTH + 1 and digits.startswith("8"):
        digits = _COUNTRY + digits[1:]

    if len(digits) != _FULL_LENGTH or not digits.startswith(_COUNTRY):
        raise PhoneFormatError(
            gettext("Telefon raqamini {hint} formatida kiriting.").format(hint=PHONE_HINT)
        )
    return f"+{digits}"


def is_valid_phone(value: str) -> bool:
    """Raqamni o'zgartirmasdan tekshiradi — hisobot buyruqlari uchun."""
    try:
        normalise_phone(value)
    except PhoneFormatError:
        return False
    return True
