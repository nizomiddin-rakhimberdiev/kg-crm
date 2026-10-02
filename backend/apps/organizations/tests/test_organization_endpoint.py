"""
Tashkilot profili endpointi (docs/04 §16).

Asosiy savol shu yerda ham bitta: mijoz faqat O'Z tashkilotini ko'radimi va
o'zgartira oladimi. Endpoint singleton bo'lgani uchun ID umuman qabul
qilinmaydi — bu eng ishonchli cross-tenant himoya, lekin uni ham tekshirib
qo'yamiz: token almashsa, javob ham almashishi kerak.
"""

from __future__ import annotations

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


class TestOrganizationProfile:
    def test_owner_reads_own_organization(self, tenant_a):
        response = tenant_a.client().get(reverse("v1:organization"))

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == tenant_a.organization.name
        assert data["slug"] == tenant_a.organization.slug

    def test_owner_can_edit_details(self, tenant_a):
        response = tenant_a.client().patch(
            reverse("v1:organization"),
            {
                "name": "Quyosh bogʻchasi",
                "legal_name": "Quyosh MCHJ",
                "tax_id": "305123456",
                "contact_phone": "+998901112233",
            },
            format="json",
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == "Quyosh bogʻchasi"
        assert data["tax_id"] == "305123456"

        # So'rov tugagach kontekst tozalanadi (P0-001) — o'qish uchun qayta ochamiz.
        from apps.core.tenancy import organization_context

        with organization_context(tenant_a.organization.id):
            tenant_a.organization.refresh_from_db()
            assert tenant_a.organization.name == "Quyosh bogʻchasi"

    def test_slug_is_immutable(self, tenant_a):
        """`slug` — global identifikator; nomni oʻzgartirish uni koʻchirmaydi."""
        original = tenant_a.organization.slug

        response = tenant_a.client().patch(
            reverse("v1:organization"),
            {"name": "Yangi nom", "slug": "yangi-slug"},
            format="json",
        )

        assert response.status_code == 200
        assert response.json()["data"]["slug"] == original

    @pytest.mark.tenancy
    def test_each_tenant_sees_only_itself(self, tenant_a, tenant_b):
        """
        URL bir xil, javob esa har xil: tashkilot ID'dan emas, TOKENDAN
        olinadi. Ya'ni boshqa tashkilotni so'rashning yo'li yo'q.
        """
        first = tenant_a.client().get(reverse("v1:organization")).json()["data"]
        second = tenant_b.client().get(reverse("v1:organization")).json()["data"]

        assert first["id"] != second["id"]
        assert first["name"] == tenant_a.organization.name
        assert second["name"] == tenant_b.organization.name

    def test_cashier_cannot_read_or_edit(self, tenant_a):
        """`settings` moduli kassirda yoʻq (docs/02 §11.2)."""
        from rest_framework.test import APIClient

        from apps.accounts.authentication import issue_token_pair
        from apps.accounts.models import User
        from apps.core.tenancy import organization_context

        with organization_context(tenant_a.organization.id):
            cashier = User.objects.create_user(
                email="kassir@alfa.uz",
                password="Juda-Kuchli-Parol-2026",  # noqa: S106
                full_name="Kassir",
                organization=tenant_a.organization,
                role=tenant_a.role("cashier"),
                branch=tenant_a.branch,
            )
            token = issue_token_pair(cashier)["access"]

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        assert client.get(reverse("v1:organization")).status_code == 403
        assert (
            client.patch(reverse("v1:organization"), {"name": "X"}, format="json").status_code
            == 403
        )
