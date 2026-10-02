"""
Bog'cha logotipi (PLAN 4.6).

Mudira kun bo'yi O'Z bog'chasining belgisini ko'rib turishi kerak,
umumiy qalpoq ikonkasi emas. Logotip YUKLASH shart emas — bo'sh
bo'lsa ekran bosh harfni ko'rsatadi.
"""

from __future__ import annotations

import io

import pytest
from django.urls import reverse

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]


def _png() -> io.BytesIO:
    """Eng kichik haqiqiy PNG (1×1)."""
    import base64

    raw = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg=="
    )
    buffer = io.BytesIO(raw)
    buffer.name = "logo.png"
    return buffer


class TestLogoUpload:
    def test_the_kindergarten_can_upload_its_own_logo(self, tenant_a):
        client = tenant_a.client()
        response = client.put(reverse("v1:organization-logo"), {"logo": _png()}, format="multipart")
        assert response.status_code == 200
        assert response.json()["data"]["logo_url"]

    def test_an_oversized_file_is_refused_with_a_reason(self, tenant_a):
        big = io.BytesIO(b"x" * (2 * 1024 * 1024 + 1))
        big.name = "logo.png"
        response = tenant_a.client().put(
            reverse("v1:organization-logo"), {"logo": big}, format="multipart"
        )
        assert response.status_code == 422
        assert "2 MB" in response.json()["error"]["message"]

    def test_a_wrong_format_is_refused(self, tenant_a):
        document = io.BytesIO(b"not an image")
        document.name = "logo.pdf"
        response = tenant_a.client().put(
            reverse("v1:organization-logo"), {"logo": document}, format="multipart"
        )
        assert response.status_code == 422

    def test_nothing_sent_is_a_plain_error_not_a_crash(self, tenant_a):
        response = tenant_a.client().put(reverse("v1:organization-logo"), {}, format="multipart")
        assert response.status_code == 422

    def test_removing_the_logo_is_a_separate_deliberate_action(self, tenant_a):
        client = tenant_a.client()
        client.put(reverse("v1:organization-logo"), {"logo": _png()}, format="multipart")
        response = client.delete(reverse("v1:organization-logo"))
        assert response.status_code == 200
        assert response.json()["data"]["logo_url"] is None

    def test_a_patch_without_a_file_does_not_wipe_the_logo(self, tenant_a):
        """Logotip ALOHIDA endpointda — aynan shu sababdan."""
        client = tenant_a.client()
        client.put(reverse("v1:organization-logo"), {"logo": _png()}, format="multipart")
        client.patch(reverse("v1:organization"), {"name": "Yangi nom"}, format="json")
        response = client.get(reverse("v1:organization"))
        assert response.json()["data"]["logo_url"]
        assert response.json()["data"]["name"] == "Yangi nom"

    def test_a_cashier_cannot_change_the_brand(self, tenant_a):
        """Logotip — sozlama, kundalik operatsiya emas (docs/02 §11.2)."""
        from rest_framework.test import APIClient

        from apps.accounts.authentication import issue_token_pair
        from apps.accounts.models import User
        from apps.core.tenancy import organization_context

        with organization_context(tenant_a.organization.id):
            cashier = User.objects.create_user(
                email="kassir@alfa.uz",
                password="Juda-Kuchli-Parol-2026",  # noqa: S106 — test ma'lumoti
                full_name="Kassir",
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                role=tenant_a.role("cashier"),
            )
            tokens = issue_token_pair(cashier)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        response = client.put(reverse("v1:organization-logo"), {"logo": _png()}, format="multipart")
        assert response.status_code == 403
