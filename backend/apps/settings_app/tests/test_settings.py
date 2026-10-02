"""Sozlamalarni aniqlash testlari (docs/03 §18.1)."""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.core.tenancy import organization_context
from apps.settings_app import services

pytestmark = pytest.mark.django_db


class TestResolution:
    def test_falls_back_to_code_default(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            assert services.get_setting(key="finance.due_day") == 10

    def test_organization_value_overrides_default(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            services.set_setting(
                organization=tenant_a.organization, key="finance.due_day", value=15
            )
            assert services.get_setting(key="finance.due_day") == 15

    def test_branch_value_overrides_organization(self, tenant_a):
        """Filialga xos qiymat global qiymatni qoplaydi."""
        with organization_context(tenant_a.organization.id):
            services.set_setting(
                organization=tenant_a.organization, key="finance.due_day", value=15
            )
            services.set_setting(
                organization=tenant_a.organization,
                key="finance.due_day",
                value=20,
                branch=tenant_a.branch,
            )
            assert services.get_setting(key="finance.due_day") == 15
            assert services.get_setting(key="finance.due_day", branch=tenant_a.branch) == 20

    def test_effective_settings_include_untouched_defaults(self, tenant_a):
        """
        Ro'yxat barcha sozlamalarni ko'rsatadi, faqat o'zgartirilganini emas.

        Aks holda foydalanuvchi "bunday sozlama umuman bormi?" degan
        savolga javob izlab yurardi.
        """
        with organization_context(tenant_a.organization.id):
            resolved = services.effective_settings()
        assert set(services.DEFAULTS) <= set(resolved)

    def test_value_can_be_any_json_shape(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            services.set_setting(
                organization=tenant_a.organization,
                key="notifications.quiet_hours",
                value={"from": "21:00", "to": "08:00"},
            )
            assert services.get_setting(key="notifications.quiet_hours")["from"] == "21:00"


class TestEndpoints:
    def test_list_returns_effective_values(self, tenant_a):
        response = tenant_a.client().get(reverse("v1:setting-list"))
        assert response.status_code == 200
        assert "finance.due_day" in response.json()["data"]

    def test_put_sets_a_value(self, tenant_a):
        client = tenant_a.client()
        response = client.put(
            reverse("v1:setting-detail", args=["finance.due_day"]),
            {"value": 25},
            format="json",
        )
        assert response.status_code == 200
        assert client.get(reverse("v1:setting-list")).json()["data"]["finance.due_day"] == 25

    def test_unknown_key_is_rejected(self, tenant_a):
        response = tenant_a.client().get(reverse("v1:setting-detail", args=["mavjud.emas"]))
        assert response.status_code == 422

    @pytest.mark.tenancy
    def test_settings_never_cross_tenants(self, tenant_a, tenant_b):
        tenant_a.client().put(
            reverse("v1:setting-detail", args=["finance.due_day"]), {"value": 25}, format="json"
        )
        other = tenant_b.client().get(reverse("v1:setting-list")).json()["data"]
        assert other["finance.due_day"] == 10  # koddagi default

    def test_director_can_read_but_not_write(self, tenant_a):
        """Direktorda `settings` faqat oʻqish (docs/02 §11.2)."""
        from rest_framework.test import APIClient

        from apps.accounts.authentication import issue_token_pair
        from apps.accounts.models import User

        with organization_context(tenant_a.organization.id):
            director = User.objects.create_user(
                email="direktor@alfa.uz",
                password="Juda-Kuchli-Parol-2026",  # noqa: S106
                full_name="Direktor",
                organization=tenant_a.organization,
                role=tenant_a.role("director"),
                branch=tenant_a.branch,
            )
            tokens = issue_token_pair(director)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        assert client.get(reverse("v1:setting-list")).status_code == 200
        assert (
            client.put(
                reverse("v1:setting-detail", args=["finance.due_day"]), {"value": 1}, format="json"
            ).status_code
            == 403
        )
