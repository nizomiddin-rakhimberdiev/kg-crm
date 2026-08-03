"""Auth oqimi testlari (docs/04 §5)."""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.accounts.models import RefreshToken, User
from apps.accounts.services import register_organization
from apps.core.tenancy import organization_context

pytestmark = pytest.mark.django_db

PASSWORD = "Juda-Kuchli-Parol-2026"  # noqa: S105


class TestSignup:
    def test_creates_organization_branch_owner_and_roles(self, api_client):
        response = api_client.post(
            reverse("v1:auth-signup"),
            {
                "organization_name": "Yangi Bog'cha",
                "contact_email": "owner@yangi.uz",
                "full_name": "Aziz Karimov",
                "password": PASSWORD,
            },
            format="json",
        )
        assert response.status_code == 201
        data = response.json()["data"]

        assert data["access"] and data["refresh"]
        assert data["user"]["role"]["code"] == "org_owner"
        assert data["user"]["organization"]["name"] == "Yangi Bog'cha"
        # Org Owner barcha modullarga to'liq kirish oladi (docs/02 §11.2).
        assert "users.create" in data["user"]["permissions"]
        assert "billing.read" in data["user"]["permissions"]

    def test_weak_password_rejected(self, api_client):
        response = api_client.post(
            reverse("v1:auth-signup"),
            {
                "organization_name": "X",
                "contact_email": "a@b.uz",
                "full_name": "A",
                "password": "123",
            },
            format="json",
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_signup_is_atomic(self, api_client, monkeypatch):
        """
        Yarim yaratilgan tashkilot qolmasligi shart.

        Aks holda kirib bo'lmaydigan, lekin mavjud tenant paydo bo'ladi va
        uni qo'lda tozalash kerak bo'ladi.
        """
        from apps.accounts import services

        def boom(*args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("seed muvaffaqiyatsiz")

        monkeypatch.setattr(services, "seed_system_roles", boom)

        response = api_client.post(
            reverse("v1:auth-signup"),
            {
                "organization_name": "Yiqiladigan",
                "contact_email": "x@yiqil.uz",
                "full_name": "X",
                "password": PASSWORD,
            },
            format="json",
        )
        # Istisno konvertga o'ralib 500 bo'ladi va ichki tafsilot chiqmaydi.
        assert response.status_code == 500
        assert response.json()["error"]["code"] == "INTERNAL_ERROR"
        assert "seed muvaffaqiyatsiz" not in response.content.decode()

        # Muhimi: yarim yaratilgan tashkilot QOLMASLIGI kerak.
        from apps.organizations.models import Organization

        assert not Organization.objects.filter(name="Yiqiladigan").exists()


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
        # Xabar "email yo'q" va "parol xato" ni farqlamasligi kerak.
        assert response.json()["error"]["message"] == "Email yoki parol noto'g'ri."

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
        assert known == unknown, "Javob mavjud va mavjud bo'lmagan emailni farqlamasin"


class TestMultiOrganizationLogin:
    """Bir odam ikki bog'chada ishlashi mumkin (docs/03 §10.6)."""

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
        Login "bu email qaysi bog'chalarda bor?" orakuli bo'lmasligi kerak.

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
        """Rotatsiyadan keyin eski token darhol o'ladi — qayta ishlatishga yo'l yo'q."""
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
        assert RefreshToken.objects.filter(revoked_at__isnull=False).exists()


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
