"""
SMS qoidalari: test rejimi, raqam, soat, chegara va narx (PLAN 3.1–3.5).

Audit topgan asosiy muammo bitta jumlada: **jurnal "Yuborildi" deb
turardi, ota-ona esa hech narsa olmagan edi.** Shu fayl aynan o'sha
jimgina yolg'onning har bir shaklini qoplaydi.
"""

from __future__ import annotations

from datetime import time
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.children.models import Child, Guardian
from apps.children.services import attach_guardian
from apps.core.tenancy import organization_context
from apps.notifications import selectors, services
from apps.notifications.models import Notification, NotificationStatus
from apps.notifications.segments import measure, parts_for, sms_safe

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]


def _guardian(tenant, phone: str = "+998901112233", name: str = "Vasiy") -> Guardian:
    with organization_context(tenant.organization.id):
        return Guardian.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name=name,
            last_name="Sinov",
            phone=phone,
        )


class TestSegments:
    """Narx BO'LAKLAR bo'yicha — bu hisob shablon muharririda ham ko'rinadi."""

    def test_latin_fits_160_characters(self):
        assert measure("a" * 160).parts == 1
        assert measure("a" * 161).parts == 2

    def test_cyrillic_drops_to_70(self):
        assert measure("ё" * 70).parts == 1
        assert measure("ё" * 71).parts == 2

    def test_uzbek_apostrophe_doubles_the_price_until_it_is_replaced(self):
        """Q11: `ʻ` GSM-7 da yo'q — bitta belgi narxni ikki baravar qiladi."""
        text = "Toʻlov qabul qilindi. " + "a" * 100
        assert measure(text).encoding == "ucs2"
        assert measure(sms_safe(text)).encoding == "gsm7"
        assert parts_for(sms_safe(text)) < parts_for(text)

    def test_queued_message_is_cleaned_before_sending(self, tenant_a):
        guardian = _guardian(tenant_a)
        with organization_context(tenant_a.organization.id):
            notification = services.queue_notification(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                guardian=guardian,
                code="debt_reminder",
                body_override="Toʻlov: ${amount}",
                variables={"amount": "500 000"},
            )
        assert notification is not None
        assert "ʻ" not in notification.rendered_body
        assert notification.rendered_body.startswith("To'lov")


class TestSendingWindow:
    def test_outside_the_window_the_message_waits_it_is_not_lost(self, tenant_a):
        guardian = _guardian(tenant_a)
        with organization_context(tenant_a.organization.id):
            notification = services.queue_notification(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                guardian=guardian,
                code="debt_reminder",
            )
            assert notification is not None
            services.dispatch_notification(notification, now_time=time(23, 30))
            notification.refresh_from_db()
            assert notification.status == NotificationStatus.QUEUED

            # Ertalab o'sha xabar ketadi — yangisi yaratilmaydi.
            services.dispatch_notification(notification, now_time=time(9, 0))
            notification.refresh_from_db()

        assert notification.status == NotificationStatus.TEST_MODE
        assert notification.sent_at is not None

    def test_the_window_is_a_setting_not_a_constant(self, tenant_a):
        from apps.settings_app.services import set_setting

        with organization_context(tenant_a.organization.id):
            set_setting(
                organization=tenant_a.organization, key="notifications.send_from_hour", value=10
            )
            assert services.within_sending_window(time(9, 0)) is False
            assert services.within_sending_window(time(10, 1)) is True


class TestInvalidNumber:
    @pytest.mark.parametrize("phone", ["12345", "+1 555 0100", ""])
    def test_a_bad_number_never_reads_as_delivered(self, tenant_a, phone):
        problem = services.delivery_problem(phone)
        assert problem, "sabab bo'lishi kerak"


class TestDailyLimit:
    def test_the_second_reminder_of_the_day_is_not_queued(self, tenant_a):
        guardian = _guardian(tenant_a)
        with organization_context(tenant_a.organization.id):
            first = services.queue_notification(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                guardian=guardian,
                code="debt_reminder",
            )
            second = services.queue_notification(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                guardian=guardian,
                code="debt_reminder",
            )
        assert first is not None
        assert second is None

    def test_a_payment_receipt_is_not_limited(self, tenant_a):
        """Kvitansiya takrorlanmaydi va har biri yangi ma'lumot."""
        guardian = _guardian(tenant_a)
        with organization_context(tenant_a.organization.id):
            services.queue_notification(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                guardian=guardian,
                code="debt_reminder",
            )
            receipt = services.queue_notification(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                guardian=guardian,
                code="payment_received",
                variables={"amount": "100 000"},
            )
        assert receipt is not None


