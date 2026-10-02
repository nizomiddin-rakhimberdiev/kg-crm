"""
Billing API va yozish darvozasi testlari (docs/04 §18, docs/03 §20.6).

`/billing/*` sweep'dan tashqarida, chunki endpointlar umuman ID qabul
qilmaydi — obuna tokendan aniqlanadi. Shuning uchun izolyatsiya shu
yerda qo'lda tekshiriladi.

Ikkinchi mavzu — `402` darvozasi. U **global** ruxsat sifatida ulangan,
ya'ni bitta joyda ishlaydi; lekin aynan shuning uchun uning qamrovi
keng va xatosi ham keng ta'sir qiladi.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.subscriptions import services
from apps.subscriptions.models import (
    Subscription,
    SubscriptionInvoice,
    SubscriptionStatus,
)

pytestmark = pytest.mark.django_db


def _subscription(tenant) -> Subscription:
    with organization_context(tenant.organization.id):
        return Subscription.objects.get(organization=tenant.organization)


def _suspend(tenant) -> None:
    with organization_context(tenant.organization.id):
        Subscription.objects.filter(organization=tenant.organization).update(
            status=SubscriptionStatus.SUSPENDED
        )


class TestSubscriptionEndpoint:
    def test_returns_the_callers_own_subscription(self, tenant_a):
        response = tenant_a.client().get(reverse("v1:billing-subscription"))
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "trialing"
        assert data["plan_code"] == "standard"
        assert data["included_children"] == 50
        assert data["base_price"] == "400000.00"

    def test_usage_is_marked_as_a_projection(self, tenant_a):
        """
        `is_projection: true` bezak emas.

        U raqam hali OLINMAGANINI bildiradi. Haqiqiy hisob doim yopilgan
        dalildan chiqadi — bu farq "kutilmagan hisob yoʻq" va'dasining
        texnik asosi (docs/04 §18).
        """
        response = tenant_a.client().get(reverse("v1:billing-usage"))
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["is_projection"] is True
        assert data["billable_children"] == 50
        assert data["projected"]["total_amount"] == "400000.00"

    def test_usage_reflects_actual_children(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            for index in range(73):
                Child.objects.create(
                    organization=tenant_a.organization,
                    branch=tenant_a.branch,
                    first_name=f"Bola{index}",
                    last_name="Testov",
                    date_of_birth=date(2021, 3, 14),
                    gender="male",
                )

        data = tenant_a.client().get(reverse("v1:billing-usage")).json()["data"]
        assert data["billable_children"] == 73
        assert data["overage_steps"] == 3
        assert data["projected"]["total_amount"] == "550000.00"


class TestConversionEndpoint:
    def test_accept_trial_issues_an_invoice(self, tenant_a):
        response = tenant_a.client().post(
            reverse("v1:billing-accept-trial"), {"payment_term": "annual"}, format="json"
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["total_amount"] == "3600000.00"
        assert data["status"] == "issued"

    def test_invoice_list_and_detail(self, tenant_a):
        client = tenant_a.client()
        invoice_id = client.post(reverse("v1:billing-accept-trial"), {}, format="json").json()[
            "data"
        ]["id"]

        listed = client.get(reverse("v1:billing-invoices")).json()["data"]
        assert len(listed) == 1

        detail = client.get(f"/api/v1/billing/invoices/{invoice_id}").json()["data"]
        assert detail["number"].startswith("KG-")
        assert detail["amount_paid"] == "0.00"

    def test_usage_history_shows_the_evidence(self, tenant_a):
        client = tenant_a.client()
        client.post(reverse("v1:billing-accept-trial"), {}, format="json")
        rows = client.get(reverse("v1:billing-usage-history")).json()["data"]
        assert len(rows) == 1
        assert rows[0]["closed_at"] is not None
        assert rows[0]["measurement_method"] == "daily_peak"


class TestIsolation:
    @pytest.mark.tenancy
    def test_another_organizations_invoice_is_404(self, tenant_a, tenant_b):
        foreign_id = (
            tenant_b.client()
            .post(reverse("v1:billing-accept-trial"), {}, format="json")
            .json()["data"]["id"]
        )
        response = tenant_a.client().get(f"/api/v1/billing/invoices/{foreign_id}")
        assert response.status_code == 404

    @pytest.mark.tenancy
    def test_invoice_list_never_crosses_organizations(self, tenant_a, tenant_b):
        tenant_b.client().post(reverse("v1:billing-accept-trial"), {}, format="json")
        assert tenant_a.client().get(reverse("v1:billing-invoices")).json()["data"] == []

    def test_billing_requires_authentication(self, api_client):
        assert api_client.get(reverse("v1:billing-subscription")).status_code == 401

    def test_only_the_owner_sees_billing(self, tenant_a):
        """`billing` faqat Org Ownerʼda (docs/02 §11.2)."""
        from rest_framework.test import APIClient

        from apps.accounts.authentication import issue_token_pair
        from apps.accounts.models import User

        with organization_context(tenant_a.organization.id):
            director = User.objects.create_user(
                email="direktor-billing@alfa.uz",
                password="Juda-Kuchli-Parol-2026",  # noqa: S106
                full_name="Direktor",
                organization=tenant_a.organization,
                role=tenant_a.role("director"),
                branch=tenant_a.branch,
            )
            tokens = issue_token_pair(director)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        assert client.get(reverse("v1:billing-subscription")).status_code == 403


class TestWriteGate:
    """
    To'lanmagan obunada yozish `402` beradi — o'qish esa ishlaydi.

    Bu farq shu sprintdagi eng muhim mahsulot qarori: ma'lumot hech
    qachon o'chirilmaydi va yashirilmaydi (docs/03 §20.6).
    """

    def test_reads_still_work_when_suspended(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            Child.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                first_name="Ali",
                last_name="Valiyev",
                date_of_birth=date(2021, 3, 14),
                gender="male",
            )
        _suspend(tenant_a)

        response = tenant_a.client().get(reverse("v1:child-list"))
        assert response.status_code == 200
        assert len(response.json()["data"]) == 1

    def test_writes_are_blocked_with_402(self, tenant_a):
        _suspend(tenant_a)
        response = tenant_a.client().post(
            reverse("v1:child-list"),
            {
                "first_name": "Yangi",
                "last_name": "Bola",
                "date_of_birth": "2021-03-14",
                "gender": "male",
            },
            format="json",
        )
        assert response.status_code == 402
        assert response.json()["error"]["code"] == "SUBSCRIPTION_INACTIVE"

    def test_402_not_403(self, tenant_a):
        """
        `403` EMAS, `402`.

        `403` "sizga ruxsat yoʻq" degani — ya'ni ROL muammosi, va
        foydalanuvchi uni tuzata olmaydi. Bu yerda rol joyida: hisob
        to'lanmagan, va buni tuzatish mumkin. Kod farqi frontendga
        to'g'ri xabar ko'rsatish imkonini beradi.
        """
        _suspend(tenant_a)
        response = tenant_a.client().post(reverse("v1:tariff-list"), {"name": "X", "amount": "1"})
        assert response.status_code == 402

    def test_payments_are_blocked_too(self, tenant_a):
        """Pul qabul qilish ham yozish — u ham toʻxtaydi."""
        _suspend(tenant_a)
        response = tenant_a.client().post(
            reverse("v1:payment-list"),
            {"child_id": "00000000-0000-0000-0000-000000000000", "amount": "1", "method": "cash"},
            format="json",
        )
        assert response.status_code == 402

    def test_billing_endpoints_still_work_when_suspended(self, tenant_a):
        """
        Hisobni ko'rish va to'lash YO'LI ochiq qolishi shart.

        Aks holda to'xtatilgan mijoz to'lamoqchi bo'lsa ham to'lay
        olmasdi — bu o'z-o'ziga qarshi ishlaydigan darvoza bo'lardi.
        """
        _suspend(tenant_a)
        assert tenant_a.client().get(reverse("v1:billing-subscription")).status_code == 200
        assert tenant_a.client().get(reverse("v1:billing-invoices")).status_code == 200

    def test_export_still_works_when_suspended(self, tenant_a):
        """
        Eksport ishlaydi — hatto to'xtatilgan holatda ham.

        Mijozning o'z operatsion ma'lumoti hech qachon hisob-kitob
        bahsining garovi bo'lmasligi kerak (docs/04 §18).
        """
        _suspend(tenant_a)
        response = tenant_a.client().post("/api/v1/reports/revenue/export", {}, format="json")
        assert response.status_code == 202

    def test_trialing_and_pending_payment_can_write(self, tenant_a):
        for status_value in (
            SubscriptionStatus.TRIALING,
            SubscriptionStatus.PENDING_PAYMENT,
            SubscriptionStatus.PAST_DUE,
        ):
            with organization_context(tenant_a.organization.id):
                Subscription.objects.filter(organization=tenant_a.organization).update(
                    status=status_value
                )
            response = tenant_a.client().post(
                reverse("v1:tariff-list"),
                {"name": f"Tarif-{status_value}", "amount": "1000000"},
                format="json",
            )
            assert response.status_code == 201, f"{status_value} holatida yozish bloklandi"


class TestPaymentTermChange:
    def test_term_change_updates_the_discount(self, tenant_a):
        response = tenant_a.client().post(
            reverse("v1:billing-payment-term"), {"payment_term": "annual"}, format="json"
        )
        assert response.status_code == 200
        assert response.json()["data"]["discount_percent"] == "25.00"

    def test_unknown_term_is_rejected(self, tenant_a):
        response = tenant_a.client().post(
            reverse("v1:billing-payment-term"), {"payment_term": "haftalik"}, format="json"
        )
        assert response.status_code == 400


class TestInvoiceImmutability:
    def test_amounts_are_frozen_on_the_invoice(self, tenant_a):
        """
        Hisob-faktura summalari NUSXA — plandan qayta o'qilmaydi.

        Hujjat uch yildan keyin ham aynan shunday ko'rinishi kerak,
        hatto plan versiyasi o'zgargan bo'lsa ham. Eski hisobni bugungi
        ma'lumotdan qayta hisoblash — xato, imkoniyat emas
        (docs/03 §20.4).
        """
        with organization_context(tenant_a.organization.id):
            invoice = services.accept_trial(subscription=_subscription(tenant_a))
            plan = invoice.subscription.plan
            plan.base_price = Decimal("999999.00")
            plan.save(update_fields=["base_price"])

            invoice.refresh_from_db()

        assert invoice.base_amount == Decimal("400000.00")
        assert invoice.total_amount == Decimal("400000.00")

    def test_invoice_arithmetic_is_enforced_by_the_database(self, tenant_a):
        """Yigʻindisi mos kelmaydigan hisob umuman yozilmasin."""
        from django.db import IntegrityError, transaction

        with organization_context(tenant_a.organization.id):
            invoice = services.accept_trial(subscription=_subscription(tenant_a))
            with pytest.raises(IntegrityError), transaction.atomic():
                SubscriptionInvoice.objects.filter(pk=invoice.pk).update(
                    total_amount=Decimal("1.00")
                )


class TestPastDueKeepsAccess:
    def test_past_due_customer_can_still_work(self, tenant_a):
        """
        `past_due` — hali TO'LIQ kirish.

        Hisob muddati o'tgan, lekin bank o'tkazmasi yo'lda bo'lishi
        mumkin. Darrov to'xtatish o'z pulini yuborayotgan mijozni
        ishdan chiqarardi (docs/03 §20.6).
        """
        with organization_context(tenant_a.organization.id):
            invoice = services.accept_trial(subscription=_subscription(tenant_a))
            SubscriptionInvoice.objects.filter(pk=invoice.pk).update(
                issued_at=timezone.localdate() - timedelta(days=10),
                due_at=timezone.localdate() - timedelta(days=3),
            )
            services.mark_past_due()

        response = tenant_a.client().post(
            reverse("v1:tariff-list"), {"name": "Hali ishlaydi", "amount": "1"}, format="json"
        )
        assert response.status_code == 201
