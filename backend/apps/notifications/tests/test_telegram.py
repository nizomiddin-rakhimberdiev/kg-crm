"""
Telegram kanali (PLAN 3.7, ADR-23).

Tarmoqqa chiqilmaydi — `requests.post` almashtiriladi. Asosiy
savollar:

* ulanmagan ota-onaga xabar JIMGINA yo'qoladimi? (yo'q — sababi
  bilan `failed`);
* `/start` boshqa bog'chaning oilasiga ulanib ketadimi? (yo'q — kod
  global unikal va bir martalik);
* maxfiy yo'ldan kelmagan so'rov nima oladi? (`404`, `403` emas);
* Telegram xabari pul turadimi? (yo'q — hisobga tushmaydi).
"""

from __future__ import annotations

from datetime import time
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from django.urls import reverse

from apps.children import telegram as links
from apps.children.models import Guardian
from apps.core.tenancy import organization_context
from apps.notifications import selectors, services
from apps.notifications.models import NotificationStatus
from apps.notifications.providers import TelegramProvider, is_test_mode

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]

SECRET = "s" * 40


@pytest.fixture
def bot(settings):
    settings.TELEGRAM_BOT_TOKEN = "123:ABC"  # noqa: S105 — test qiymati
    settings.TELEGRAM_BOT_USERNAME = "radix_kg_bot"
    settings.TELEGRAM_WEBHOOK_SECRET = SECRET  # noqa: S105 — test qiymati
    return settings


def _guardian(tenant, phone: str = "+998901112233", chat: str = "") -> Guardian:
    with organization_context(tenant.organization.id):
        return Guardian.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Nodira",
            last_name="Karimova",
            phone=phone,
            telegram_chat_id=chat,
        )


def _ok(message_id: int = 7) -> Mock:
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"ok": True, "result": {"message_id": message_id}}
    response.text = "ok"
    return response


def _error(status_code: int, description: str) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.json.return_value = {"ok": False, "description": description}
    response.text = description
    return response


class TestProvider:
    def test_without_a_token_the_provider_refuses_to_start(self, settings):
        from django.core.exceptions import ImproperlyConfigured

        settings.TELEGRAM_BOT_TOKEN = ""
        with pytest.raises(ImproperlyConfigured):
            TelegramProvider()

    def test_a_token_makes_telegram_the_live_channel(self, bot):
        assert is_test_mode("telegram") is False
        # SMS esa ulanmagan — bu normal holat, xato emas.
        assert is_test_mode("sms") is True

    def test_the_chat_id_goes_as_the_address(self, bot):
        with patch("requests.post", return_value=_ok()) as post:
            result = TelegramProvider().send(address="55501", body="Salom")
        assert result.success and result.provider_message_id == "7"
        assert post.call_args.kwargs["json"]["chat_id"] == "55501"
        # Bezak YO'Q: bola ismidagi `_` yoki `<` butun xabarni
        # yiqitmasligi kerak.
        assert "parse_mode" not in post.call_args.kwargs["json"]

    def test_a_blocked_bot_is_reported_in_plain_words(self, bot):
        blocked = _error(403, "Forbidden: bot was blocked by the user")
        with patch("requests.post", return_value=blocked):
            result = TelegramProvider().send(address="55501", body="Salom")
        assert result.success is False
        assert result.error == "Ota-ona botni bloklagan"

    def test_an_unknown_chat_reads_as_not_connected(self, bot):
        with patch("requests.post", return_value=_error(400, "Bad Request: chat not found")):
            result = TelegramProvider().send(address="55501", body="Salom")
        assert result.error == "Telegram ulanmagan"

    def test_a_network_failure_is_not_a_crash(self, bot):
        import requests

        with patch("requests.post", side_effect=requests.ConnectionError("tarmoq yoʻq")):
            result = TelegramProvider().send(address="55501", body="Salom")
        assert result.success is False and "Tarmoq" in result.error


