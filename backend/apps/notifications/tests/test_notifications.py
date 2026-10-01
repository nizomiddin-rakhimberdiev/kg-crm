"""
Bildirishnoma testlari (docs/03 §17, docs/04 §15).

Asosiy savol: "xabar yuborilmagani jimgina yo'qolib keta oladimi?" —
"SMS kelmadi" degan shikoyatga javob jurnalda bo'lishi kerak.
"""

from __future__ import annotations

from datetime import date, time
from decimal import Decimal

import pytest
from django.test import override_settings
from django.urls import reverse

from apps.children.models import Child, Guardian
from apps.children.services import attach_guardian
from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context
from apps.notifications import services
from apps.notifications.models import Notification, NotificationStatus, NotificationTemplate

pytestmark = pytest.mark.django_db


@pytest.fixture
def guardian(tenant_a) -> Guardian:
    with organization_context(tenant_a.organization.id):
        return Guardian.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Nodira",
            last_name="Valiyeva",
            phone="+998901112233",
        )


@pytest.fixture
def child_with_guardian(tenant_a, guardian) -> Child:
    with organization_context(tenant_a.organization.id):
        child = Child.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Ali",
            last_name="Valiyev",
            date_of_birth=date(2021, 3, 14),
            gender="male",
        )
        attach_guardian(child=child, guardian=guardian, relation="mother", is_primary=True)
        return child


class TestTemplates:
    def test_seeded_on_signup(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            codes = set(NotificationTemplate.objects.values_list("code", flat=True))
        assert {"payment_received", "debt_reminder", "absence_notice"} <= codes

    def test_seeding_is_idempotent(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            before = NotificationTemplate.objects.count()
            services.seed_default_templates(tenant_a.organization)
            assert NotificationTemplate.objects.count() == before

    def test_branch_template_overrides_global(self, tenant_a, guardian):
        with organization_context(tenant_a.organization.id):
            NotificationTemplate.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                code="debt_reminder",
                channel="sms",
                body="Filialga xos matn",
            )
            notification = services.queue_notification(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                guardian=guardian,
                code="debt_reminder",
            )
        assert notification.rendered_body == "Filialga xos matn"


class TestRendering:
    def test_variables_are_substituted(self):
        body = "Salom ${guardian}, ${child} uchun ${amount} so'm"
        assert (
            services.render_template(
                body, {"guardian": "Nodira", "child": "Ali", "amount": "500 000"}
            )
            == "Salom Nodira, Ali uchun 500 000 so'm"
        )

    def test_unknown_placeholder_does_not_break_the_message(self):
        """
        Noma'lum o'rinbosar xabarni yiqitmaydi.

        Shablon matnini MIJOZ tahrirlaydi; bitta xato o'rinbosar tufayli
        butun yuborish to'xtab qolishi mumkin emas.
        """
        result = services.render_template("Salom ${nomalum}", {})
        assert "${nomalum}" in result

    def test_stray_brace_does_not_break_the_message(self):
        """`.format()` bo'lganda `{` belgisi yuborishni yiqitardi."""
        assert services.render_template("Narx {100} so'm", {}) == "Narx {100} so'm"


class TestQueueing:
    def test_snapshot_of_address_and_body(self, tenant_a, guardian):
        """
        Manzil va matn nusxa sifatida saqlanadi.

        Vasiy telefonini keyin o'zgartirsa, jurnalda AYNAN qayerga nima
        yuborilgani ko'rinib turishi kerak.
        """
        with organization_context(tenant_a.organization.id):
            notification = services.queue_notification(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                guardian=guardian,
                code="debt_reminder",
                variables={
                    "guardian": "Nodira",
                    "child": "Ali",
                    "amount": "100",
                    "organization": "X",
                },
            )
            Guardian.objects.filter(pk=guardian.pk).update(phone="+998900000000")
            notification.refresh_from_db()

        assert notification.recipient_address == "+998901112233"
        assert "Nodira" in notification.rendered_body

    def test_guardian_without_phone_is_skipped_not_an_error(self, tenant_a):
        """
        Telefonsiz vasiy — oddiy holat, xato emas.

        Istisno ko'tarish to'lov qabul qilishni yiqitardi, holbuki
        to'lovning o'zi muvaffaqiyatli.
        """
        with organization_context(tenant_a.organization.id):
            silent = Guardian.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                first_name="Telefonsiz",
                last_name="Vasiy",
                phone="",
            )
            assert (
                services.queue_notification(
                    organization=tenant_a.organization,
                    branch=tenant_a.branch,
                    guardian=silent,
                    code="debt_reminder",
                )
                is None
            )


