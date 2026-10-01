"""
Qidiruv kaliti — apostrof va alifbo farqini yo'q qiladi (Q11, PLAN 2.7).

Bog'chada bitta bola uch xil yoziladi: "Ulug'bek", "Ulugʻbek",
"Улугбек". Mudira qaysi birini yozsa ham bolani topishi kerak — aks
holda u "bu bola tizimda yo'q" deb xulosa qiladi va ikkinchi marta
kiritadi. Natijada bitta bola ikkita yozuvda, ikkita balansda.

Yechim: har bir yozuvda **qidiruv kaliti** saqlanadi — faqat lotin
harflari va raqamlardan iborat, apostrofsiz, kichik harfda. So'rov ham
o'sha funksiyadan o'tadi, ya'ni ikkalasi bir xil shaklga keladi.

Nega alohida ustun, `ILIKE` emas: Postgres uchun "Ulug'bek" va
"Улугбек" butunlay boshqa satrlar, va ularni so'rov paytida
solishtirish uchun har qatorda `translate()` chaqirish kerak bo'lardi —
ya'ni indeks ishlamay qolardi.
"""

from __future__ import annotations

import re
import unicodedata

__all__ = ["search_key", "APOSTROPHES"]

#: Bir xil hisoblanadigan apostroflar (Q11).
#:
#: O'zbek lotinida ikkitasi ma'noli (U+02BB oʻ/gʻ uchun, U+02BC tutuq),
#: qolganlari esa klaviatura va nusxa-ko'chirishdan keladi. Qidiruvda
#: ularning hammasi ayni bir narsa.
APOSTROPHES = "'‘’ʻʼ`´′"

#: Kirill → lotin. O'zbek kirill alifbosi uchun; ruscha harflar ham
#: tushadi, chunki ismlar ko'pincha ruscha hujjatdan ko'chiriladi.
_CYRILLIC = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "ғ": "g",
    "д": "d",
    "е": "e",
    "ё": "yo",
    "ж": "j",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "қ": "q",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ў": "o",
    "ф": "f",
    "х": "h",
    "ҳ": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sh",
    "ъ": "",
    "ы": "i",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def search_key(value: str) -> str:
    """
    Matnni qidiruv kalitiga aylantiradi.

    "Ulug'bek", "Ulugʻbek", "Улугбек", "ULUG`BEK" → `"ulugbek"`.

    Telefon raqami ham shu yerdan o'tadi: "+998 90 123 45 67" →
    `"998901234567"`, ya'ni mudira raqamni qanday yozsa ham topadi.
    """
    if not value:
        return ""

    text = unicodedata.normalize("NFKC", value).lower()
    # Apostroflar BUTUNLAY olib tashlanadi, bo'sh joyga ham
    # almashtirilmaydi: "o'g'li" va "ogli" bir xil kalit berishi kerak.
    for mark in APOSTROPHES:
        text = text.replace(mark, "")
    text = "".join(_CYRILLIC.get(char, char) for char in text)
    # Qolgan hamma narsa — harf va raqamdan tashqari — tushib qoladi.
    text = re.sub(r"[^a-z0-9]+", "", text)
    # `x` va `h` birlashtiriladi: "Shahzoda" va "Shaxzoda", "Baxtiyor"
    # va "Bahtiyor" — bitta ism, ikki xil yozilishi. Kirill х ham,
    # ҳ ham shu yerga tushadi, ya'ni uch alifbo bir kalitga keladi.
    return text.replace("x", "h")
