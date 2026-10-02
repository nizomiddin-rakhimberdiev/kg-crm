"""Auth endpointlari (docs/04 §5). View'lar yupqa — mantiq servislarda."""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.db import transaction
from django.utils.translation import gettext
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken as JWTRefreshToken

from apps.accounts import services
from apps.accounts.authentication import (
    authenticate_candidates,
    hydrate_user,
    issue_pending_token,
    issue_token_pair,
    read_pending_token,
)
from apps.accounts.models import User
from apps.accounts.serializers import (
    LoginSerializer,
    PasswordChangeSerializer,
    ProfilePhotoSerializer,
    ProfileUpdateSerializer,
    SelectOrganizationSerializer,
)
from apps.audit import services as audit
from apps.core.tenancy import auth_lookup_context, organization_context
from apps.core.typing import request_user

__all__ = [
    "LoginView",
    "SelectOrganizationView",
    "RefreshView",
    "LogoutView",
    "MeView",
    "ProfilePhotoView",
    "PasswordChangeView",
]


logger = logging.getLogger(__name__)


class LoginThrottle(AnonRateThrottle):
    """Brute-force'ga qarshi (docs/02 §20.2)."""

    scope = "login"


class RefreshThrottle(AnonRateThrottle):
    """
    Token yangilash uchun alohida, keng chegara.

    `RefreshView` anonim (`AllowAny`) — access token muddati tugagani uchun
    aynan shu so'rov yuboriladi. Alohida scope bo'lmasa u umumiy `anon`
    (120/soat, IP bo'yicha) chegarasiga tushadi, bog'chada esa hamma bitta
    IP ortida: ish kuni o'rtasida yangilash 429 bilan qaytadi va xodimlar
    sessiyasi uziladi. Sozlamalardagi izohga qarang.
    """

    scope = "refresh"


def _org_summary(user: User) -> dict[str, str]:
    # Bu funksiya faqat login nomzodlari uchun chaqiriladi — ular ta'rifiga
    # ko'ra tashkilotga tegishli (platforma xodimlari bu yo'ldan kelmaydi).
    organization = user.organization
    assert organization is not None
    return {
        "id": str(organization.id),
        "name": organization.name,
        "slug": organization.slug,
    }


class LoginView(APIView):
    """
    `POST /auth/login`.

    Email tashkilot ichida unikal bo'lgani uchun bitta email bir nechta
    hisobga mos kelishi mumkin — u holda pending token qaytariladi.
    """

    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        candidates = authenticate_candidates(email, serializer.validated_data["password"])

        if not candidates:
            audit.record(
                action="login_failed",
                request=request._request,
                actor_email=email,
            )
            # Umumiy xabar: "email yo'q" va "parol xato" farqlanmasin.
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "AUTHENTICATION_REQUIRED",
                        "message": gettext("Email yoki parol notoʻgʻri."),
                        "details": None,
                    },
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if len(candidates) > 1:
            # Faqat paroli MOS KELGAN tashkilotlar ko'rsatiladi — aks holda
            # login "bu email qaysi bog'chalarda bor?" orakuliga aylanardi.
            return Response(
                {
                    "pending_token": issue_pending_token(email),
                    "organizations": [_org_summary(u) for u in candidates],
                }
            )

        return Response(self._complete_login(request, candidates[0]))

    @staticmethod
    def _complete_login(request: Request, user: User) -> dict[str, Any]:
        with organization_context(user.organization_id):
            tokens = issue_token_pair(user)
            services.store_refresh_token(
                user=user,
                raw_token=tokens["refresh"],
                lifetime=settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"],
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                ip=audit.client_ip(request._request),
            )
            services.touch_last_login(user)
            audit.record(action="login", request=request._request, actor=user)
            payload = services.user_payload(user)

        return {
            **tokens,
            "user": payload,
            "subscription": services.subscription_payload(user.organization),
        }


