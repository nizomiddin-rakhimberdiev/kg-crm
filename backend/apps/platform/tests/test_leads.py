"""Public lead intake: tenantlar bilan aralashmaydigan, cheklangan oqim."""

from __future__ import annotations

import uuid

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.tenancy import platform_context
from apps.platform.authentication import issue_platform_token
from apps.platform.models import Lead, PlatformRole, PlatformUser
from apps.platform.totp import generate_secret

pytestmark = pytest.mark.django_db

URL = "/api/v1/public/leads"


def payload(**overrides):
    body = {
        "name": "Dilshod Karimov",
        "phone": "90 123 45 67",
        "kindergarten_name": "Mehrjon bog'chasi",
        "children_count": 60,
        "city": "Toshkent",
        "message": "Demo olishni xohlaymiz.",
        "language": "uz",
        "consent": True,
        "privacy_policy_version": "2026-09",
        "submission_id": str(uuid.uuid4()),
    }
    body.update(overrides)
    return body


def platform_admin() -> PlatformUser:
    with platform_context():
        return PlatformUser.objects.create(
            email="platform-leads@radix-crm.uz",
            full_name="Platform Admin",
            password="not-used",  # Token testi; password flow alohida sinalgan.
            role=PlatformRole.ADMIN,
            totp_secret=generate_secret(),
            totp_confirmed_at=timezone.now(),
        )


class TestPublicLeadCreate:
    def test_creates_a_platform_lead_and_normalizes_phone(self):
        response = APIClient().post(URL, payload(), format="json")
        assert response.status_code == 201
        lead = Lead.objects.get(pk=response.json()["data"]["id"])
        assert lead.phone == "+998901234567"
        assert lead.language == "uz"
        assert lead.consented_at is not None

    def test_consent_is_required_server_side(self):
        response = APIClient().post(URL, payload(consent=False), format="json")
        assert response.status_code == 400
        assert Lead.objects.count() == 0

    def test_invalid_phone_is_rejected(self):
        response = APIClient().post(URL, payload(phone="12345"), format="json")
        assert response.status_code == 400
        assert Lead.objects.count() == 0

    def test_same_submission_is_idempotent(self):
        body = payload()
        first = APIClient().post(URL, body, format="json")
        second = APIClient().post(URL, body, format="json")
        assert first.status_code == 201
        assert second.status_code == 200
        assert Lead.objects.count() == 1

    def test_rate_limit_applies(self, monkeypatch):
        """
        `override_settings` bu yerda ISHLAMAYDI.

        DRF `THROTTLE_RATES` ni klass atributi sifatida import paytida
        o'qiydi (`apps/accounts/tests/test_throttling.py` da hujjatlangan
        naqsh), ya'ni sozlamani `override_settings` bilan almashtirish
        klassning o'ziga ta'sir qilmaydi. To'g'ri yo'l — klass atributini
        bevosita monkeypatch qilish. Buning oldingi ko'rinishi (`override_
        settings`) test yashil bo'lib qolgan holda rate limitni umuman
        tekshirmasdi — 429 o'rniga 200 qaytardi.
        """
        from rest_framework.throttling import SimpleRateThrottle

        monkeypatch.setattr(SimpleRateThrottle, "THROTTLE_RATES", {"lead": "1/hour"})

        client = APIClient()
        assert client.post(URL, payload(), format="json").status_code == 201
        assert client.post(URL, payload(), format="json").status_code == 429


class TestLeadAccess:
    def test_tenant_user_cannot_list_leads(self, tenant_a):
        response = tenant_a.client().get("/api/v1/platform/leads")
        assert response.status_code == 401

    def test_platform_admin_can_list_leads(self):
        APIClient().post(URL, payload(), format="json")
        admin = platform_admin()
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {issue_platform_token(admin)}")
        response = client.get("/api/v1/platform/leads")
        assert response.status_code == 200
        assert response.json()["data"][0]["kindergarten_name"] == "Mehrjon bog'chasi"

    def test_anonymous_user_cannot_list_leads(self):
        assert APIClient().get("/api/v1/platform/leads").status_code == 401


class TestPublicPricing:
    @pytest.mark.parametrize(
        ("children", "monthly", "annual", "saving"),
        [
            (50, "400000.00", "3600000.00", "1200000.00"),
            (60, "450000.00", "4050000.00", "1350000.00"),
            (70, "500000.00", "4500000.00", "1500000.00"),
            (80, "550000.00", "4950000.00", "1650000.00"),
            (51, "450000.00", "4050000.00", "1350000.00"),
            (69, "500000.00", "4500000.00", "1500000.00"),
        ],
    )
    def test_uses_the_current_versioned_subscription_formula(
        self, children, monthly, annual, saving
    ):
        response = APIClient().get(f"/api/v1/public/pricing?children={children}")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["monthly"]["total_amount"] == monthly
        assert data["annual"]["total_amount"] == annual
        assert data["annual_saving"] == saving
