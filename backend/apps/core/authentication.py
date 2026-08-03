"""
Tenant kontekstini o'rnatuvchi JWT autentifikatsiyasi.

Nega bu middleware'da emas: DRF autentifikatsiyasi middleware'dan **keyin**,
view ichida ishlaydi. Middleware paytida JWT so'rovlarida `request.user` hali
`AnonymousUser` — ya'ni u yerdan tashkilotni olib bo'lmaydi.

`DEFAULT_PERMISSION_CLASSES = [IsAuthenticated]` bo'lgani uchun `request.user`
har doim view tanasidan oldin o'qiladi, demak kontekst har doim o'rnatilgan
bo'ladi. Autentifikatsiya umuman bo'lmasa (ochiq endpoint) kontekst `None`
qoladi va tenant-scoped so'rov `TenantScopeMissing` bilan yiqiladi —
fail-closed.
"""

from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.settings import api_settings

from apps.core.tenancy import set_current_organization_id

__all__ = ["TenantJWTAuthentication"]


class TenantJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token: Any) -> Any:
        user_id = validated_token.get(api_settings.USER_ID_CLAIM)
        if user_id is None:
            raise InvalidToken("Tokenda foydalanuvchi identifikatori yo'q.")

        # `auth_objects` — ataylab tenant filtrisiz. Bu tovuq-tuxum holati:
        # foydalanuvchini topish AYNAN kontekstni o'rnatadigan so'rov, shuning
        # uchun u o'zi cheklangan bo'la olmaydi. Bu yagona joy — qolgan hamma
        # narsa shundan keyin cheklanadi.
        user = (
            get_user_model()
            .auth_objects.filter(**{api_settings.USER_ID_FIELD: user_id})
            .select_related("organization", "role", "branch")
            .first()
        )
        if user is None:
            raise AuthenticationFailed("Foydalanuvchi topilmadi.", code="user_not_found")
        if not user.is_active:
            raise AuthenticationFailed("Hisob faol emas.", code="user_inactive")

        claimed = validated_token.get("organization_id")
        actual = str(user.organization_id) if user.organization_id else None

        # Tokendagi tashkilot bazadagisi bilan mos kelishi shart.
        # `organization_id` o'zgarmas (DB trigger), shuning uchun nomuvofiqlik
        # faqat eskirgan yoki qalbaki tokenda bo'ladi — ikkalasi ham rad etiladi.
        if claimed != actual:
            raise InvalidToken("Token tashkiloti hisob bilan mos kelmaydi.")

        set_current_organization_id(user.organization_id)
        return user
