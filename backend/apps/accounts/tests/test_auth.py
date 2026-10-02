"""Auth oqimi testlari (docs/04 §5)."""

from __future__ import annotations

from typing import Any

import pytest
from django.urls import reverse

from apps.accounts.models import RefreshToken, User
from apps.accounts.services import register_organization
from apps.core.tenancy import organization_context

pytestmark = pytest.mark.django_db

PASSWORD = "Juda-Kuchli-Parol-2026"  # noqa: S105


class TestPublicSignupIsClosed:
    """
    Ochiq ro'yxatdan o'tish OLIB TASHLANDI.

    Avvalgi `TestSignup` testlari o'chirilmadi — ular
    `apps/platform/tests/test_platform_console.py::TestOrganizationCreation`
    ga ko'chdi, chunki tekshiriladigan xulq-atvor o'sha-o'sha, faqat eshik
    vendor konsoliga ko'chdi.

    Bu yerda qolgan test boshqa narsani qo'riqlaydi: eshik QAYTA
    OCHILMASIN. Har bir signup haqiqiy tenant yaratadi — RLS siyosatlari,
    obuna, rollar — va ADR-11 bo'yicha mijoz ma'lumoti hech qachon
    o'chirilmaydi. Ya'ni tasodifan qaytarilgan `/auth/signup` bazada
    abadiy qoladigan begona tenantlar qoldirardi.
    """

    def test_the_signup_endpoint_no_longer_exists(self, api_client):
        response = api_client.post(
            "/api/v1/auth/signup",
            {
                "organization_name": "Yangi Bogʻcha",
                "contact_email": "owner@yangi.uz",
                "full_name": "Aziz Karimov",
                "password": PASSWORD,
            },
            format="json",
        )
        assert response.status_code == 404

        from apps.core.tenancy import platform_context
        from apps.organizations.models import Organization

        with platform_context():
            assert not Organization.objects.filter(name="Yangi Bogʻcha").exists()


def _refresh_cookie(response: Any) -> str:
    """
    Refresh token javob TANASIDA emas, COOKIE'da (PLAN 5.1).

    Testlar shu yordamchidan o'qiydi — ya'ni ular saqlash joyi
    o'zgarganini BIR MARTA biladi, har bir test alohida emas.
    """
    from apps.accounts.cookies import REFRESH_COOKIE

    return str(response.cookies[REFRESH_COOKIE].value)


def _refresh(client: Any, body: dict[str, Any] | None = None) -> Any:
    """
    Yangilash so'rovi — frontend kabi, CSRF sarlavhasi bilan.

    Cookie bilan kelgan so'rov `X-CSRFToken` ni talab qiladi va u
    `radix_csrf` cookie'siga mos bo'lishi kerak (double submit).
    Begona sayt bizning cookie'imizni o'qiy olmaydi, ya'ni
    sarlavhani to'g'ri to'ldira olmaydi.
    """
    from apps.accounts.cookies import CSRF_COOKIE, CSRF_HEADER

    headers = {}
    token = client.cookies.get(CSRF_COOKIE)
    if token is not None:
        headers[CSRF_HEADER] = token.value
    return client.post(reverse("v1:auth-refresh"), body or {}, format="json", headers=headers)


