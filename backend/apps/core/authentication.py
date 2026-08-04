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

import uuid
from typing import Any

from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.settings import api_settings

from apps.core.rls import apply_tenant_setting
from apps.core.tenancy import set_current_organization_id

__all__ = ["TenantJWTAuthentication"]


class TenantJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token: Any) -> Any:
        user_id = validated_token.get(api_settings.USER_ID_CLAIM)
        if user_id is None:
            raise InvalidToken("Tokenda foydalanuvchi identifikatori yo'q.")

        # Tashkilot TOKENDAN olinadi va kontekst foydalanuvchini
        # qidirishdan OLDIN o'rnatiladi.
        #
        # Avval bu teskari edi: `auth_objects` (filtrsiz) bilan
        # foydalanuvchi topilib, keyin tashkilot solishtirilardi. U ham
        # ishlagan, lekin RLS qo'shilganda ma'lum bo'ldiki, bu tartib
        # `user` jadvaliga cross-tenant o'qish talab qiladi. Tartibni
        # teskari qilish esa **hech qanday eshikni** talab qilmaydi:
        # token yolg'on tashkilot ko'rsatsa, foydalanuvchi o'sha
        # tashkilotda topilmaydi va so'rov 401 oladi. Ya'ni RLS
        # tekshiruvni kod bilan BIRGA bajaradi, kod o'rniga emas.
        claimed = validated_token.get("organization_id")
        if not claimed:
            raise InvalidToken("Tokenda tashkilot ko'rsatilmagan.")

        set_current_organization_id(uuid.UUID(str(claimed)))
        apply_tenant_setting(claimed)

        user = (
            get_user_model()
            .objects.filter(**{api_settings.USER_ID_FIELD: user_id})
            .select_related("organization", "role", "branch")
            .first()
        )
        if user is None:
            raise AuthenticationFailed("Foydalanuvchi topilmadi.", code="user_not_found")
        if not user.is_active:
            raise AuthenticationFailed("Hisob faol emas.", code="user_inactive")

        # Ikki qavatli tekshiruv: yuqoridagi filtr allaqachon tashkilotni
        # cheklaydi, lekin bu shart aniq XABAR beradi va menejer
        # o'zgarsa ham qoladi.
        actual = str(user.organization_id) if user.organization_id else None
        if str(claimed) != actual:
            raise InvalidToken("Token tashkiloti hisob bilan mos kelmaydi.")

        return user
