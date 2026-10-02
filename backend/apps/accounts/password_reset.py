"""
Parolni tiklash (PLAN 5.2).

**Token bazada SAQLANMAYDI.** Django'ning `PasswordResetTokenGenerator`
tokenni foydalanuvchining joriy parol xeshi va `last_login` dan hosil
qiladi, ya'ni:

* parol o'zgargach eski havola **o'z-o'zidan** o'ladi — "bir martalik"
  xususiyati tekinga keladi va uni qo'lda yuritish (jadval, `used_at`,
  tozalash vazifasi) kerak emas;
* tiklash jadvali RLS yuzasiga yangi jadval qo'shmaydi. Bu muhim:
  tiklash so'rovi tenant ANIQLANMAGAN holda keladi, ya'ni yangi
  jadval uchun yana bitta "tor eshik" kerak bo'lardi (docs/03 §6.3).

Foydalanuvchini email bo'yicha topish esa mavjud eshikdan o'tadi —
`User.auth_objects` (login bilan bir xil yo'l, ADR-9).

**Javob email mavjudligini OSHKOR QILMAYDI.** "Bu email ro'yxatda
yo'q" degan javob begona odamga mijozlar ro'yxatini tekshirish
imkonini beradi: bir bog'chaning direktori raqobatchisining xodimi
tizimda borligini bilib oladi. Shuning uchun javob har doim bir xil.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.translation import gettext

from apps.accounts.models import User

logger = logging.getLogger(__name__)

__all__ = [
    "build_link",
    "find_user",
    "all_users",
    "send_reset_email",
    "check_token",
    "user_from_uid",
    "reset_password",
]


def all_users(email: str) -> list[User]:
    """
    Email bo'yicha hisoblar — tenant ANIQLANMAGAN holda.

    Ikki narsa birga kerak:

    * `auth_objects` — tenant filtri yo'q menejer;
    * `auth_lookup_context()` — RLS'ning TOR eshigi (`user` va
      `refresh_token` jadvallari uchun, docs/03 §6.3). Uni
      so'ramasdan so'rov jimgina BO'SH qaytadi: baza qatorni
      ko'rsatmaydi, xato ham bermaydi. Aynan shunday bo'ldi — xat
      yuborilmasdi va sabab ko'rinmasdi.

    Email tashkilot ICHIDA unikal (ADR-9), ya'ni bir odam ikki
    bog'chada ishlashi mumkin. Havola HAR BIR hisob uchun alohida
    yuboriladi — aks holda ikkinchi bog'chadagi xodim parolini
    tiklay olmasdi.
    """
    from apps.core.tenancy import auth_lookup_context

    cleaned = (email or "").strip().lower()
    if not cleaned:
        return []
    with auth_lookup_context():
        return list(User.auth_objects.filter(email__iexact=cleaned, is_active=True))


def find_user(email: str) -> User | None:
    users = all_users(email)
    return users[0] if users else None


def build_link(user: User) -> str:
    """`{FRONTEND_URL}/reset-password?uid=…&token=…`"""
    query = urlencode(
        {
            "uid": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": default_token_generator.make_token(user),
        }
    )
    base = str(getattr(settings, "FRONTEND_URL", "")).rstrip("/")
    return f"{base}/reset-password?{query}"


def user_from_uid(uid: str) -> User | None:
    """Havoladagi `uid` dan foydalanuvchi — shu ham tor eshikdan."""
    from apps.core.tenancy import auth_lookup_context

    try:
        pk = urlsafe_base64_decode(uid).decode()
    except (TypeError, ValueError, UnicodeDecodeError):
        return None
    with auth_lookup_context():
        return User.auth_objects.filter(pk=pk, is_active=True).first()


def check_token(user: User, token: str) -> bool:
    return bool(default_token_generator.check_token(user, token))


def send_reset_email(user: User, link: str) -> None:
    """
    Xatni yuboradi. Xato bo'lsa JAVOB o'zgarmaydi.

    Pochta serveri yiqilsa ham javob bir xil bo'lishi kerak: aks
    holda "xat yuborilmadi" degan javob email bazada bor-yo'qligini
    oshkor qilib qo'yardi.
    """
    # Bog'cha nomi TENANT KONTEKSTIDA o'qiladi.
    #
    # `user.organization` ni kontekstsiz o'qish RLS ostida
    # `Organization.DoesNotExist` ko'taradi (qator ko'rinmaydi), va
    # DRF uni `404` ga aylantiradi — ya'ni tiklash so'rovi "topilmadi"
    # bo'lib qaytardi. `getattr(..., default)` buni yashirmaydi: u
    # faqat `AttributeError` ni ushlaydi.
    from apps.core.tenancy import organization_context

    with organization_context(user.organization_id):
        organization = getattr(user.organization, "name", "") or gettext("Radix CRM")
    minutes = max(1, int(getattr(settings, "PASSWORD_RESET_TIMEOUT", 1800)) // 60)
    subject = gettext("Radix CRM — parolni tiklash")
    body = gettext(
        "Assalomu alaykum, {name}!\n\n"
        "{organization} hisobingiz uchun parolni tiklash soʻrovi keldi.\n"
        "Yangi parol oʻrnatish uchun havolani bosing:\n\n"
        "{link}\n\n"
        "Havola {minutes} daqiqa ishlaydi va bir marta ishlatiladi.\n"
        "Agar bu soʻrovni siz yubormagan boʻlsangiz — hech narsa qilish "
        "kerak emas, parolingiz oʻzgarmaydi."
    ).format(
        name=user.full_name or user.email,
        organization=organization,
        link=link,
        minutes=minutes,
    )

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=None,  # `DEFAULT_FROM_EMAIL`
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception:  # noqa: BLE001 — javob o'zgarmasligi kerak
        logger.exception("Parol tiklash xati yuborilmadi: %s", user.pk)


def reset_password(*, user: User, password: str) -> None:
    """
    Parolni almashtiradi va BARCHA sessiyalarni yopadi.

    Agar hisob o'g'irlangan bo'lsa, parolni almashtirishning butun
    ma'nosi shu: eski token bilan ichkarida o'tirgan odam chiqarib
    yuborilishi kerak. Aks holda tiklash faqat qulfni almashtirib,
    ichkaridagini qoldirish bo'lardi.
    """
    from apps.accounts import services

    user.set_password(password)
    user.save(update_fields=["password", "updated_at"])
    services.revoke_all_refresh_tokens(user)


def audit_changes(user: User) -> dict[str, Any]:
    return {"password_reset": True, "sessions_closed": True}