class TestChannelChoice:
    def test_a_linked_parent_is_messaged_on_telegram(self, bot, tenant_a):
        guardian = _guardian(tenant_a, chat="55501")
        with organization_context(tenant_a.organization.id):
            services.seed_default_templates(tenant_a.organization)
            notification = services.queue_notification(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                guardian=guardian,
                code="debt_reminder",
                variables={"guardian": "Nodira", "child": "Ali", "amount": "500 000"},
            )
            assert notification is not None
            assert notification.channel == "telegram"
            assert notification.recipient_address == "55501"
            with patch("requests.post", return_value=_ok()):
                services.dispatch_notification(notification, now_time=time(10, 0))
            notification.refresh_from_db()
        assert notification.status == NotificationStatus.SENT

    def test_an_unlinked_parent_is_not_silently_skipped(self, bot, tenant_a):
        """Jurnalda sabab turishi kerak — bogʻcha nimani tuzatishni bilsin."""
        guardian = _guardian(tenant_a)
        with organization_context(tenant_a.organization.id):
            notification = services.queue_notification(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                guardian=guardian,
                code="debt_reminder",
            )
            assert notification is not None
            services.dispatch_notification(notification, now_time=time(10, 0))
            notification.refresh_from_db()
        assert notification.status == NotificationStatus.FAILED
        assert notification.error == "Telegram ulanmagan"

    def test_sms_is_used_only_when_its_gateway_is_really_connected(self, bot, tenant_a, settings):
        guardian = _guardian(tenant_a)
        with organization_context(tenant_a.organization.id):
            # Test rejimidagi SMS'ga "tushib qolish" YO'Q.
            assert services.resolve_channel(guardian) == "telegram"

            settings.NOTIFICATION_PROVIDER = "eskiz"
            settings.ESKIZ_EMAIL = "a@b.uz"
            settings.ESKIZ_PASSWORD = "secret"  # noqa: S105 — test qiymati
            settings.ESKIZ_FROM = "4546"
            assert services.resolve_channel(guardian) == "sms"

    def test_telegram_keeps_the_uzbek_apostrophe(self, bot, tenant_a):
        """SMSʼda `ʻ` narxni ikki baravar qiladi; Telegramda cheklov yoʻq."""
        guardian = _guardian(tenant_a, chat="55501")
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
        assert "ʻ" in notification.rendered_body

    def test_the_daily_cap_works_without_a_template_row(self, bot, tenant_a):
        """
        Chegara shablon FK'siga TAYANMAYDI.

        `template_id` `NULL` bo'lishi mumkin (matn koddagi sukutdan) va
        shablon o'chirilsa `SET_NULL` bo'ladi — ikkala holatda ham
        chegara jimgina ishlamay qo'yardi.
        """
        from apps.notifications.models import NotificationTemplate

        guardian = _guardian(tenant_a, chat="55501")
        with organization_context(tenant_a.organization.id):
            # Shablon qatorini ATAYLAB o'chiramiz: matn koddagi
            # sukutdan keladi va `template_id` `NULL` bo'ladi — ya'ni
            # chegara faqat `template_code` ga tayanishi kerak.
            NotificationTemplate.objects.filter(channel="telegram").delete()
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
        assert first is not None and first.template is None
        assert first.template_code == "debt_reminder"
        assert second is None


