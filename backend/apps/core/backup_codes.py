"""
Zaxira kodlari — 2FA ning yagona qulflanmasligi kafolati (PLAN 5.4).

Telefon sinadi, o'g'irlanadi va almashtiriladi. Majburiy ikkinchi omil
shu holatda hisobni butunlay yopadi, va "vendorga yozing" degan yechim
bu yerda ishlamaydi: vendor mijozning ma'lumotiga yoza olmaydi
(ADR-10, qo'llab-quvvatlash sessiyasi faqat o'qish uchun). Shuning
uchun zaxira kodlari — qo'shimcha qulaylik emas, 2FA ni yoqishning
SHARTI.

Uch qaror:

* **Kod bir martalik.** Ishlatilgan kod ro'yxatdan O'CHIRILADI: qog'ozga
  yozilgan kod yo'qolishi mumkin, va "bir marta ishlatilgan, lekin
  hamon yaroqli" kod eng yomon holat.
* **Faqat xesh saqlanadi** (SHA-256). Kodlar yuqori entropiyali
  (40 bit), ya'ni parol xeshlash (PBKDF2) kerak emas — u faqat
  taxmin qilinadigan sirlar uchun zarur. Lug'at hujumi mumkin
  bo'lmagan qiymatni sekin xeshlash — o'nta kodni tekshirishni uch
  soniyaga cho'zardi, foyda keltirmay.
* **Guruhlangan ko'rinish** (`a1b2-c3d4`): odam uni qog'ozga ko'chiradi
  va chiziqcha xatoni kamaytiradi. Tekshirishda chiziqcha ham, katta
  harf ham, bo'sh joy ham hisobga olinmaydi.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

__all__ = ["CODE_COUNT", "generate", "hash_code", "consume"]

#: Nechta kod beriladi. O'nta — bir necha yil davomida yetadigan,
#: lekin qog'ozga sig'adigan son.
CODE_COUNT = 10

#: Chalkashadigan belgilar yo'q: `0/O`, `1/l/I` olib tashlangan.
_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
_LENGTH = 8


def _one() -> str:
    raw = "".join(secrets.choice(_ALPHABET) for _ in range(_LENGTH))
    return f"{raw[:4]}-{raw[4:]}"


def normalize(code: str) -> str:
    return code.strip().lower().replace("-", "").replace(" ", "")


def hash_code(code: str) -> str:
    return hashlib.sha256(normalize(code).encode()).hexdigest()


def generate(count: int = CODE_COUNT) -> tuple[list[str], list[str]]:
    """Yangi kodlar: `(ko'rsatiladigan, saqlanadigan xeshlar)`."""
    codes = [_one() for _ in range(count)]
    return codes, [hash_code(code) for code in codes]


def consume(hashes: list[str], code: str) -> list[str] | None:
    """
    Kod ro'yxatda bo'lsa — ro'yxatning QOLGAN qismini qaytaradi.

    `None` — kod topilmadi. Taqqoslash `compare_digest` bilan: xeshlar
    sir emas, lekin bu yo'l autentifikatsiyada va u yerda doimiy
    vaqtli taqqoslash odat bo'lishi kerak.
    """
    if not code.strip():
        return None
    target = hash_code(code)
    for index, stored in enumerate(hashes):
        if hmac.compare_digest(str(stored), target):
            return [*hashes[:index], *hashes[index + 1 :]]
    return None
