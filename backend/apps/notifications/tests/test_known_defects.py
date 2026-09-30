"""
SMS kamchiliklari — 2026-09-30 auditi (PLAN 3.1–3.3; Q8, Q9).

Auditda: `provider_message_id` "console-…", holat "Yuborildi" — hatto
"12345" raqamiga ham. Ya'ni bildirishnomalar sahifasi ishlayotgandek
ko'rinadi, aslida esa hech kimga hech narsa bormagan. Bu eng yomon
turdagi xato: jimgina va ishonchli ko'rinadigan.

Kerak:
  * console provayder "yuborildi" emas, "test rejimi" deb belgilaydi;
  * noto'g'ri raqamga urinilmaydi — "xato: notoʻgʻri raqam";
  * yuborish soatlari 08:00–21:00 (Q9), qolganlari navbatda turadi.
"""

from __future__ import annotations

from datetime import time

import pytest

from apps.children.models import Guardian
from apps.core.tenancy import organization_context
from apps.notifications import services
from apps.notifications.models import NotificationStatus

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]


def _guardian(tenant_a, phone: str) -> Guardian:
    with organization_context(tenant_a.organization.id):
        return Guardian.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Vasiy",
            last_name="Sinov",
            phone=phone,
        )


def _queue(tenant_a, guardian):
    return services.queue_notification(
        organization=tenant_a.organization,
        branch=tenant_a.branch,
        guardian=guardian,
        code="debt_reminder",
        variables={"child": "Ali", "amount": "1 500 000", "days": "15"},
    )


class TestTestModeIsVisible:
    @pytest.mark.xfail(
        strict=True,
        reason="PLAN 3.2: console provayder 'sent' qaytaradi — test rejimi ko'rinmaydi",
    )
    def test_console_provider_does_not_claim_the_message_was_sent(self, tenant_a):
        guardian = _guardian(tenant_a, "+998901234567")
        with organization_context(tenant_a.organization.id):
            notification = _queue(tenant_a, guardian)
            assert notification is not None
            services.dispatch_notification(notification)
            notification.refresh_from_db()

        # "Yuborildi" — bu yolg'on: hech qayerga ketmadi.
        assert notification.status != NotificationStatus.SENT
        assert notification.status == "test_mode"


class TestInvalidRecipient:
    @pytest.mark.xfail(strict=True, reason="PLAN 3.1 / Q8: noto'g'ri raqam ham 'yuborildi' bo'ladi")
    @pytest.mark.parametrize("phone", ["12345", "45", "+1 555 0100"])
    def test_invalid_phone_is_marked_failed_not_sent(self, tenant_a, phone):
        guardian = _guardian(tenant_a, phone)
        with organization_context(tenant_a.organization.id):
            notification = _queue(tenant_a, guardian)
            assert notification is not None
            services.dispatch_notification(notification)
            notification.refresh_from_db()

        assert notification.status == NotificationStatus.FAILED
        assert notification.error_message, "sabab yozilishi kerak"


class TestSendingWindow:
    """Q9: 08:00–21:00 (Asia/Tashkent), qolganlari navbatda turadi."""

    @pytest.mark.xfail(strict=True, reason="PLAN 3.3 / Q9: yuborish oynasi yo'q")
    def test_sending_window_is_configurable(self, tenant_a):
        from apps.settings_app.services import DEFAULTS

        assert "notifications.send_from" in DEFAULTS
        assert "notifications.send_to" in DEFAULTS

    @pytest.mark.xfail(strict=True, reason="PLAN 3.3 / Q9: soat tekshiruvi yo'q")
    def test_message_outside_the_window_stays_queued(self, tenant_a):
        guardian = _guardian(tenant_a, "+998901234567")
        with organization_context(tenant_a.organization.id):
            notification = _queue(tenant_a, guardian)
            assert notification is not None
            # Kechasi soat 02:00 — ota-onani uyg'otmaymiz.
            services.dispatch_notification(notification, now_time=time(2, 0))  # type: ignore[call-arg]
            notification.refresh_from_db()

        assert notification.status == NotificationStatus.QUEUED


class TestDailyLimit:
    @pytest.mark.xfail(
        strict=True, reason="PLAN 3.3: bir bola bo'yicha kunlik eslatma chegarasi yo'q"
    )
    def test_only_one_debt_reminder_per_child_per_day(self, tenant_a):
        guardian = _guardian(tenant_a, "+998901234567")
        with organization_context(tenant_a.organization.id):
            first = _queue(tenant_a, guardian)
            second = _queue(tenant_a, guardian)

        assert first is not None
        # Ikkinchisi o'sha kuni yaratilmasligi kerak.
        assert second is None
