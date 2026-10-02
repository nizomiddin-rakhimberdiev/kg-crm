"""
Platforma konsoli — PLAN 5.12.

* reja va to'lov davrini o'zgartirish: faqat administrator, sabab
  majburiy, mijozning audit jurnaliga tushadi, boshqa tashkilotga
  ta'sir qilmaydi;
* "Taxminiy oylik" — mijoz o'z ekranida ko'radigan AYNAN o'sha raqam;
* kirish ruxsatlari tarixi — tugaganlari bilan;
* faollik — sonlar, qatorlar emas.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.core.tenancy import organization_context, platform_context
from apps.platform.models import PlatformRole, SupportGrant
from apps.platform.tests.test_platform_console import _client, _platform_user

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]


def _url(tenant, tail: str) -> str:
    return f"/api/v1/platform/organizations/{tenant.organization.id}/{tail}"


def _subscription(tenant):
    from apps.subscriptions.models import Subscription

    with organization_context(tenant.organization.id):
        return Subscription.objects.get(organization=tenant.organization)


class TestPaymentTerm:
    def test_admin_changes_it_with_a_reason_and_it_is_logged(self, tenant_a):
        response = _client(_platform_user()).post(
            _url(tenant_a, "payment-term"),
            {"payment_term": "annual", "reason": "Mijoz yillik toʻlashni soʻradi"},
            format="json",
        )
        assert response.status_code == 200
        subscription = _subscription(tenant_a)
        assert subscription.payment_term == "annual"
        assert subscription.discount_percent == Decimal("25")

        # Mijoz o'z jurnalida ko'radi: vendor nima o'zgartirgani va nega.
        rows = tenant_a.client().get("/api/v1/audit-logs/platform-access").json()["data"]
        assert any(
            row["changes"].get("payment_term") == {"from": "monthly", "to": "annual"}
            for row in rows
        )

    def test_a_reason_is_required(self, tenant_a):
        response = _client(_platform_user()).post(
            _url(tenant_a, "payment-term"), {"payment_term": "annual"}, format="json"
        )
        assert response.status_code == 400

    def test_support_staff_cannot_change_it(self, tenant_a):
        support = _platform_user(role=PlatformRole.SUPPORT, email="support@kg-crm.uz")
        response = _client(support).post(
            _url(tenant_a, "payment-term"),
            {"payment_term": "annual", "reason": "Test"},
            format="json",
        )
        assert response.status_code == 422
        assert _subscription(tenant_a).payment_term == "monthly"

    def test_the_other_organization_is_untouched(self, tenant_a, tenant_b):
        _client(_platform_user()).post(
            _url(tenant_a, "payment-term"),
            {"payment_term": "semiannual", "reason": "Kelishuv"},
            format="json",
        )
        assert _subscription(tenant_b).payment_term == "monthly"

    def test_a_customer_token_cannot_reach_it(self, tenant_a):
        """Mijoz tokeni vendor tekisligiga umuman kira olmaydi (ADR-10)."""
        response = tenant_a.client().post(
            _url(tenant_a, "payment-term"),
            {"payment_term": "annual", "reason": "x"},
            format="json",
        )
        assert response.status_code in (401, 403)
        assert _subscription(tenant_a).payment_term == "monthly"


class TestPlan:
    def test_admin_switches_to_the_current_version_of_another_plan(self, tenant_a):
        from apps.subscriptions.models import SubscriptionPlan

        with platform_context():
            SubscriptionPlan.objects.create(
                code="premium",
                name="Premium",
                base_price=Decimal("600000"),
                included_children=50,
                overage_step_children=10,
                overage_step_price=Decimal("50000"),
                valid_from=timezone.localdate() - timedelta(days=1),
            )
        response = _client(_platform_user()).post(
            _url(tenant_a, "plan"), {"plan_code": "premium", "reason": "Kelishuv"}, format="json"
        )
        assert response.status_code == 200
        assert _subscription(tenant_a).plan.code == "premium"

    def test_an_unknown_plan_is_refused(self, tenant_a):
        response = _client(_platform_user()).post(
            _url(tenant_a, "plan"), {"plan_code": "yoq", "reason": "x x"}, format="json"
        )
        assert response.status_code == 422


class TestDetail:
    def test_the_projection_is_the_number_the_customer_sees(self, tenant_a):
        vendor = (
            _client(_platform_user())
            .get(f"/api/v1/platform/organizations/{tenant_a.organization.id}")
            .json()["data"]["projection"]
        )
        customer = tenant_a.client().get("/api/v1/billing/usage").json()["data"]
        assert vendor["projected"]["total_amount"] == customer["projected"]["total_amount"]
        assert vendor["is_projection"] is True

    def test_grant_history_keeps_expired_and_revoked_grants(self, tenant_a):
        admin = _platform_user()
        now = timezone.now()
        with platform_context():
            SupportGrant.objects.create(
                organization=tenant_a.organization,
                platform_user=admin,
                reason="Eski yordam",
                expires_at=now - timedelta(days=3),
            )
            SupportGrant.objects.create(
                organization=tenant_a.organization,
                platform_user=admin,
                reason="Bekor qilingan",
                expires_at=now + timedelta(hours=1),
                revoked_at=now,
            )
        grants = (
            _client(admin)
            .get(f"/api/v1/platform/organizations/{tenant_a.organization.id}")
            .json()["data"]["grants"]
        )
        reasons = {g["reason"]: g for g in grants}
        assert reasons["Eski yordam"]["is_active"] is False
        assert reasons["Bekor qilingan"]["revoked_at"] is not None

    def test_activity_counts_sign_ins(self, tenant_a, api_client):
        api_client.post(
            "/api/v1/auth/login",
            {"email": tenant_a.owner.email, "password": tenant_a.password},
            format="json",
        )
        activity = (
            _client(_platform_user())
            .get(f"/api/v1/platform/organizations/{tenant_a.organization.id}")
            .json()["data"]["activity"]
        )
        assert activity["active_users_30d"] == 1
        assert activity["last_activity_at"] is not None
