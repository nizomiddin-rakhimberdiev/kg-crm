"""
SMS uzunligi va bo'laklari (PLAN 3.3, 3.4; Q11).

Nega alohida modul: SMS narxi **bo'lak** bo'yicha hisoblanadi, belgi
bo'yicha emas, va bo'laklar soni alifboga bog'liq. 160 belgilik lotin
xabari bitta bo'lak, 70 belgilik kirill xabari ham bitta bo'lak —
ya'ni kirillga o'tish narxni ikki baravar oshiradi. Mudira buni
shablonni yozayotganda ko'rishi kerak, oy oxirida hisobdan emas.

Shu hisob **ikki joyda** kerak: shablon muharririda (jonli hisoblagich)
va tannarx baholashda. Shuning uchun u servisda emas, shu yerda.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "GSM7_SINGLE",
    "GSM7_MULTI",
    "UCS2_SINGLE",
    "UCS2_MULTI",
    "SmsLength",
    "sms_safe",
    "measure",
    "parts_for",
]

# GSM 03.38 asosiy jadvali. Bu yerda ataylab to'liq ro'yxat: "lotin
# harflarmi?" degan taxmin yetarli emas — `ʻ`, `–`, `«` kabi belgilar
# lotin matnida ham uchraydi va ular butun xabarni UCS-2 ga o'tkazadi.
GSM7_BASIC = (
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
)
# Bu belgilar GSM-7 da IKKI o'rin egallaydi (escape bilan).
GSM7_EXTENDED = "^{}\\[~]|€"

GSM7_SINGLE = 160
GSM7_MULTI = 153  # ko'p bo'lakli xabarda 7 belgi sarlavhaga ketadi
UCS2_SINGLE = 70
UCS2_MULTI = 67

#: Q11: o'zbek apostroflari SMS'da oddiy `'` ga almashtiriladi.
#:
#: `ʻ` va `ʼ` GSM-7 da YO'Q, ya'ni bitta shunday belgi 160 belgilik
#: xabarni 70 belgilik UCS-2 xabariga aylantiradi — narx ikki baravar,
#: matn esa kesilishi mumkin. "Toʻlov" va "To'lov" o'rtasidagi farq
#: ota-ona uchun sezilmaydi, hisobda esa sezilади.
APOSTROPHE_MAP = {
    "ʻ": "'",  # ʻ — o', g'
    "ʼ": "'",  # ʼ
    "‘": "'",
    "’": "'",
    "′": "'",
    "´": "'",
    "“": '"',
    "”": '"',
    "–": "-",
    "—": "-",
    "…": "...",
    " ": " ",
}


@dataclass(frozen=True)
class SmsLength:
    """Matnning o'lchami — muharrir shuni ko'rsatadi."""

    encoding: str  # "gsm7" | "ucs2"
    characters: int  # hisoblangan o'rinlar (escape belgilari 2 ga teng)
    parts: int
    limit: int  # shu bo'lakka sig'adigan belgilar soni


def sms_safe(text: str) -> str:
    """Yuborishdan oldin matnni tozalaydi (Q11)."""
    for source, target in APOSTROPHE_MAP.items():
        text = text.replace(source, target)
    return text


def _is_gsm7(text: str) -> bool:
    return all(char in GSM7_BASIC or char in GSM7_EXTENDED for char in text)


def measure(text: str) -> SmsLength:
    """Matnning kodlanishi, uzunligi va bo'laklari."""
    if _is_gsm7(text):
        length = sum(2 if char in GSM7_EXTENDED else 1 for char in text)
        single, multi, encoding = GSM7_SINGLE, GSM7_MULTI, "gsm7"
    else:
        # Emoji va boshqa BMP tashqarisidagi belgilar UCS-2 da ikki
        # o'rin egallaydi (surrogat juftlik).
        length = sum(2 if ord(char) > 0xFFFF else 1 for char in text)
        single, multi, encoding = UCS2_SINGLE, UCS2_MULTI, "ucs2"

    if length == 0:
        return SmsLength(encoding=encoding, characters=0, parts=0, limit=single)
    if length <= single:
        return SmsLength(encoding=encoding, characters=length, parts=1, limit=single)
    parts = -(-length // multi)  # yuqoriga yaxlitlash
    return SmsLength(encoding=encoding, characters=length, parts=parts, limit=multi)


def parts_for(text: str) -> int:
    """Shu matn necha SMS bo'lagi — narx hisobi uchun."""
    return measure(text).parts