class TestLinking:
    def test_the_link_carries_a_one_time_code(self, bot, tenant_a):
        guardian = _guardian(tenant_a)
        with organization_context(tenant_a.organization.id):
            url = links.link_url(guardian)
            guardian.refresh_from_db()
        assert url.startswith("https://t.me/radix_kg_bot?start=")
        assert guardian.telegram_code and len(guardian.telegram_code) >= 16

    def test_without_a_bot_username_there_is_no_link(self, tenant_a, settings):
        settings.TELEGRAM_BOT_USERNAME = ""
        guardian = _guardian(tenant_a)
        with organization_context(tenant_a.organization.id):
            assert links.link_url(guardian) == ""

    def test_start_links_the_chat_and_burns_the_code(self, bot, tenant_a):
        guardian = _guardian(tenant_a)
        with organization_context(tenant_a.organization.id):
            code = links.ensure_code(guardian)

        linked = links.link_from_start(code=code, chat_id="99001")
        assert linked is not None and linked.pk == guardian.pk

        with organization_context(tenant_a.organization.id):
            guardian.refresh_from_db()
        assert guardian.telegram_chat_id == "99001"
        assert guardian.telegram_linked_at is not None
        # Havola oilaviy guruhga tashlanishi mumkin — kod bir martalik.
        assert guardian.telegram_code == ""
        assert links.link_from_start(code=code, chat_id="99002") is None

    def test_stop_unlinks_every_kindergarten_using_that_chat(self, bot, tenant_a, tenant_b):
        """Ota-ona bitta botda "to'xtat" dedi — hamma joyda to'xtaydi."""
        first = _guardian(tenant_a, chat="99001")
        second = _guardian(tenant_b, phone="+998905556677", chat="99001")

        assert links.unlink_chat("99001") == 2
        with organization_context(tenant_a.organization.id):
            first.refresh_from_db()
            assert first.telegram_chat_id == ""
        with organization_context(tenant_b.organization.id):
            second.refresh_from_db()
            assert second.telegram_chat_id == ""

    @pytest.mark.tenancy
    def test_a_code_from_another_organization_links_only_its_own_guardian(
        self, bot, tenant_a, tenant_b
    ):
        mine = _guardian(tenant_a)
        theirs = _guardian(tenant_b, phone="+998905556677")
        with organization_context(tenant_b.organization.id):
            foreign_code = links.ensure_code(theirs)

        linked = links.link_from_start(code=foreign_code, chat_id="99009")
        assert linked is not None
        assert linked.organization_id == tenant_b.organization.id
        with organization_context(tenant_a.organization.id):
            mine.refresh_from_db()
            assert mine.telegram_chat_id == ""


class TestLinkEndpoint:
    def test_staff_can_issue_and_rotate_the_link(self, bot, tenant_a):
        guardian = _guardian(tenant_a)
        url = reverse("v1:guardian-telegram-link", args=[guardian.id])
        first = tenant_a.client().post(url, {}, format="json")
        assert first.status_code == 200
        issued = first.json()["data"]["url"]
        assert "start=" in issued

        again = tenant_a.client().post(url, {}, format="json")
        assert again.json()["data"]["url"] == issued, "qayta soʻrash kodni almashtirmaydi"

        rotated = tenant_a.client().post(url, {"rotate": True}, format="json")
        assert rotated.json()["data"]["url"] != issued

    def test_staff_can_unlink(self, bot, tenant_a):
        guardian = _guardian(tenant_a, chat="99001")
        response = tenant_a.client().post(
            reverse("v1:guardian-telegram-unlink", args=[guardian.id]), {}, format="json"
        )
        assert response.status_code == 200
        assert response.json()["data"]["telegram_linked"] is False

    @pytest.mark.tenancy
    def test_another_organizations_guardian_is_404(self, bot, tenant_a, tenant_b):
        theirs = _guardian(tenant_b, phone="+998905556677")
        response = tenant_a.client().post(
            reverse("v1:guardian-telegram-link", args=[theirs.id]), {}, format="json"
        )
        assert response.status_code == 404


