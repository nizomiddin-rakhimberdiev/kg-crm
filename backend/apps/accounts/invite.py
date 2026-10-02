"""
Taklif havolasi — yangi bog'cha egasi parolni O'ZI o'rnatadi (PLAN 5.5).

Avval vendor konsolda yangi mijoz ochganda parolni ham yozardi, keyin
uni telefonda yoki Telegramda aytib yuborardi. Uch muammo birga:

1. **Vendor mijozning parolini biladi.** U yerdan keyin "biz hech
   qachon mijoz ma'lumotini ko'rmaymiz" (ADR-10) degan da'vo
   ishonchsiz bo'lib qoladi — texnik jihatdan ham, ijtimoiy jihatdan
   ham.
2. **Parol ochiq kanal orqali uzatiladi** va o'sha yozishmada abadiy
   qoladi.
3. **Mijoz uni almashtirmaydi.** Amalda hech kim almashtirmaydi.

Shuning uchun: vendor parol yozmaydi, egaga 72 soatlik havola ketadi
va u birinchi kirishda parolni o'zi o'rnatadi.

**Token bazada saqlanmaydi** — `TimestampSigner` bilan imzolanadi va
ichida foydalanuvchi id'si hamda **parol xeshining qisqa izi** bor.
Parol o'rnatilgach iz o'zgaradi va havola o'z-o'zidan o'ladi: bir
martalik xususiyat tekinga keladi, yangi jadval va tozalash vazifasi
kerak emas (`password_reset.py` bilan bir xil mantiq).

**Nega 72 soat.** Parolni tiklash havolasi 30 daqiqa yashaydi, chunki
odam uni o'zi hozir so'ragan. Taklif boshqa: u sotuv suhbatidan keyin
yuboriladi va bog'cha egasi uni dushanba kuni ochishi mumkin. Bir
kundan kam oyna — "havola ishlamadi" degan qo'ng'iroqlar; bir haftadan
ko'p esa yopilmagan eshik.
"""

from __future__ import annotations

import hashlib
from typing import Any

from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.utils.translation import gettext

from apps.accounts.models import User

__all__ = ["INVITE_MAX_AGE", "make_token", "read_token", "build_link", "send_invite_email"]

#: 72 soat.
INVITE_MAX_AGE = 72 * 3600

_SALT = "radix.invite"


def _fingerprint(user: User) -> str:
    """
    Parol xeshining qisqa izi.

    Parol o'rnatilgach xesh o'zgaradi, ya'ni iz ham o'zgaradi va eski
    havola yaroqsiz bo'ladi. Xeshning O'ZI tokenga tushmaydi: u
    bo'lmagan taqdirda ham havola oshkor bo'lsa, undan parol haqida
    hech narsa chiqarib bo'lmaydi.
    """
    return hashlib.sha256(user.password.encode()).hexdigest()[:12]


def make_token(user: User) -> str:
    return signing.TimestampSigner(salt=_SALT).sign(f"{user.pk}:{_fingerprint(user)}")


def read_token(token: str, *, max_age: int = INVITE_MAX_AGE) -> User | None:
    """Tokendan foydalanuvchi; muddati o'tgan yoki ishlatilgan bo'lsa `None`."""
    from apps.core.tenancy import auth_lookup_context

    try:
        payload = signing.TimestampSigner(salt=_SALT).unsign(token, max_age=max_age)
    except (signing.BadSignature, signing.SignatureExpired):
        return None

    user_id, _, fingerprint = payload.partition(":")
    if not user_id or not fingerprint:
        return None

    # Tor eshik: taklifni qabul qilish tenant ANIQLANMAGAN holda
    # bo'ladi, xuddi login kabi (docs/03 §6.3).
    with auth_lookup_context():
        user = User.auth_objects.filter(pk=user_id, is_active=True).first()
    if user is None or _fingerprint(user) != fingerprint:
        # Iz mos kelmasa — parol allaqachon o'rnatilgan, ya'ni havola
        # ishlatilgan.
        return None
    return user


def build_link(user: User) -> str:
    base = str(getattr(settings, "FRONTEND_URL", "")).rstrip("/")
    return f"{base}/invite?token={make_token(user)}"


def send_invite_email(user: User, link: str, organization_name: str) -> None:
    """
    Taklifni yuboradi. Xato bo'lsa tashkilot YARATILGAN qoladi.

    Vendor javobda havolani ham oladi, ya'ni pochta ishlamasa u
    havolani qo'lda uzatishi mumkin. Tashkilotni yaratmay turish esa
    noto'g'ri bo'lardi: sotuv suhbati tugagan, mijoz kutayapti.
    """
    import logging

    hours = INVITE_MAX_AGE // 3600
    subject = gettext("Radix CRM — bogʻchangiz tayyor")
    body = gettext(
        "Assalomu alaykum, {name}!\n\n"
        "{organization} uchun Radix CRM hisobi ochildi.\n"
        "Parolni oʻzingiz oʻrnatasiz — havolani bosing:\n\n"
        "{link}\n\n"
        "Havola {hours} soat ishlaydi. Parolni hech kimga aytmang: "
        "biz ham uni bilmaymiz va soʻramaymiz."
    ).format(
        name=user.full_name or user.email, organization=organization_name, link=link, hours=hours
    )

    try:
        send_mail(subject=subject, message=body, from_email=None, recipient_list=[user.email])
    except Exception:  # noqa: BLE001 — tashkilot yaratilgan qoladi
        logging.getLogger(__name__).exception("Taklif xati yuborilmadi: %s", user.pk)


def accept(*, user: User, password: str) -> None:
    """Parolni o'rnatadi — shu bilan havola ham o'ladi (iz o'zgaradi)."""
    user.set_password(password)
    user.save(update_fields=["password", "updated_at"])


def audit_changes() -> dict[str, Any]:
    return {"invite_accepted": True}
