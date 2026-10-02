"""
Refresh token — httpOnly cookie'da (PLAN 5.1).

Avval u `localStorage` da yashardi. Bu ongli murosa edi va uning
narxi aniq: **XSS bilan o'g'irlanadi.** Bitta zararli skript (yuklangan
rasm emas — masalan buzilgan npm paketi yoki reklama kodi) refresh
tokenni o'qib, uni o'z serveriga yuborishi mumkin, va u yetti kun
ishlaydi. `httpOnly` cookie'ni JavaScript UMUMAN o'qiy olmaydi.

Uchta bayroq va ularning sababi:

* **`HttpOnly`** — XSS tokenni o'qiy olmaydi (butun o'zgarishning
  maqsadi);
* **`Secure`** — faqat HTTPS orqali ketadi. Lokal ishlab chiqishda
  (`http://localhost`) brauzer `Secure` cookie'ni YUBORMAYDI, shuning
  uchun u `DEBUG` da o'chiriladi;
* **`SameSite=Strict`** — begona saytdan kelgan so'rovga cookie
  QO'SHILMAYDI. Bu CSRF'ning asosiy to'sig'i: `Lax` bo'lsa yuqori
  darajadagi navigatsiyada cookie ketardi, `Strict` esa hech qanday
  cross-site so'rovga qo'shilmaydi.

**Yo'l cheklangan** (`/api/v1/auth`): cookie faqat auth endpointlariga
ketadi. Qolgan har bir so'rovda uni yuborish ma'nosiz trafik va
ortiqcha oshkor qilish bo'lardi.

**CSRF — ikkinchi qatlam.** `SameSite=Strict` ning o'zi deyarli
yetarli, lekin u brauzerga ishonadi. Shuning uchun cookie bilan
kelgan yangilash so'rovi `X-CSRFToken` sarlavhasini ham talab
qiladi va u `csrftoken` cookie'siga mos bo'lishi kerak (double
submit). Begona sayt bizning cookie'imizni O'QIY olmaydi, ya'ni
sarlavhani to'g'ri to'ldira olmaydi.
"""

from __future__ import annotations

import secrets
from typing import Any

from django.conf import settings

__all__ = [
    "REFRESH_COOKIE",
    "CSRF_COOKIE",
    "CSRF_HEADER",
    "set_refresh_cookie",
    "clear_refresh_cookie",
    "read_refresh_cookie",
    "csrf_ok",
]

REFRESH_COOKIE = "radix_refresh"
CSRF_COOKIE = "radix_csrf"
CSRF_HEADER = "X-CSRFToken"

#: Cookie faqat auth endpointlariga ketadi.
COOKIE_PATH = "/api/v1/auth"


def _secure() -> bool:
    """
    Lokal `http://localhost` da `Secure` cookie YUBORILMAYDI.

    Shuning uchun u faqat `DEBUG=False` da qo'yiladi — ya'ni
    productionda har doim, ishlab chiqishda hech qachon. Sozlama
    bilan emas, ataylab `DEBUG` bilan bog'langan: "productionda
    `Secure` ni o'chirib qo'yish" degan holat bo'lmasligi kerak.
    """
    return not settings.DEBUG


def set_refresh_cookie(response: Any, raw_token: str) -> None:
    lifetime = settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"]
    response.set_cookie(
        REFRESH_COOKIE,
        raw_token,
        max_age=int(lifetime.total_seconds()),
        httponly=True,
        secure=_secure(),
        samesite="Strict",
        path=COOKIE_PATH,
    )
    # CSRF juftligi: bu cookie JS uchun O'QILADIGAN bo'lishi kerak —
    # frontend uni sarlavhaga ko'chiradi. Sir emas: uning butun
    # ma'nosi "bu so'rov bizning sahifamizdan keldi" ni isbotlash.
    response.set_cookie(
        CSRF_COOKIE,
        secrets.token_urlsafe(24),
        max_age=int(lifetime.total_seconds()),
        httponly=False,
        secure=_secure(),
        samesite="Strict",
        path="/",
    )


def clear_refresh_cookie(response: Any) -> None:
    response.delete_cookie(REFRESH_COOKIE, path=COOKIE_PATH)
    response.delete_cookie(CSRF_COOKIE, path="/")


def read_refresh_cookie(request: Any) -> str:
    return str(request.COOKIES.get(REFRESH_COOKIE) or "")


def csrf_ok(request: Any) -> bool:
    """
    Double-submit tekshiruvi.

    Begona sayt bizning cookie'imizni o'qiy olmaydi (same-origin
    policy), ya'ni sarlavhani to'g'ri to'ldira olmaydi. Cookie yo'q
    bo'lsa tekshiruv o'tadi: bu eski mijoz yoki birinchi so'rov, va
    o'shanda refresh token ham cookie'dan kelmaydi — demak CSRF
    vektori yo'q.
    """
    cookie = str(request.COOKIES.get(CSRF_COOKIE) or "")
    if not cookie:
        return True
    header = str(request.headers.get(CSRF_HEADER) or "")
    return bool(header) and secrets.compare_digest(header, cookie)
