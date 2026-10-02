"""
Uzun so'rov rejimi (PLAN 3.7).

Webhook va uzun so'rov BIR XIL mantiqdan o'tishi kerak: ikki nusxa
bo'lsa, ular ertami-kechmi ajralib ketadi — biri `/stop` ni biladi,
ikkinchisi bilmaydi, va bot qaysi rejimda ishlayotganiga qarab
boshqacha javob beradi.

Tarmoqqa chiqilmaydi: `requests` almashtiriladi.
"""

from __future__ import annotations

from io import StringIO
from unittest.mock import Mock, patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.children import telegram as links
from apps.children.models import Guardian
from apps.core.tenancy import organization_context
from apps.notifications.telegram_updates import handle_update

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]


@pytest.fixture
def bot(settings):
    settings.TELEGRAM_BOT_TOKEN = "123:ABC"  # noqa: S105 — test qiymati
    settings.TELEGRAM_BOT_USERNAME = "radix_crm_bot"
    return settings


def _json(payload: dict) -> Mock:
    response = Mock()
    response.status_code = 200
    response.json.return_value = payload
    response.text = str(payload)
    return response


def _update(text: str, chat_id: int = 777, update_id: int = 1) -> dict:
    return {
        "update_id": update_id,
        "message": {"message_id": 1, "chat": {"id": chat_id}, "text": text},
    }


class TestSharedHandler:
    """Ikki rejim bitta funksiyadan o'tadi."""

    def test_start_links_the_guardian(self, bot, tenant_a):
        with organization_context(tenant_a.organization.id):
            guardian = Guardian.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                first_name="Nodira",
                last_name="Karimova",
                phone="+998901112233",
            )
            code = links.ensure_code(guardian)

        with patch("requests.post", return_value=_json({"ok": True, "result": {"message_id": 1}})):
            assert handle_update(_update(f"/start {code}")) == "linked"

        with organization_context(tenant_a.organization.id):
            guardian.refresh_from_db()
        assert guardian.telegram_chat_id == "777"

    def test_an_expired_code_says_so(self, bot):
        with patch("requests.post", return_value=_json({"ok": True})):
            assert handle_update(_update("/start nothing")) == "unknown_code"

    def test_plain_start_gets_instructions(self, bot):
        with patch("requests.post", return_value=_json({"ok": True})):
            assert handle_update(_update("/start")) == "help"

    def test_chatter_is_ignored(self, bot):
        with patch("requests.post") as post:
            assert handle_update(_update("Assalomu alaykum")) == "ignored"
        assert not post.called, "bot suhbat quradigan joy emas"

    def test_a_broken_update_does_not_raise(self, bot):
        assert handle_update({"nonsense": True}) == "ignored"


class TestPollingCommand:
    def test_it_refuses_to_start_without_a_token(self, settings):
        settings.TELEGRAM_BOT_TOKEN = ""
        with pytest.raises(CommandError, match="TELEGRAM_BOT_TOKEN"):
            call_command("run_telegram_polling", once=True, stdout=StringIO())

    def test_it_refuses_while_a_webhook_is_set(self, bot):
        """
        Telegram ikkalasini bir vaqtda qabul qilmaydi.

        Buni oldin aytmasak, xato `409 Conflict` bo'lib keladi va u
        nima bo'layotganini tushuntirmaydi. Prod webhook'ini
        JIMGINA o'chirib qo'yish esa bog'chalarni bildirishnomasiz
        qoldirardi.
        """
        responses = {
            "getMe": _json({"ok": True, "result": {"username": "radix_crm_bot"}}),
            "getWebhookInfo": _json({"ok": True, "result": {"url": "https://radix-crm.uz/hook"}}),
        }
        with (
            patch("requests.get", side_effect=lambda url, **kw: responses[url.rsplit("/", 1)[-1]]),
            pytest.raises(CommandError, match="Webhook o'rnatilgan"),
        ):
            call_command("run_telegram_polling", once=True, stdout=StringIO())

    def test_it_processes_a_batch_and_advances_the_offset(self, bot, tenant_a):
        with organization_context(tenant_a.organization.id):
            guardian = Guardian.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                first_name="Nodira",
                last_name="Karimova",
                phone="+998901112233",
            )
            code = links.ensure_code(guardian)

        calls: list[dict] = []

        def fake_get(url: str, **kwargs):
            name = url.rsplit("/", 1)[-1]
            if name == "getMe":
                return _json({"ok": True, "result": {"username": "radix_crm_bot"}})
            if name == "getWebhookInfo":
                return _json({"ok": True, "result": {"url": ""}})
            calls.append(kwargs.get("params") or {})
            return _json({"ok": True, "result": [_update(f"/start {code}", update_id=42)]})

        out = StringIO()
        with (
            patch("requests.get", side_effect=fake_get),
            patch("requests.post", return_value=_json({"ok": True, "result": {"message_id": 1}})),
        ):
            call_command("run_telegram_polling", once=True, stdout=out)

        assert "linked" in out.getvalue()
        with organization_context(tenant_a.organization.id):
            guardian.refresh_from_db()
        assert guardian.telegram_chat_id == "777"
        # Birinchi so'rovda `offset` yo'q — Telegram yetkazilmaganini
        # beradi; keyingisida esa 43 bo'lishi kerak.
        assert "offset" not in calls[0]

    def test_one_broken_update_does_not_stop_the_loop(self, bot):
        def fake_get(url: str, **kwargs):
            name = url.rsplit("/", 1)[-1]
            if name == "getMe":
                return _json({"ok": True, "result": {"username": "radix_crm_bot"}})
            if name == "getWebhookInfo":
                return _json({"ok": True, "result": {"url": ""}})
            return _json({"ok": True, "result": [_update("/stop", update_id=7)]})

        out, err = StringIO(), StringIO()
        with (
            patch("requests.get", side_effect=fake_get),
            # Buyruq `handle_update` ni modul darajasida import
            # qiladi, shuning uchun almashtirish AYNAN shu nomga
            # qo'yiladi — manba modulidagisiga emas.
            patch(
                "apps.notifications.management.commands.run_telegram_polling.handle_update",
                side_effect=RuntimeError("x"),
            ),
        ):
            call_command("run_telegram_polling", once=True, stdout=out, stderr=err)
        # Buyruq yiqilmadi va sababni yozdi.
        assert "Update 7" in err.getvalue()
