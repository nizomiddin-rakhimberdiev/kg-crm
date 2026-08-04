"""
Autentifikatsiya — ko'p tashkilotli login (docs/04 §5).

Email tashkilot ichida unikal, global emas. Ya'ni bitta email bir nechta
tashkilotda hisobga ega bo'lishi mumkin va Django'ning default
`ModelBackend` i buni hal qila olmaydi — u `USERNAME_FIELD` bo'yicha bitta
foydalanuvchi topilishiga tayanadi.

Oqim:
    1. `/auth/login` — email+parol barcha tashkilotlar bo'ylab tekshiriladi.
       Bitta moslik → to'liq token juftligi.
       Bir nechta moslik → qisqa muddatli **pending token** + tashkilotlar ro'yxati.
    2. `/auth/select-organization` — pending token + organization_id → to'liq tokenlar.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.contrib.auth.hashers import check_password
from django.utils import timezone
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken, Token
from rest_framework_simplejwt.tokens import RefreshToken as JWTRefreshToken

from apps.accounts.models import User
from apps.core.tenancy import auth_lookup_context, organization_context

__all__ = [
    "authenticate_candidates",
    "issue_token_pair",
    "PendingOrganizationToken",
]

# Pending token juda qisqa yashaydi: u faqat "parol to'g'ri, endi tashkilotni
# tanlang" degan bir qadamlik holat. Uzoq yashasa — u to'liq tokenga teng
# qiymatli o'g'irlash nishoniga aylanadi.
PENDING_TOKEN_LIFETIME = timedelta(minutes=5)


class PendingOrganizationToken(Token):
    """Tashkilot tanlanmaguncha amal qiladigan oraliq token."""

    token_type = "pending_organization"  # noqa: S105 — token turi, parol emas
    lifetime = PENDING_TOKEN_LIFETIME


def authenticate_candidates(email: str, password: str) -> list[User]:
    """
    Email+parol mos keladigan **barcha** hisoblarni qaytaradi.

    Diqqat: parol mos kelmagan tashkilotlar ro'yxatga TUSHMAYDI. Aks holda
    login "bu email qaysi bog'chalarda bor?" degan savolga javob beruvchi
    orakulga aylanardi (docs/04 §5).

    Vaqt hujumiga qarshi: hech qanday nomzod topilmasa ham bitta hash
    tekshiruvi bajariladi, shunda "email mavjud emas" va "parol noto'g'ri"
    holatlari bir xil vaqt oladi.
    """
    # Tor eshik: email bo'yicha qidirish AYNAN tenantni aniqlaydigan
    # so'rov, ya'ni u o'zi tenant bilan cheklangan bo'la olmaydi
    # (docs/03 §6.3). Eshik faqat `user` jadvaliga ochiladi.
    #
    # `select_related` bu yerda ATAYLAB YO'Q: `organization`, `role` va
    # `branch` eshikdan tashqarida, ya'ni JOIN ularni `NULL` qilib
    # qaytarardi — va bu jimgina, xatosiz sodir bo'lardi. Ular
    # foydalanuvchi aniqlangandan keyin, O'Z tashkiloti kontekstida
    # yuklanadi.
    with auth_lookup_context():
        candidates = list(User.auth_objects.filter(email__iexact=email, is_active=True))

    if not candidates:
        User().set_password(password)  # dummy hash — vaqtni tenglashtirish uchun
        return []

    matched = [u for u in candidates if check_password(password, u.password)]
    return [hydrate_user(u) for u in matched]


def hydrate_user(user: User) -> User:
    """
    Bog'liq obyektlarni foydalanuvchining O'Z tashkiloti kontekstida yuklaydi.

    Login paytida bu ikkinchi so'rov — lekin u tor eshikni `user`
    jadvali bilan cheklangan holda saqlaydi. Muqobili — eshikni
    `organization`, `role`, `branch` ga ham ochish, ya'ni login yo'lini
    buzgan kishiga butun tashkilot tuzilmasini berish.
    """
    with organization_context(user.organization_id):
        return User.objects.select_related("organization", "role", "branch").get(pk=user.pk)


def _apply_claims(token: Token, user: User) -> None:
    """
    Tenant ma'lumotini tokenga yozadi.

    `organization_id` tokendan olinadi va so'rovda mijozdan **hech qachon**
    qabul qilinmaydi — aks holda bu oddiy IDOR bo'lardi (docs/04 §1).
    """
    token["organization_id"] = str(user.organization_id) if user.organization_id else None
    token["branch_id"] = str(user.branch_id) if user.branch_id else None
    token["role"] = user.role.code if user.role else None


def issue_token_pair(user: User) -> dict[str, str]:
    """To'liq access + refresh juftligini beradi."""
    refresh = JWTRefreshToken.for_user(user)
    _apply_claims(refresh, user)
    _apply_claims(refresh.access_token, user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def issue_pending_token(email: str) -> str:
    token = PendingOrganizationToken()
    token["email"] = email
    token["issued_at"] = timezone.now().isoformat()
    return str(token)


def read_pending_token(raw: str) -> dict[str, Any]:
    """Pending tokenni o'qiydi; yaroqsiz bo'lsa `TokenError` ko'taradi."""
    # simplejwt stub'lari `Token(str)` ni tanimaydi, lekin haqiqiy
    # imzo aynan shunday (token: str | None).
    token = PendingOrganizationToken(raw)  # type: ignore[arg-type]
    return dict(token.payload)


def decode_access_token(raw: str) -> dict[str, Any]:
    try:
        return dict(AccessToken(raw).payload)  # type: ignore[arg-type]
    except TokenError:
        return {}