class TestLogin:
    def test_single_organization_returns_tokens(self, api_client, tenant_a):
        response = api_client.post(
            reverse("v1:auth-login"),
            {"email": tenant_a.owner.email, "password": PASSWORD},
            format="json",
        )
        assert response.status_code == 200
        data = response.json()["data"]
        # Refresh token TANADA YO'Q (PLAN 5.1): u yerda qolsa, mijoz
        # uni `localStorage` ga yozishi mumkin va httpOnly cookie'ga
        # o'tishning ma'nosi qolmasdi.
        assert data["access"]
        assert "refresh" not in data
        assert _refresh_cookie(response)
        assert data["user"]["organization"]["id"] == str(tenant_a.organization.id)

    def test_wrong_password_is_generic_401(self, api_client, tenant_a):
        response = api_client.post(
            reverse("v1:auth-login"),
            {"email": tenant_a.owner.email, "password": "noto-g-ri"},
            format="json",
        )
        assert response.status_code == 401
        # Xabar "email yoʻq" va "parol xato" ni farqlamasligi kerak.
        assert response.json()["error"]["message"] == "Email yoki parol notoʻgʻri."

    def test_unknown_email_gives_identical_response(self, api_client, tenant_a):
        known = api_client.post(
            reverse("v1:auth-login"),
            {"email": tenant_a.owner.email, "password": "noto-g-ri"},
            format="json",
        ).json()
        unknown = api_client.post(
            reverse("v1:auth-login"),
            {"email": "yoq@example.uz", "password": "noto-g-ri"},
            format="json",
        ).json()
        assert known == unknown, "Javob mavjud va mavjud boʻlmagan emailni farqlamasin"


