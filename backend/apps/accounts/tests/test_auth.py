"""Auth oqimi testlari (docs/04 §5)."""

from __future__ import annotations

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


class TestLogin:
    def test_single_organization_returns_tokens(self, api_client, tenant_a):
        response = api_client.post(
            reverse("v1:auth-login"),
            {"email": tenant_a.owner.email, "password": PASSWORD},
            format="json",
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["access"] and data["refresh"]
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
        ).json()["data"]

        response = api_client.post(
            reverse("v1:auth-refresh"), {"refresh": login["refresh"]}, format="json"
        )
        assert response.status_code == 200
        assert response.json()["data"]["refresh"] != login["refresh"]

    def test_old_refresh_token_stops_working(self, api_client, tenant_a):
        """Rotatsiyadan keyin eski token darhol oʻladi — qayta ishlatishga yoʻl yoʻq."""
        login = api_client.post(
            reverse("v1:auth-login"),
            {"email": tenant_a.owner.email, "password": PASSWORD},
            format="json",
        ).json()["data"]
        api_client.post(reverse("v1:auth-refresh"), {"refresh": login["refresh"]}, format="json")

        again = api_client.post(
            reverse("v1:auth-refresh"), {"refresh": login["refresh"]}, format="json"
        )
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
        return response.json()["data"]["refresh"]

    def test_reusing_a_rotated_token_closes_every_session(self, api_client, tenant_a):
        """
        Eski tokenni qayta ishlatish BARCHA sessiyalarni yopadi.

        Faqat rad etish yetarli emasdi: o'g'ri allaqachon yangi token
        olgan bo'lardi va u ishlayverardi — ya'ni haqiqiy foydalanuvchi
        bloklanib, o'g'ri qolardi.
        """
        first = self._login(api_client, tenant_a)

        # Normal yangilash — `first` bekor qilinadi, `second` beriladi.
        rotated = api_client.post(reverse("v1:auth-refresh"), {"refresh": first}, format="json")
        assert rotated.status_code == 200
        second = rotated.json()["data"]["refresh"]

        # Yangi token hozircha ishlaydi.
        assert (
            api_client.post(
                reverse("v1:auth-refresh"), {"refresh": second}, format="json"
            ).status_code
            == 200
        )

        # ESKI tokenni qayta ishlatish — o'g'irlik belgisi.
        replay = api_client.post(reverse("v1:auth-refresh"), {"refresh": first}, format="json")
        assert replay.status_code == 401

        # Endi barcha sessiyalar yopilgan bo'lishi kerak.
        with organization_context(tenant_a.organization.id):
            assert not RefreshToken.objects.filter(
                user=tenant_a.owner, revoked_at__isnull=True
            ).exists(), "ochiq sessiya qoldi — oʻgʻri hamon kira oladi"

    def test_the_thiefs_fresh_token_stops_working_too(self, api_client, tenant_a):
        """Eng muhimi: oʻgʻri olgan YANGI token ham oʻladi."""
        first = self._login(api_client, tenant_a)
        stolen_new = api_client.post(
            reverse("v1:auth-refresh"), {"refresh": first}, format="json"
        ).json()["data"]["refresh"]

        # Haqiqiy foydalanuvchi eski tokenini ishlatadi → oila yopiladi.
        api_client.post(reverse("v1:auth-refresh"), {"refresh": first}, format="json")

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