class TestDispatch:
    def test_successful_send_records_provider_id(self, tenant_a, guardian):
        with organization_context(tenant_a.organization.id):
            notification = services.queue_notification(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                guardian=guardian,
                code="debt_reminder",
            )
            services.dispatch_notification(notification, now_time=time(10, 0))
            notification.refresh_from_db()

        # Console provayder — "Yuborildi" emas, "Test rejimi" (PLAN 3.2):
        # xabar hech qayerga ketmagan va jurnal buni aytishi kerak.
        assert notification.status == NotificationStatus.TEST_MODE
        assert notification.provider_message_id
        assert notification.sent_at is not None

    @override_settings(NOTIFICATION_PROVIDER="failing")
    def test_failure_is_logged_not_swallowed(self, tenant_a, guardian):
        """
        Xato JIMGINA yo'qolmaydi.

        "SMS kelmadi" degan shikoyatga javob jurnalda — sabab va urinishlar
        soni bilan — bo'lishi kerak.
        """
        with organization_context(tenant_a.organization.id):
            notification = services.queue_notification(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                guardian=guardian,
                code="debt_reminder",
            )
            services.dispatch_notification(notification, now_time=time(10, 0))
            notification.refresh_from_db()

        assert notification.status == NotificationStatus.FAILED
        assert notification.error
        assert notification.retry_count == 1

    def test_already_sent_cannot_be_resent(self, tenant_a, guardian):
        with organization_context(tenant_a.organization.id):
            notification = services.queue_notification(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                guardian=guardian,
                code="debt_reminder",
            )
            services.dispatch_notification(notification, now_time=time(10, 0))
            with pytest.raises(BusinessRuleViolation, match="yuborib bo'lmaydi"):
                services.dispatch_notification(notification, now_time=time(10, 0))


class TestPaymentReceipt:
    def test_payment_queues_an_sms(self, tenant_a, child_with_guardian):
        from apps.finance import services as finance
        from apps.finance.models import TariffPlan

        with organization_context(tenant_a.organization.id):
            tariff = TariffPlan.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                name="Tarif",
                amount=Decimal("1000000"),
            )
            Child.objects.filter(pk=child_with_guardian.pk).update(tariff=tariff)
            child_with_guardian.refresh_from_db()

            invoice = finance.issue_invoice(
                child=child_with_guardian, period_year=2026, period_month=7
            )
            finance.record_payment(
                child=child_with_guardian,
                amount=Decimal("1000000"),
                method="cash",
                invoice=invoice,
            )
            notification = Notification.objects.filter(template__code="payment_received").first()

        assert notification is not None
        assert "1 000 000" in notification.rendered_body

    @override_settings(NOTIFICATION_PROVIDER="failing")
    def test_payment_succeeds_even_if_sms_fails(self, tenant_a, child_with_guardian):
        """
        SMS shlyuzi ishlamasa ham to'lov qabul qilinadi.

        Pul allaqachon kelgan — uni bildirishnoma tufayli bekor qilish
        mumkin emas (P8).
        """
        from apps.finance import services as finance

        with organization_context(tenant_a.organization.id):
            payment = finance.record_payment(
                child=child_with_guardian, amount=Decimal("250000"), method="cash"
            )
        assert payment.id is not None


class TestDebtReminders:
    def test_reminders_go_only_to_actual_debtors(self, tenant_a, child_with_guardian):
        from apps.finance import services as finance
        from apps.finance.models import TariffPlan

        with organization_context(tenant_a.organization.id):
            tariff = TariffPlan.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                name="Tarif",
                amount=Decimal("1500000"),
            )
            Child.objects.filter(pk=child_with_guardian.pk).update(tariff=tariff)
            child_with_guardian.refresh_from_db()
            invoice = finance.issue_invoice(
                child=child_with_guardian, period_year=2026, period_month=7
            )

            queued = services.queue_debt_reminders(organization=tenant_a.organization)
            assert len(queued) == 1
            assert "1 500 000" in queued[0].rendered_body

            # To'lagandan keyin eslatma ketmaydi.
            finance.record_payment(
                child=child_with_guardian,
                amount=Decimal("1500000"),
                method="cash",
                invoice=invoice,
            )
            assert services.queue_debt_reminders(organization=tenant_a.organization) == []


class TestEndpoints:
    def test_send_endpoint(self, tenant_a, guardian):
        response = tenant_a.client().post(
            reverse("v1:notification-send"),
            {
                "template_code": "debt_reminder",
                "guardian_ids": [str(guardian.id)],
                "variables": {
                    "guardian": "Nodira",
                    "child": "Ali",
                    "amount": "500000",
                    "organization": "Alfa",
                },
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["data"]["queued"] == 1

    def test_log_is_read_only(self, tenant_a, guardian):
        with organization_context(tenant_a.organization.id):
            notification = services.queue_notification(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                guardian=guardian,
                code="debt_reminder",
            )
        client = tenant_a.client()
        url = reverse("v1:notification-detail", args=[notification.id])
        assert client.patch(url, {"rendered_body": "x"}, format="json").status_code == 405
        assert client.delete(url).status_code == 405

    @pytest.mark.tenancy
    def test_cannot_message_another_tenants_guardian(self, tenant_a, tenant_b):
        with organization_context(tenant_b.organization.id):
            foreign = Guardian.objects.create(
                organization=tenant_b.organization,
                branch=tenant_b.branch,
                first_name="Begona",
                last_name="Vasiy",
                phone="+998909999999",
            )
        response = tenant_a.client().post(
            reverse("v1:notification-send"),
            {"template_code": "debt_reminder", "guardian_ids": [str(foreign.id)]},
            format="json",
        )
        # Begona vasiy `Guardian.objects` da umuman ko'rinmaydi.
        assert response.status_code == 422
        assert "topilmadi" in response.json()["error"]["message"]
