"""
Ikki bosqichli tasdiqlash — mijoz tomoni (PLAN 5.4, ADR-24).

Vendor tekisligida 2FA **majburiy** (`PLATFORM_2FA_REQUIRED`, sukut
bo'yicha yoqilgan). Mijoz tomonida esa **ixtiyoriy va o'z-o'ziga
xizmat**: har kim o'z hisobini himoyalaydi, hech kim boshqasiga
yoqib qo'ymaydi.

Nega majburiy emas: bog'chada smenada ishlaydigan odamda shaxsiy
smartfon bo'lmasligi mumkin, va majburiy kod jamoani bitta umumiy
telefonga o'tishga majburlardi — ya'ni audit izi "kim kirdi" degan
savolga javob bermay qolardi. Ega uchun esa u aynan kerak: uning
hisobi butun bog'chaning moliyasini ko'radi.

**Yoqish ikki qadam.** `start_setup()` sirni yaratadi va saqlaydi,
lekin 2FA hali ISHLAMAYDI; `confirm()` haqiqiy kodni tekshirib
yoqadi. Bir qadamda qilinsa, QR'ni ko'rib ilovaga qo'shmagan odam
keyingi kirishda o'z hisobidan chiqib qolardi.

**Zaxira kodlari — yoqishning sharti**, qo'shimcha emas: telefon
sinadi, va vendor mijozning ma'lumotiga YOZA olmaydi (ADR-10), ya'ni
"bizga yozing" degan yechim bu yerda mavjud emas.
"""

from __future__ import annotations

from typing import Any

from django.utils import timezone

from apps.accounts.models import User
from apps.core import backup_codes
from apps.core.totp import generate_secret, provisioning_uri, verify

__all__ = [
    "start_setup",
    "confirm",
    "disable",
    "regenerate_backup_codes",
    "check_second_factor",
    "ISSUER",
]

#: Authenticator ilovasida ko'rinadigan nom — ommaviy brend.
ISSUER = "Radix CRM"


def start_setup(user: User) -> dict[str, Any]:
    """
    Yangi sir yaratadi. 2FA hali YOQILMAYDI.

    Har chaqiruvda YANGI sir: foydalanuvchi sozlashni yarim yo'lda
    tashlab, boshqa telefonda qaytadan boshlashi normal holat, va
    eski sirni qoldirish "qaysi biri ishlaydi?" degan savolni
    tug'dirardi.
    """
    secret = generate_secret()
    user.totp_secret = secret
    user.totp_confirmed_at = None
    user.totp_backup_codes = []
    user.save(update_fields=["totp_secret", "totp_confirmed_at", "totp_backup_codes", "updated_at"])
    return {
        "secret": secret,
        "otpauth_uri": provisioning_uri(secret, account=user.email, issuer=ISSUER),
    }


def confirm(*, user: User, code: str) -> list[str]:
    """
    Kodni tekshirib 2FA ni yoqadi va zaxira kodlarini qaytaradi.

    Kodlar FAQAT shu yerda, bir marta ko'rinadi: ularning xeshi
    saqlanadi, o'zi esa yo'q.
    """
    if not user.totp_secret or not verify(user.totp_secret, code):
        return []

    codes, hashes = backup_codes.generate()
    user.totp_confirmed_at = timezone.now()
    user.totp_backup_codes = hashes
    user.save(update_fields=["totp_confirmed_at", "totp_backup_codes", "updated_at"])
    return codes


def disable(user: User) -> None:
    """O'chirish — sir ham, kodlar ham qoldirilmaydi."""
    user.totp_secret = ""
    user.totp_confirmed_at = None
    user.totp_backup_codes = []
    user.save(update_fields=["totp_secret", "totp_confirmed_at", "totp_backup_codes", "updated_at"])


def regenerate_backup_codes(user: User) -> list[str]:
    """
    Yangi kodlar — eskilari DARHOL yaroqsiz.

    Kerak bo'ladigan holat aniq: qog'oz yo'qoldi, yoki kodlar
    tugashiga yaqin qoldi.
    """
    codes, hashes = backup_codes.generate()
    user.totp_backup_codes = hashes
    user.save(update_fields=["totp_backup_codes", "updated_at"])
    return codes


def check_second_factor(user: User, code: str) -> str | None:
    """
    Kirish paytidagi tekshiruv: `"totp"`, `"backup"` yoki `None`.

    Ishlatilgan zaxira kodi ro'yxatdan O'CHIRILADI. Yozuv
    `auth_lookup_context()` ichida bo'ladi — bu paytda tenant
    konteksti hali yo'q (kirish tashkilot tanlanishidan oldin
    bo'ladi, ADR-9), shuning uchun `auth_objects` orqali.
    """
    code = (code or "").strip()
    if not code or not user.has_2fa:
        return None

    if verify(user.totp_secret, code):
        return "totp"

    remaining = backup_codes.consume(list(user.totp_backup_codes or []), code)
    if remaining is None:
        return None

    from apps.core.tenancy import auth_lookup_context

    user.totp_backup_codes = remaining
    with auth_lookup_context():
        User.auth_objects.filter(pk=user.pk).update(totp_backup_codes=remaining)
    return "backup"
