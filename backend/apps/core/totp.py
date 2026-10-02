"""
TOTP (RFC 6238) — ikkinchi omil algoritmi, **ikki tekislik uchun bitta**.

Kutubxona qo'shilmadi: algoritm o'ttiz qatorda va u standart
kutubxonadagi `hmac` bilan to'liq ifodalanadi. Bitta bog'liqlik kamayishi
bu darajadagi kod uchun arziydi — ayniqsa u autentifikatsiya yo'lida
turgan bog'liqlik bo'lsa.

Ilgari bu fayl `apps/platform/` da yashardi, chunki 2FA faqat vendor
hisoblarida bor edi. Mijoz egasiga ham ixtiyoriy 2FA qo'shilgach
(PLAN 5.4, ADR-24) u `core` ga ko'chdi: ikki nusxa algoritm — bu ikki
xil xulq va bir kun ikkinchisida tuzatilmagan xato. Modulda MODEL
yo'q, faqat matematika, ya'ni ADR-10 dagi tekisliklar ajratuvi
buzilmaydi: har bir tekislik sirni o'z jadvalida saqlaydi.

**Majburiylik har xil.** Vendor uchun 2FA — talab (`PLATFORM_2FA_REQUIRED`,
sukut bo'yicha YOQILGAN, ADR-24). Mijoz xodimlari uchun esa MAJBURIY
EMAS va bo'lmaydi ham: bog'chada telefon almashinuvi tez-tez bo'ladi va
majburiy 2FA ularni bitta umumiy telefonga o'tishga majburlardi — ya'ni
audit izini buzardi (P7 bilan bir xil mantiq).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

__all__ = ["generate_secret", "provisioning_uri", "verify", "current_code"]

DIGITS = 6
PERIOD = 30
# Bir qadam oldinga va orqaga ruxsat: telefon soati bir necha soniya
# farq qilishi normal holat va uni "noto'g'ri kod" deb ko'rsatish
# foydalanuvchini tizimdan chiqarib yuborardi.
WINDOW = 1


def generate_secret() -> str:
    """Yangi base32 sir — QR kodga tushadigan qiymat."""
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _code_at(secret: str, counter: int) -> str:
    padding = "=" * (-len(secret) % 8)
    key = base64.b32decode(secret + padding, casefold=True)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(value % 10**DIGITS).zfill(DIGITS)


def current_code(secret: str, *, at: float | None = None) -> str:
    return _code_at(secret, int((at or time.time()) // PERIOD))


def verify(secret: str, code: str, *, at: float | None = None) -> bool:
    """
    Kodni tekshiradi.

    Taqqoslash `hmac.compare_digest` bilan — vaqt hujumiga qarshi. Oddiy
    `==` kodni belgima-belgi taqqoslab, javob vaqti orqali to'g'ri
    prefiksni oshkor qilardi.
    """
    if not secret or not code or not code.strip().isdigit():
        return False
    counter = int((at or time.time()) // PERIOD)
    return any(
        hmac.compare_digest(_code_at(secret, counter + shift), code.strip())
        for shift in range(-WINDOW, WINDOW + 1)
    )


def provisioning_uri(secret: str, *, account: str, issuer: str = "Radix CRM") -> str:
    """
    Authenticator ilovasi uchun `otpauth://` havolasi.

    `issuer` — ilovada ko'rinadigan nom, ya'ni ommaviy brend
    (`Radix CRM`). U sirga ta'sir qilmaydi: nomi o'zgargani eski
    yozuvlarni buzmaydi, faqat yangi yozuv boshqa nom bilan tushadi.
    """
    return (
        f"otpauth://totp/{quote(issuer)}:{quote(account)}?secret={secret}"
        f"&issuer={quote(issuer)}&algorithm=SHA1&digits={DIGITS}&period={PERIOD}"
    )