class TestUsageAndCost:
    def test_test_mode_messages_are_not_counted_as_cost(self, tenant_a):
        guardian = _guardian(tenant_a)
        with organization_context(tenant_a.organization.id):
            from apps.settings_app.services import set_setting

            set_setting(
                organization=tenant_a.organization, key="notifications.sms_price", value="85"
            )
            notification = services.queue_notification(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                guardian=guardian,
                code="debt_reminder",
            )
            assert notification is not None
            services.dispatch_notification(notification, now_time=time(10, 0))

            usage = selectors.monthly_usage(
                year=notification.created_at.year, month=notification.created_at.month
            )

        assert usage["test_mode"] == 1
        assert usage["sent"] == 0
        # Test rejimidagi xabar hech qayerga bormagan — u pul turmaydi.
        assert usage["parts"] == 0
        assert usage["estimated_cost"] == Decimal("0")

    def test_price_is_decimal_never_float(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            usage = selectors.monthly_usage(year=2026, month=10)
        assert isinstance(usage["price_per_part"], Decimal)


class TestStatusEndpoint:
    def test_status_tells_the_screen_it_is_test_mode(self, tenant_a):
        response = tenant_a.client().get(reverse("v1:notification-sms-status"))
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["test_mode"] is True
        assert data["send_from_hour"] == 8
        assert data["send_to_hour"] == 21

    def test_a_live_provider_turns_the_banner_off(self, tenant_a, settings):
        # `override_settings` dekoratori `settings` fixture bilan birga
        # ishlatilmaydi: dekorator test qaytgach o'chadi, fixture esa
        # undan KEYIN tiklaydi va natijada qiymat butun sessiyaga
        # sizib qoladi (shu sababdan boshqa fayldagi test yiqilgan edi).
        settings.NOTIFICATION_PROVIDER = "eskiz"
        settings.ESKIZ_EMAIL = "a@b.uz"
        settings.ESKIZ_PASSWORD = "secret"  # noqa: S105 — test qiymati
        settings.ESKIZ_FROM = "4546"
        response = tenant_a.client().get(reverse("v1:notification-sms-status"))
        assert response.json()["data"]["test_mode"] is False

    @pytest.mark.tenancy
    def test_usage_counts_only_my_own_organization(self, tenant_a, tenant_b):
        with organization_context(tenant_b.organization.id):
            foreign = Guardian.objects.create(
                organization=tenant_b.organization,
                branch=tenant_b.branch,
                first_name="Begona",
                last_name="Vasiy",
                phone="+998909999999",
            )
            services.queue_notification(
                organization=tenant_b.organization,
                branch=tenant_b.branch,
                guardian=foreign,
                code="debt_reminder",
            )

        response = tenant_a.client().get(reverse("v1:notification-sms-status"))
        assert response.json()["data"]["usage"]["total"] == 0


class TestReminderPreview:
    @pytest.fixture
    def debtor(self, tenant_a) -> Child:
        from datetime import date

        from apps.finance import services as finance

        guardian = _guardian(tenant_a, name="Qarzdor")
        with organization_context(tenant_a.organization.id):
            child = Child.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                first_name="Qarzdor",
                last_name="Bola",
                date_of_birth=date(2021, 5, 5),
            )
            attach_guardian(child=child, guardian=guardian, relation="mother", is_primary=True)
            finance.post_ledger_entry(
                child=child,
                entry_type="tuition",
                direction="debit",
                amount=Decimal("1500000"),
                source_type="invoice",
            )
        return child

    def test_preview_counts_before_anything_is_sent(self, tenant_a, debtor):
        url = reverse("v1:notification-reminder-preview")
        response = tenant_a.client().get(url)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["eligible"] == 1
        assert data["parts"] >= 1
        # Ko'rib chiqish HECH NARSA yubormaydi.
        with organization_context(tenant_a.organization.id):
            assert Notification.objects.count() == 0

    def test_preview_and_send_use_the_same_filter(self, tenant_a, debtor):
        client = tenant_a.client()
        # 60+ kun kechikkanlar: bu bola 60 kun kechikmagan.
        preview = client.get(reverse("v1:notification-reminder-preview"), {"min_days": 60})
        assert preview.json()["data"]["eligible"] == 0

        sent = client.post(
            reverse("v1:notification-remind-debtors"), {"min_days": 60}, format="json"
        )
        assert sent.json()["data"]["queued"] == 0

    def test_a_broken_group_filter_does_not_widen_the_audience(self, tenant_a, debtor):
        """Buzuq filtr HAMMAGA yuborishga aylanmasin."""
        response = tenant_a.client().post(
            reverse("v1:notification-remind-debtors"), {"group_id": "not-a-uuid"}, format="json"
        )
        assert response.status_code == 422
        with organization_context(tenant_a.organization.id):
            assert Notification.objects.count() == 0