class TestWebhook:
    def _url(self, secret: str = SECRET) -> str:
        return reverse("v1:telegram-webhook", args=[secret])

    def _update(self, text: str, chat_id: int = 99001) -> dict:
        return {
            "update_id": 1,
            "message": {"message_id": 1, "chat": {"id": chat_id}, "text": text},
        }

    def test_a_wrong_secret_is_404_not_403(self, bot, client):
        response = client.post(
            self._url("wrong-secret"),
            self._update("/start"),
            content_type="application/json",
        )
        # `403` "endpoint bor, lekin ruxsat yoʻq" deb aytib qo'yardi.
        assert response.status_code == 404

    def test_without_configuration_the_endpoint_does_not_exist(self, settings, client):
        settings.TELEGRAM_WEBHOOK_SECRET = ""
        response = client.post(self._url(), self._update("/start"), content_type="application/json")
        assert response.status_code == 404

    def test_start_with_a_code_links_the_parent(self, bot, tenant_a, client):
        guardian = _guardian(tenant_a)
        with organization_context(tenant_a.organization.id):
            code = links.ensure_code(guardian)

        with patch("requests.post", return_value=_ok()) as post:
            response = client.post(
                self._url(), self._update(f"/start {code}"), content_type="application/json"
            )

        assert response.status_code == 200
        with organization_context(tenant_a.organization.id):
            guardian.refresh_from_db()
        assert guardian.telegram_chat_id == "99001"
        # Ota-onaga tasdiq boradi.
        assert "Nodira" in post.call_args.kwargs["json"]["text"]

    def test_an_expired_code_gets_a_human_answer(self, bot, client):
        with patch("requests.post", return_value=_ok()) as post:
            response = client.post(
                self._url(), self._update("/start nothing"), content_type="application/json"
            )
        assert response.status_code == 200
        assert "eskirgan" in post.call_args.kwargs["json"]["text"]

    def test_stop_unlinks(self, bot, tenant_a, client):
        guardian = _guardian(tenant_a, chat="99001")
        with patch("requests.post", return_value=_ok()):
            client.post(self._url(), self._update("/stop"), content_type="application/json")
        with organization_context(tenant_a.organization.id):
            guardian.refresh_from_db()
        assert guardian.telegram_chat_id == ""

    def test_a_broken_update_still_answers_200(self, bot, client):
        """
        Telegram `2xx` bo'lmagan javobdan keyin QAYTA yuboradi — soatlab.

        Ya'ni bitta buzuq update cheksiz tsiklga aylanishi mumkin edi.
        """
        response = client.post(self._url(), {"nonsense": True}, content_type="application/json")
        assert response.status_code == 200

    def test_chatter_is_ignored(self, bot, client):
        with patch("requests.post", return_value=_ok()) as post:
            response = client.post(
                self._url(), self._update("Assalomu alaykum"), content_type="application/json"
            )
        assert response.status_code == 200
        assert not post.called, "bot suhbat quradigan joy emas"


class TestCost:
    def test_telegram_messages_are_free(self, bot, tenant_a):
        from apps.settings_app.services import set_setting

        guardian = _guardian(tenant_a, chat="55501")
        with organization_context(tenant_a.organization.id):
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
            with patch("requests.post", return_value=_ok()):
                services.dispatch_notification(notification, now_time=time(10, 0))

            usage = selectors.monthly_usage(
                year=notification.created_at.year, month=notification.created_at.month
            )

        assert usage["sent"] == 1
        assert usage["telegram"] == 1 and usage["sms"] == 0
        # Yuborildi, lekin pul turmaydi.
        assert usage["parts"] == 0
        assert usage["estimated_cost"] == Decimal("0")

    def test_status_reports_how_many_parents_are_reachable(self, bot, tenant_a):
        _guardian(tenant_a, chat="55501")
        _guardian(tenant_a, phone="+998905556677")
        response = tenant_a.client().get(reverse("v1:notification-sms-status"))
        reach = response.json()["data"]["channels"]["telegram"]["reach"]
        assert reach == {"linked": 1, "total": 2}

    @pytest.mark.tenancy
    def test_reach_counts_only_my_own_organization(self, bot, tenant_a, tenant_b):
        _guardian(tenant_b, chat="55502")
        response = tenant_a.client().get(reverse("v1:notification-sms-status"))
        assert response.json()["data"]["channels"]["telegram"]["reach"]["total"] == 0


class TestLog:
    def test_the_log_shows_which_channel_was_used(self, bot, tenant_a):
        guardian = _guardian(tenant_a, chat="55501")
        with organization_context(tenant_a.organization.id):
            services.queue_notification(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                guardian=guardian,
                code="debt_reminder",
            )
        response = tenant_a.client().get(reverse("v1:notification-list"))
        row = response.json()["data"][0]
        assert row["channel"] == "telegram"
        assert row["template_code"] == "debt_reminder"