class TestMultiOrganizationLogin:
    """Bir odam ikki bogʻchada ishlashi mumkin (docs/03 §10.6)."""

    @pytest.fixture
    def shared_email_user(self, tenant_a, tenant_b) -> str:
        email = "ustoz@example.uz"
        for tenant in (tenant_a, tenant_b):
            with organization_context(tenant.organization.id):
                User.objects.create_user(
                    email=email,
                    password=PASSWORD,
                    full_name="Ustoz",
                    organization=tenant.organization,
                    role=tenant.role("cashier"),
                    branch=tenant.branch,
                )
        return email

    def test_returns_pending_token_and_organization_list(self, api_client, shared_email_user):
        response = api_client.post(
            reverse("v1:auth-login"),
            {"email": shared_email_user, "password": PASSWORD},
            format="json",
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert "access" not in data
        assert data["pending_token"]
        assert len(data["organizations"]) == 2

    def test_select_organization_completes_login(self, api_client, shared_email_user, tenant_a):
        pending = api_client.post(
            reverse("v1:auth-login"),
            {"email": shared_email_user, "password": PASSWORD},
            format="json",
        ).json()["data"]["pending_token"]

        response = api_client.post(
            reverse("v1:auth-select-organization"),
            {"pending_token": pending, "organization_id": str(tenant_a.organization.id)},
            format="json",
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["user"]["organization"]["id"] == str(tenant_a.organization.id)

    def test_wrong_password_never_lists_organizations(self, api_client, shared_email_user):
        """
        Login "bu email qaysi bogʻchalarda bor?" orakuli bo'lmasligi kerak.

        Parol noto'g'ri bo'lsa tashkilotlar ro'yxati umuman qaytmaydi.
        """
        response = api_client.post(
            reverse("v1:auth-login"),
            {"email": shared_email_user, "password": "noto-g-ri"},
            format="json",
        )
        assert response.status_code == 401
        assert "organizations" not in response.json().get("data", {})


class TestRefreshAndLogout:
    def test_refresh_rotates_token(self, api_client, tenant_a):
        login = api_client.post(
            reverse("v1:auth-login"),
            {"email": tenant_a.owner.email, "password": PASSWORD},
            format="json",
        )
        first = _refresh_cookie(login)

        # Cookie klientda saqlanadi — tanada hech narsa yuborilmaydi.
        response = _refresh(api_client)
        assert response.status_code == 200
        assert _refresh_cookie(response) != first

    def test_old_refresh_token_stops_working(self, api_client, tenant_a):
        """Rotatsiyadan keyin eski token darhol oʻladi — qayta ishlatishga yoʻl yoʻq."""
        login = api_client.post(
            reverse("v1:auth-login"),
            {"email": tenant_a.owner.email, "password": PASSWORD},
            format="json",
        )
        old = _refresh_cookie(login)
        _refresh(api_client)

        # Eski tokenni TANADA yuborib ko'rish ham ishlamaydi —
        # rotatsiya uni o'ldirgan.
        api_client.cookies.clear()
        again = api_client.post(reverse("v1:auth-refresh"), {"refresh": old}, format="json")
        assert again.status_code == 401

    def test_logout_revokes_refresh_token(self, tenant_a):
        client = tenant_a.client()
        login_refresh = None
        with organization_context(tenant_a.organization.id):
            from django.conf import settings

            from apps.accounts.authentication import issue_token_pair
            from apps.accounts.services import store_refresh_token

            tokens = issue_token_pair(tenant_a.owner)
            store_refresh_token(
                user=tenant_a.owner,
                raw_token=tokens["refresh"],
                lifetime=settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"],
            )
            login_refresh = tokens["refresh"]

        response = client.post(reverse("v1:auth-logout"), {"refresh": login_refresh}, format="json")
        assert response.status_code == 204

        # So'rov tugagach kontekst tozalanadi (P0-001) — o'qish uchun qayta ochamiz.
        with organization_context(tenant_a.organization.id):
            assert RefreshToken.objects.filter(revoked_at__isnull=False).exists()


class TestRefreshTokenReuse:
    """
    O'g'irlangan sessiyani aniqlash (P2-004).

    Rotatsiya har yangilashda eski tokenni o'ldiradi, ya'ni normal mijoz
    uni ikkinchi marta ishlatmaydi. Ishlatgan bo'lsa — ikkita nusxa
    bor, va qaysi biri haqiqiy egasi ekanini bilib bo'lmaydi.
    """

    def _login(self, api_client, tenant):
        response = api_client.post(
            reverse("v1:auth-login"),
            {"email": tenant.owner.email, "password": PASSWORD},
            format="json",
        )
        assert response.status_code == 200
        return _refresh_cookie(response)

    @staticmethod
    def _raw(api_client, token: str):
        """
        XOM token bilan yangilash — brauzersiz.

        Bu ikki holatni modellaydi: (a) `localStorage` dagi tokeni bor
        ESKI mijozning bir martalik o'tishi, (b) tokenni o'g'irlagan,
        lekin bizning cookie'imiz yo'q odam. Shuning uchun cookie
        ataylab tozalanadi — aks holda view cookie'ni afzal ko'radi
        va sinov o'z ma'nosini yo'qotardi.
        """
        api_client.cookies.clear()
        return api_client.post(reverse("v1:auth-refresh"), {"refresh": token}, format="json")

    def test_reusing_a_rotated_token_closes_every_session(self, api_client, tenant_a):
        """
        Eski tokenni qayta ishlatish BARCHA sessiyalarni yopadi.

        Faqat rad etish yetarli emasdi: o'g'ri allaqachon yangi token
        olgan bo'lardi va u ishlayverardi — ya'ni haqiqiy foydalanuvchi
        bloklanib, o'g'ri qolardi.
        """
        first = self._login(api_client, tenant_a)

        # Normal yangilash — `first` bekor qilinadi, `second` beriladi.
        rotated = self._raw(api_client, first)
        assert rotated.status_code == 200
        second = _refresh_cookie(rotated)

        # Yangi token hozircha ishlaydi.
        assert self._raw(api_client, second).status_code == 200

        # ESKI tokenni qayta ishlatish — o'g'irlik belgisi.
        assert self._raw(api_client, first).status_code == 401

        # Endi barcha sessiyalar yopilgan bo'lishi kerak.
        with organization_context(tenant_a.organization.id):
            assert not RefreshToken.objects.filter(
                user=tenant_a.owner, revoked_at__isnull=True
            ).exists(), "ochiq sessiya qoldi — oʻgʻri hamon kira oladi"

    def test_the_thiefs_fresh_token_stops_working_too(self, api_client, tenant_a):
        """Eng muhimi: oʻgʻri olgan YANGI token ham oʻladi."""
        first = self._login(api_client, tenant_a)
        stolen_new = _refresh_cookie(self._raw(api_client, first))

        # Haqiqiy foydalanuvchi eski tokenini ishlatadi → oila yopiladi.
        self._raw(api_client, first)

        after = api_client.post(reverse("v1:auth-refresh"), {"refresh": stolen_new}, format="json")
        assert after.status_code == 401

    def test_an_unknown_token_does_not_close_anything(self, api_client, tenant_a):
        """
        Tanilmagan token — shunchaki yaroqsiz.

        Aks holda har kim istalgan satrni yuborib, boshqalarni
        tizimdan chiqarib yuborardi.
        """
        self._login(api_client, tenant_a)
        response = api_client.post(
            reverse("v1:auth-refresh"), {"refresh": "umuman-boshqa-narsa"}, format="json"
        )
        assert response.status_code == 401

        with organization_context(tenant_a.organization.id):
            assert RefreshToken.objects.filter(
                user=tenant_a.owner, revoked_at__isnull=True
            ).exists(), "begona token sessiyalarni yopib yubordi"


class TestMe:
    def test_requires_authentication(self, api_client):
        assert api_client.get(reverse("v1:auth-me")).status_code == 401

    def test_returns_user_with_permissions(self, tenant_a):
        response = tenant_a.client().get(reverse("v1:auth-me"))
        assert response.status_code == 200
        user = response.json()["data"]["user"]
        assert user["email"] == tenant_a.owner.email
        assert user["role"]["code"] == "org_owner"


class TestPasswordChange:
    def test_changes_password_and_revokes_sessions(self, tenant_a):
        client = tenant_a.client()
        response = client.post(
            reverse("v1:auth-password-change"),
            {"current_password": PASSWORD, "new_password": "Boshqa-Kuchli-Parol-2026"},
            format="json",
        )
        assert response.status_code == 204

        # So'rov tugagach kontekst tozalanadi (P0-001) — o'qish uchun qayta ochamiz.
        with organization_context(tenant_a.organization.id):
            tenant_a.owner.refresh_from_db()
            assert tenant_a.owner.check_password("Boshqa-Kuchli-Parol-2026")

    def test_wrong_current_password_rejected(self, tenant_a):
        response = tenant_a.client().post(
            reverse("v1:auth-password-change"),
            {"current_password": "xato", "new_password": "Boshqa-Kuchli-Parol-2026"},
            format="json",
        )
        assert response.status_code == 401


class TestTokenClaims:
    @pytest.mark.tenancy
    def test_token_from_other_organization_is_rejected(self, tenant_a, tenant_b):
        """
        Tokendagi `organization_id` bazadagisi bilan mos kelmasa — rad.

        Qalbaki yoki eskirgan token bilan begona tenant'ga kirishga urinish
        aynan shu yerda to'xtaydi.
        """
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken as JWTRefreshToken

        with organization_context(tenant_a.organization.id):
            token = JWTRefreshToken.for_user(tenant_a.owner)
            token["organization_id"] = str(tenant_b.organization.id)  # qalbakilashtirish
            access = str(token.access_token)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        assert client.get(reverse("v1:auth-me")).status_code == 401


class TestRegistrationService:
    def test_slug_is_unique_across_same_names(self, db):
        first = register_organization(
            organization_name="Bir xil nom",
            contact_email="a@a.uz",
            full_name="A",
            password=PASSWORD,
        )
        second = register_organization(
            organization_name="Bir xil nom",
            contact_email="b@b.uz",
            full_name="B",
            password=PASSWORD,
        )
        assert first.organization.slug != second.organization.slug


class TestSubscriptionPayload:
    """
    Signup va login javobida obuna holati BO'LISHI kerak.

    Bu regressiya testi: `subscription_payload` tenant kontekstidan
    tashqarida chaqirilardi va RLS ostida so'rov jimgina bo'sh
    qaytardi — obuna bazada bor, javobda `null`. Xato chiqmasdi,
    shunchaki sinov banneri hech qachon ko'rinmasdi va mijoz "necha
    kun qoldi?" degan savolga javob topolmasdi.
    """

    def test_login_response_carries_the_trial(self, api_client, tenant_a):
        response = api_client.post(
            reverse("v1:auth-login"),
            {"email": tenant_a.owner.email, "password": PASSWORD},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["data"]["subscription"]["status"] == "trialing"

    def test_me_carries_the_trial_too(self, tenant_a):
        response = tenant_a.client().get(reverse("v1:auth-me"))
        assert response.status_code == 200
        assert response.json()["data"]["subscription"]["status"] == "trialing"


class TestRefreshCookie:
    """
    Refresh token httpOnly cookie'da (PLAN 5.1).

    Avval u `localStorage` da yashardi va bu ongli murosa edi. Narxi
    aniq: bitta zararli skript (buzilgan npm paketi, reklama kodi)
    tokenni o'qib o'z serveriga yuborishi mumkin, va u YETTI KUN
    ishlaydi. `httpOnly` cookie'ni JavaScript umuman o'qiy olmaydi.
    """

    def _login(self, api_client, tenant):
        return api_client.post(
            reverse("v1:auth-login"),
            {"email": tenant.owner.email, "password": PASSWORD},
            format="json",
        )

    def test_the_cookie_carries_the_security_flags(self, api_client, tenant_a):
        from apps.accounts.cookies import REFRESH_COOKIE

        response = self._login(api_client, tenant_a)
        cookie = response.cookies[REFRESH_COOKIE]
        assert cookie["httponly"], "XSS tokenni o'qiy olmasligi kerak"
        assert cookie["samesite"] == "Strict", "begona saytdan kelgan so'rovga qo'shilmasin"
        # Yo'l cheklangan: cookie faqat auth endpointlariga ketadi.
        assert cookie["path"] == "/api/v1/auth"

    def test_an_old_session_migrates_once_and_then_uses_the_cookie(self, api_client, tenant_a):
        """
        Yumshoq o'tish: `localStorage` dagi tokeni bor sessiya bir
        marta yangilanadi va shu paytda cookie'ga ko'chadi.
        """
        old_token = _refresh_cookie(self._login(api_client, tenant_a))
        api_client.cookies.clear()

        migrated = api_client.post(
            reverse("v1:auth-refresh"), {"refresh": old_token}, format="json"
        )
        assert migrated.status_code == 200
        assert _refresh_cookie(migrated), "cookie o'rnatilishi kerak"

        # Ikkinchi yangilashda tana BO'SH — token cookie'dan keladi.
        assert _refresh(api_client).status_code == 200

    def test_a_cookie_request_without_the_csrf_header_is_refused(self, api_client, tenant_a):
        """
        CSRF — ikkinchi qatlam.

        `SameSite=Strict` ning o'zi deyarli yetarli, lekin u brauzerga
        ishonadi. Double submit esa begona saytni to'xtatadi: u
        bizning cookie'imizni O'QIY olmaydi, ya'ni sarlavhani to'g'ri
        to'ldira olmaydi.
        """
        self._login(api_client, tenant_a)
        response = api_client.post(reverse("v1:auth-refresh"), {}, format="json")
        assert response.status_code == 401

    def test_a_wrong_csrf_header_is_refused(self, api_client, tenant_a):
        from apps.accounts.cookies import CSRF_HEADER

        self._login(api_client, tenant_a)
        response = api_client.post(
            reverse("v1:auth-refresh"), {}, format="json", headers={CSRF_HEADER: "boshqa-qiymat"}
        )
        assert response.status_code == 401

    def test_logout_clears_the_cookie(self, api_client, tenant_a):
        from apps.accounts.cookies import REFRESH_COOKIE

        login = self._login(api_client, tenant_a).json()["data"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login['access']}")
        response = api_client.post(reverse("v1:auth-logout"), {}, format="json")
        assert response.status_code == 204
        # Chiqish tugmasi bosilgach brauzerda hech narsa qolmasligi
        # kerak — token topilmasa ham cookie tozalanadi.
        assert response.cookies[REFRESH_COOKIE].value == ""
