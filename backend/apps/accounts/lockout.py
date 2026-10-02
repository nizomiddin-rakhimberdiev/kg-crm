"""
Kirish urinishlarini cheklash (PLAN 5.3).

Nega tezlik chegarasining o'zi yetarli emas. `LoginThrottle` IP
bo'yicha 20/min beradi va u **jamoaviy** chegara: bog'chada hamma
bitta Wi-Fi ortida, shuning uchun uni pasaytirish birinchi kuni
"tizim buzuq" degan taassurot berardi. Lekin 20/min = soatda 1200
urinish, ya'ni bitta hisobga qarshi parol terish uchun ko'p.

Shuning uchun ikkinchi qatlam: **hisob bo'yicha** chegara.
Kalit `(email, IP)` emas, ALOHIDA ikkita hisoblagich:

* `email` — bitta hisobga qarshi terishni to'xtatadi, hujumchi IP'ni
  almashtirsa ham;
* `IP` — bitta manbadan ko'p hisobni sinab ko'rishni to'xtatadi
  (login "bu email bormi?" orakuliga aylanmasin).

Muvaffaqiyatli kirish hisoblagichni **nolga qaytaradi**: parolni
unutib uch marta xato terган xodim to'g'ri kirgach jazolanmasligi
kerak.

**Blok vaqtinchalik va qisqa** (15 daqiqa). Abadiy blok qo'lda
yechishni talab qiladi — ya'ni bog'chaning ishi egasining telefoniga
bog'liq bo'lib qoladi. 15 daqiqa avtomatik hujumni foydasiz qiladi va
haqiqiy xodimni bir choy ichimlik vaqtida qaytaradi.

Hisoblagich **Redis'da** (`cache`): u o'z-o'zidan eskiradi va bazaga
yozuv qo'shmaydi. Redis yiqilsa chegara ishlamaydi — bu ongli
tanlov: kirishni butunlay to'xtatgandan ko'ra, chegarasiz ishlash
kamroq zarar (audit baribir yozib turadi).
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.cache import cache

__all__ = ["MAX_ATTEMPTS", "BLOCK_SECONDS", "is_locked", "record_failure", "reset", "retry_after"]

#: Necha xato urinishdan keyin blok.
MAX_ATTEMPTS = int(getattr(settings, "LOGIN_MAX_ATTEMPTS", 10))

#: Blok qancha davom etadi (soniya).
BLOCK_SECONDS = int(getattr(settings, "LOGIN_BLOCK_SECONDS", 15 * 60))

#: Hisoblagichning yashash muddati — blok bilan bir xil: oynada
#: to'plangan urinishlar oyna o'tgach o'z-o'zidan yo'qoladi.
_WINDOW = BLOCK_SECONDS


def _keys(email: str, ip: str) -> list[str]:
    keys = []
    if email:
        keys.append(f"login:fail:email:{email.strip().lower()}")
    if ip:
        keys.append(f"login:fail:ip:{ip}")
    return keys


def is_locked(*, email: str = "", ip: str = "") -> bool:
    """Shu email yoki shu IP hozir bloklanganmi."""
    return any(int(cache.get(key) or 0) >= MAX_ATTEMPTS for key in _keys(email, ip))


def retry_after(*, email: str = "", ip: str = "") -> int:
    """Blok tugashiga necha soniya qolgani — javobda aytiladi."""
    longest = 0
    for key in _keys(email, ip):
        if int(cache.get(key) or 0) >= MAX_ATTEMPTS:
            ttl = cache.ttl(key) if hasattr(cache, "ttl") else None
            longest = max(longest, int(ttl) if ttl else BLOCK_SECONDS)
    return longest or BLOCK_SECONDS


def record_failure(*, email: str = "", ip: str = "") -> int:
    """
    Xato urinishni sanaydi va yangi qiymatni qaytaradi.

    `cache.add` + `incr`: `incr` mavjud bo'lmagan kalitda istisno
    ko'taradi, `add` esa faqat kalit yo'q bo'lsa yozadi — ya'ni ikki
    parallel urinish bitta hisoblagichni buzmaydi.
    """
    highest = 0
    for key in _keys(email, ip):
        cache.add(key, 0, _WINDOW)
        try:
            value = int(cache.incr(key))
        except ValueError:
            # Kalit `add` dan keyin, `incr` dan oldin eskirgan.
            cache.set(key, 1, _WINDOW)
            value = 1
        highest = max(highest, value)
    return highest


def reset(*, email: str = "", ip: str = "") -> None:
    """Muvaffaqiyatli kirish — hisoblagich nolga."""
    for key in _keys(email, ip):
        cache.delete(key)


def state(*, email: str = "", ip: str = "") -> dict[str, Any]:
    """Diagnostika uchun (buyruq va testlar)."""
    return {key: int(cache.get(key) or 0) for key in _keys(email, ip)}
