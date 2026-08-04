"""
Platforma autentifikatsiyasi — mijoz yo'lidan ALOHIDA (ADR-10).

Ikkita farq muhim:

1. **Boshqa endpoint, boshqa token.** Token'da `plane: "platform"`
   da'vosi bor va mijoz API'si uni qabul qilmaydi (`organization_id`
   yo'q → 401). Teskarisi ham: mijoz tokeni platforma konsoliga
   kirolmaydi. Ikki tekislik tokenlari almashinmaydi.

2. **2FA majburiy.** `totp_secret` tasdiqlanmagan hisob umuman kira
   olmaydi — "keyin yoqaman" degan holat yo'q. Vendor hisobining
   buzilishi barcha mijozlarga tegadigan yagona hodisa.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from apps.core.tenancy import platform_context
from apps.platform.models import PlatformUser

__all__ = ["PlatformTokenAuthentication", "issue_platform_token", "PLATFORM_TOKEN_LIFETIME"]

# Qisqa muddat: platforma sessiyasi mijoz sessiyasidan xavfliroq va
# uni uzoq ushlab turishning sababi yo'q.
PLATFORM_TOKEN_LIFETIME = timedelta(hours=4)


def issue_platform_token(user: PlatformUser) -> str:
    token = AccessToken()
    token.set_exp(lifetime=PLATFORM_TOKEN_LIFETIME)
    token["plane"] = "platform"
    token["platform_user_id"] = str(user.id)
    token["role"] = user.role
    return str(token)


class PlatformTokenAuthentication(BaseAuthentication):
    """Faqat `plane: "platform"` tokenini qabul qiladi."""

    keyword = "Bearer"

    def authenticate_header(self, request: Any) -> str:
        """
        DRF bu metod bo'lmasa `401` o'rniga `403` qaytaradi.

        Farq muhim: `401` "kim ekaningizni bilmadim", `403` esa "kim
        ekaningizni bilaman, lekin ruxsat yo'q". Ikkinchisi platforma
        konsoli mavjudligini va sizning hisobingiz unga tegishli
        emasligini tasdiqlardi.
        """
        return f'{self.keyword} realm="platform"'

    def authenticate(self, request: Any) -> tuple[Any, Any] | None:
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith(f"{self.keyword} "):
            return None

        raw = header.split(" ", 1)[1].strip()
        try:
            token = AccessToken(raw)
        except TokenError as exc:
            raise AuthenticationFailed("Token yaroqsiz.") from exc

        if token.get("plane") != "platform":
            # Mijoz tokeni platforma konsoliga kira olmaydi. Bu
            # tekshiruv ataylab qat'iy: ikki tekislik tokenlari hech
            # qachon almashinmaydi (ADR-10).
            raise AuthenticationFailed("Bu token platforma konsoli uchun emas.")

        with platform_context():
            user = PlatformUser.objects.filter(
                pk=token.get("platform_user_id"), is_active=True
            ).first()
        if user is None:
            raise AuthenticationFailed("Hisob topilmadi yoki faol emas.")
        if not user.has_2fa:
            raise AuthenticationFailed("Ikki bosqichli tasdiqlash sozlanmagan.")

        user.is_authenticated = True  # type: ignore[attr-defined]
        return (user, token)


def authenticate_platform_user(*, email: str, password: str, code: str) -> PlatformUser:
    """
    Email + parol + TOTP. Uchtasi ham to'g'ri bo'lishi shart.

    Xato xabari HAR DOIM bir xil: qaysi omil noto'g'ri ekanini aytish
    hujumchiga qaysi bosqichda ekanini bildirardi.
    """
    with platform_context():
        user = PlatformUser.objects.filter(email__iexact=email, is_active=True).first()

    generic = AuthenticationFailed("Kirish ma'lumotlari noto'g'ri.")
    if user is None:
        PlatformUser().set_password(password)  # vaqtni tenglashtirish
        raise generic
    if not user.check_password(password):
        raise generic
    if not user.has_2fa:
        raise AuthenticationFailed("Ikki bosqichli tasdiqlash sozlanmagan.")

    from apps.platform.totp import verify

    if not verify(user.totp_secret, code):
        raise generic

    with platform_context():
        user.last_login_at = timezone.now()
        user.save(update_fields=["last_login_at", "updated_at"])
    return user