class SelectOrganizationView(APIView):
    """`POST /auth/select-organization` — pending token → to'liq tokenlar."""

    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request: Request) -> Response:
        serializer = SelectOrganizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payload = read_pending_token(serializer.validated_data["pending_token"])
        except TokenError:
            return _auth_error(gettext("Tanlov muddati tugadi. Qaytadan kiring."))

        with auth_lookup_context():
            user = User.auth_objects.filter(
                email__iexact=payload.get("email", ""),
                organization_id=serializer.validated_data["organization_id"],
                is_active=True,
            ).first()
        if user is not None:
            user = hydrate_user(user)
        if user is None:
            # Pending token to'g'ri, lekin tashkilot ro'yxatda yo'q edi.
            # Bir xil umumiy xato — mavjudlikni oshkor qilmaymiz.
            return _auth_error(gettext("Tanlangan tashkilot mavjud emas."))

        return Response(LoginView._complete_login(request, user))


class RefreshView(APIView):
    """`POST /auth/refresh` — access tokenni yangilaydi (rotatsiya bilan)."""

    permission_classes = [AllowAny]
    throttle_classes = [RefreshThrottle]

    def post(self, request: Request) -> Response:
        raw = request.data.get("refresh")
        if not raw:
            return _auth_error(gettext("Refresh token koʻrsatilmagan."))

        # Refresh token — tenant hali noma'lum bo'lgan paytdagi qidiruv,
        # xuddi login kabi. Tor eshik shuning uchun `refresh_token` ni
        # ham qamraydi (docs/03 §6.3).
        with auth_lookup_context():
            stored = services.RefreshToken.objects.filter(
                token_hash=services.hash_token(raw)
            ).first()
        if stored is None:
            return _auth_error(gettext("Refresh token yaroqsiz."))

        if not stored.is_valid:
            # BEKOR QILINGAN tokenni qayta ishlatish — o'g'irlangan
            # sessiya belgisi (P2-004).
            #
            # Rotatsiya har yangilashda eski tokenni o'ldiradi, ya'ni
            # normal mijoz uni ikkinchi marta ishlatmaydi. Ishlatgan
            # bo'lsa — ikkita nusxa bor: haqiqiy foydalanuvchi va
            # o'g'ri. Qaysi biri ekanini bilib bo'lmaydi, shuning
            # uchun ikkalasi ham yopiladi: foydalanuvchining BARCHA
            # sessiyalari bekor qilinadi va u qayta kirishga majbur
            # bo'ladi. Noqulaylik — bu holatda to'g'ri narx.
            #
            # Faqat rad etish yetarli emasdi: o'g'ri allaqachon YANGI
            # token olgan bo'lardi va u ishlayverardi — ya'ni haqiqiy
            # foydalanuvchi bloklanib, o'g'ri qolardi.
            if stored.revoked_at is not None:
                with auth_lookup_context():
                    compromised = User.auth_objects.filter(pk=stored.user_id).first()
                if compromised is not None:
                    with organization_context(compromised.organization_id):
                        closed = services.revoke_all_refresh_tokens(compromised)
                        audit.record(
                            action="logout",
                            request=request._request,
                            actor=None,
                            organization=compromised.organization,
                            actor_email=compromised.email,
                            entity_type="refresh_token",
                            changes={"reason": "reuse_detected", "sessions_closed": closed},
                        )
                    logger.warning(
                        "Bekor qilingan refresh token qayta ishlatildi — barcha sessiyalar yopildi"
                    )
            return _auth_error(gettext("Refresh token yaroqsiz."))

        try:
            token = JWTRefreshToken(raw)
        except TokenError:
            return _auth_error(gettext("Refresh token yaroqsiz."))

        with auth_lookup_context():
            user = User.auth_objects.filter(pk=token["user_id"], is_active=True).first()
        if user is not None:
            user = hydrate_user(user)
        if user is None:
            return _auth_error(gettext("Refresh token yaroqsiz."))

        with transaction.atomic(), organization_context(user.organization_id):
            services.revoke_refresh_token(raw)  # rotatsiya: eskisi darhol o'ladi
            tokens = issue_token_pair(user)
            services.store_refresh_token(
                user=user,
                raw_token=tokens["refresh"],
                lifetime=settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"],
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                ip=audit.client_ip(request._request),
            )
        return Response(tokens)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        raw = request.data.get("refresh")
        if raw:
            services.revoke_refresh_token(raw)
        audit.record(action="logout", request=request._request, actor=request_user(request))
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    """
    `GET /auth/me` — frontend boot paytida auth holatini to'ldiradi.
    `PATCH /auth/me` — foydalanuvchi O'ZINING profilini tahrirlaydi.

    PATCH ataylab `/users/{id}` dan alohida: u `users.update` ruxsatini
    talab qiladi, ya'ni kassir o'z telefon raqamini ham o'zgartira olmasdi.
    Bu endpoint esa ID qabul qilmaydi — u har doim so'rov egasining o'z
    qatorini yangilaydi, va faqat xavfsiz maydonlarni: rol ham, filial ham,
    `is_active` ham bu yerdan o'zgarmaydi (aks holda har bir foydalanuvchi
    o'zini tashkilot egasi qilib qo'ya olardi).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        user = request_user(request)
        # Bog'chaning sukut tili shu yerda qaytadi: frontend uni boot
        # paytida (foydalanuvchining o'z tanlovi bo'lmasa) qo'llaydi.
        # Alohida so'rov qilmaymiz — bu javob har yuklanishda baribir olinadi.
        from apps.settings_app.services import get_setting

        return Response(
            {
                "user": services.user_payload(user),
                "subscription": services.subscription_payload(user.organization),
                "organization_settings": {
                    "default_language": get_setting(key="general.default_language"),
                },
            }
        )

    def patch(self, request: Request) -> Response:
        user = request_user(request)
        serializer = ProfileUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        audit.record(
            action="update",
            request=request._request,
            actor=user,
            entity_type="user",
            entity_id=user.id,
            changes={"self_profile": sorted(serializer.validated_data)},
        )
        return Response(
            {
                "user": services.user_payload(user),
                "subscription": services.subscription_payload(user.organization),
            }
        )


class ProfilePhotoView(APIView):
    """
    `POST /auth/me/photo` — o'z profil rasmini yuklash.
    `DELETE /auth/me/photo` — rasmni olib tashlash.

    ID qabul qilmaydi: rasm har doim so'rov egasining o'zinikiga yoziladi.
    Boshqa xodimning rasmini almashtirish uchun `/users/{id}` yo'li bor va
    u `users.update` ruxsatini talab qiladi.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request: Request) -> Response:
        user = request_user(request)
        serializer = ProfilePhotoSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Eski faylni saqlab qo'yish keraksiz joy egallaydi va uni hech kim
        # ko'rmaydi — yangisi yozilgach o'chiriladi.
        previous = user.photo.name if user.photo else None
        serializer.save()
        if previous and previous != user.photo.name:
            user.photo.storage.delete(previous)

        audit.record(
            action="update",
            request=request._request,
            actor=user,
            entity_type="user",
            entity_id=user.id,
            changes={"self_profile": ["photo"]},
        )
        return Response(
            {
                "user": services.user_payload(user),
                "subscription": services.subscription_payload(user.organization),
            }
        )

    def delete(self, request: Request) -> Response:
        user = request_user(request)
        if user.photo:
            user.photo.delete(save=True)
            audit.record(
                action="update",
                request=request._request,
                actor=user,
                entity_type="user",
                entity_id=user.id,
                changes={"self_profile": ["photo:removed"]},
            )
        return Response(
            {
                "user": services.user_payload(user),
                "subscription": services.subscription_payload(user.organization),
            }
        )


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request_user(request)
        if not check_password(serializer.validated_data["current_password"], user.password):
            return _auth_error(gettext("Joriy parol notoʻgʻri."))

        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])

        # Parol o'zgarganda barcha boshqa sessiyalar yopiladi (docs/02 §20.2).
        services.revoke_all_refresh_tokens(user)
        audit.record(action="password_change", request=request._request, actor=user)
        return Response(status=status.HTTP_204_NO_CONTENT)


def _auth_error(message: str) -> Response:
    return Response(
        {
            "success": False,
            "error": {
                "code": "AUTHENTICATION_REQUIRED",
                "message": message,
                "details": None,
            },
        },
        status=status.HTTP_401_UNAUTHORIZED,
    )
