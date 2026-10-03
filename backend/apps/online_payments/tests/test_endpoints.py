"""
Staff endpoints and the parent's public page (PLAN 6.1).

Tenant isolation: another kindergarten's invoice is 404, never 403, and
a link token from one kindergarten cannot be read through another.
"""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.accounts.authentication import issue_token_pair
from apps.accounts.models import User
from apps.core.tenancy import organization_context
from apps.online_payments.tests.conftest import make_invoice

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]


def _member_client(tenant, role_code: str) -> APIClient:
    with organization_context(tenant.organization.id):
        user = User.objects.create_user(
            email=f"{role_code}@{tenant.organization.slug}.uz",
            password=tenant.password,
            full_name=role_code,
            organization=tenant.organization,
            role=tenant.role(role_code),
            branch=tenant.branch,
        )
        tokens = issue_token_pair(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


def _create_link(client, invoice):
    return client.post("/api/v1/online-payments/links", {"invoice_id": str(invoice.id)})


class TestLinkCreation:
    def test_owner_gets_a_link(self, tenant_a, payme, invoice):
        response = _create_link(tenant_a.client(), invoice)
        assert response.status_code == 201
        assert "/pay/" in response.json()["data"]["url"]

    def test_asking_twice_reuses_the_link(self, tenant_a, payme, invoice):
        first = _create_link(tenant_a.client(), invoice).json()["data"]["url"]
        second = _create_link(tenant_a.client(), invoice).json()["data"]["url"]
        assert first == second

    def test_a_role_without_payments_create_is_forbidden(self, tenant_a, payme, invoice):
        response = _create_link(_member_client(tenant_a, "manager"), invoice)
        assert response.status_code == 403

    def test_another_kindergartens_invoice_is_404(self, tenant_a, tenant_b, payme):
        foreign = make_invoice(tenant_b)
        response = _create_link(tenant_a.client(), foreign)
        assert response.status_code == 404

    def test_without_a_connected_provider_it_is_a_business_error(self, tenant_a, invoice):
        response = _create_link(tenant_a.client(), invoice)
        assert response.status_code == 422


class TestPublicPage:
    def _token(self, tenant, invoice) -> str:
        url = _create_link(tenant.client(), invoice).json()["data"]["url"]
        return url.rsplit("/", 1)[1]

    def test_parent_sees_the_invoice_and_payme_button(self, api_client, tenant_a, payme, invoice):
        token = self._token(tenant_a, invoice)
        response = api_client.get(f"/api/v1/public/pay/link/{token}")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["child"] == "Ali V."
        assert data["payable"] == "1500000.00"
        assert data["providers"]["payme"].startswith("https://checkout.paycom.uz/")
        assert "click" not in data["providers"]

    def test_a_made_up_token_is_404(self, api_client, tenant_a):
        assert api_client.get("/api/v1/public/pay/link/nonsense").status_code == 404

    def test_a_token_rewritten_to_another_org_is_404(self, api_client, tenant_a, tenant_b, payme):
        """The org is embedded in the token — swapping it lands in a tenant with no such link."""
        import base64

        token = self._token(tenant_a, make_invoice(tenant_a, "1000"))
        raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
        forged = base64.urlsafe_b64encode(tenant_b.organization.id.bytes + raw[16:])
        response = api_client.get(f"/api/v1/public/pay/link/{forged.decode().rstrip('=')}")
        assert response.status_code == 404


class TestCredentials:
    def test_owner_saves_and_lists_without_the_secret(self, tenant_a):
        client = tenant_a.client()
        saved = client.put(
            "/api/v1/online-payments/credentials/payme",
            {"merchant_id": "abc", "secret": "very-secret-9876"},
            format="json",
        )
        assert saved.status_code == 200
        listed = client.get("/api/v1/online-payments/credentials").json()["data"]
        payme = next(row for row in listed if row["provider"] == "payme")
        assert payme["configured"] is True
        assert payme["secret_hint"] == "9876"
        assert "very-secret" not in str(listed)
        assert str(tenant_a.organization.id) in payme["webhook_url"]

    def test_click_needs_a_service_id(self, tenant_a):
        response = tenant_a.client().put(
            "/api/v1/online-payments/credentials/click",
            {"merchant_id": "abc", "secret": "k"},
            format="json",
        )
        assert response.status_code == 400

    def test_a_director_cannot_change_keys(self, tenant_a):
        response = _member_client(tenant_a, "director").put(
            "/api/v1/online-payments/credentials/payme",
            {"merchant_id": "abc", "secret": "k"},
            format="json",
        )
        assert response.status_code == 403

    def test_keys_are_per_kindergarten(self, tenant_a, tenant_b, payme):
        listed = tenant_b.client().get("/api/v1/online-payments/credentials").json()["data"]
        assert all(row["configured"] is False for row in listed)

    def test_switching_off(self, tenant_a, payme):
        client = tenant_a.client()
        assert client.delete("/api/v1/online-payments/credentials/payme").status_code == 204
        listed = client.get("/api/v1/online-payments/credentials").json()["data"]
        assert all(row["configured"] is False for row in listed)
