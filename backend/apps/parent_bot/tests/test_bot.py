"""
Parent bot (PLAN 6.2) and phone linking (PLAN 6.3, ADR-27).

What must hold: a parent sees only their own children; a chat or phone
leads to the right kindergarten without RLS being widened; a forwarded
contact card links nobody; the index never stores a phone or chat id.
"""

from __future__ import annotations

from decimal import Decimal
from io import StringIO
from unittest.mock import Mock, patch

import pytest
from django.core.management import call_command

from apps.children import telegram as links
from apps.children.models import ChildGuardian, Guardian
from apps.core.tenancy import organization_context, platform_context
from apps.notifications.telegram_updates import handle_update
from apps.online_payments.tests.conftest import connect, make_invoice
from apps.parent_bot.models import ContactIndex

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]

CHAT = 5550001


@pytest.fixture
def bot(settings):
    settings.TELEGRAM_BOT_TOKEN = "123:ABC"  # noqa: S105 — test value
    settings.TELEGRAM_BOT_USERNAME = "radix_crm_bot"
    settings.FRONTEND_URL = "https://radix-crm.uz"
    return settings


def _ok() -> Mock:
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"ok": True, "result": {"message_id": 1}}
    return response


def _send(update: dict) -> tuple[str, list[dict]]:
    """Runs one update; returns the outcome and every message the bot sent."""
    with patch("requests.post", return_value=_ok()) as post:
        outcome = handle_update(update)
    return outcome, [call.kwargs["json"] for call in post.call_args_list]


def _text(text: str, chat: int = CHAT, language: str = "uz") -> dict:
    return {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "chat": {"id": chat},
            "from": {"id": chat, "language_code": language},
            "text": text,
        },
    }


def _contact(phone: str, *, chat: int = CHAT, owner: int | None = None) -> dict:
    return {
        "update_id": 2,
        "message": {
            "message_id": 2,
            "chat": {"id": chat},
            "from": {"id": chat},
            "contact": {"phone_number": phone, "user_id": owner if owner is not None else chat},
        },
    }


def _family(tenant, *, phone: str = "+998901112233", amount: str = "1500000", first="Ali"):
    """A guardian with one child and an open invoice in `tenant`."""
    invoice = make_invoice(tenant, amount)
    with organization_context(tenant.organization.id):
        child = invoice.child
        if first != "Ali":
            child.first_name = first
            child.save(update_fields=["first_name", "updated_at"])
        guardian = Guardian.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Nodira",
            last_name="Karimova",
            phone=phone,
        )
        ChildGuardian.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            child=child,
            guardian=guardian,
            relation="mother",
            is_primary=True,
        )
        code = links.ensure_code(guardian)
    return guardian, child, invoice, code


def _link(tenant, chat: int = CHAT, **kwargs):
    guardian, child, invoice, code = _family(tenant, **kwargs)
    outcome, _ = _send(_text(f"/start {code}", chat=chat))
    assert outcome == "linked"
    return guardian, child, invoice


class TestMenu:
    def test_linking_shows_the_four_buttons(self, bot, tenant_a):
        _guardian, _child, _invoice, code = _family(tenant_a)
        _outcome, sent = _send(_text(f"/start {code}"))
        keyboard = sent[0]["reply_markup"]["keyboard"]
        labels = [button["text"] for row in keyboard for button in row]
        assert labels == ["💰 Balans", "🧾 Hisob-fakturalar", "💳 Toʻlash", "📄 Kvitansiyalar"]

    def test_balance_shows_the_debt_from_the_one_formula(self, bot, tenant_a):
        _link(tenant_a)
        outcome, sent = _send(_text("💰 Balans"))
        assert outcome == "balance"
        assert "Valiyev Ali" in sent[0]["text"]
        assert "Qarz: 1 500 000 soʻm" in sent[0]["text"]

    def test_buttons_work_in_any_language(self, bot, tenant_a):
        _link(tenant_a)
        assert _send(_text("💰 Баланс"))[0] == "balance"

    def test_invoices_lists_status(self, bot, tenant_a):
        _link(tenant_a)
        _outcome, sent = _send(_text("🧾 Hisob-fakturalar"))
        assert "09.2026" in sent[0]["text"] and "toʻlanmagan" in sent[0]["text"]

    def test_receipts_list_payments(self, bot, tenant_a):
        from apps.finance.services import record_payment

        _guardian, child, invoice = _link(tenant_a)
        with organization_context(tenant_a.organization.id):
            record_payment(child=child, amount=Decimal("500000"), method="cash", invoice=invoice)
        _outcome, sent = _send(_text("📄 Kvitansiyalar"))
        assert "500 000" in sent[0]["text"] and "naqd" in sent[0]["text"]

    def test_unknown_text_from_a_linked_parent_shows_the_menu(self, bot, tenant_a):
        _link(tenant_a)
        assert _send(_text("salom"))[0] == "menu"

    def test_an_unlinked_chat_is_still_ignored(self, bot, tenant_a):
        outcome, sent = _send(_text("💰 Balans"))
        assert outcome == "ignored" and sent == []


class TestPay:
    def test_without_online_payment_the_parent_is_sent_to_the_office(self, bot, tenant_a):
        _link(tenant_a)
        _outcome, sent = _send(_text("💳 Toʻlash"))
        assert "kassasida" in sent[0]["text"]

    def test_with_a_merchant_the_button_opens_the_pay_page(self, bot, tenant_a):
        _link(tenant_a)
        connect(tenant_a, "payme")
        _outcome, sent = _send(_text("💳 Toʻlash"))
        (button,) = [row[0] for row in sent[0]["reply_markup"]["inline_keyboard"]]
        assert button["url"].startswith("https://radix-crm.uz/pay/")
        assert "Ali" in button["text"]

    def test_a_paid_child_has_nothing_to_pay(self, bot, tenant_a):
        from apps.finance.services import record_payment

        _guardian, child, invoice = _link(tenant_a)
        connect(tenant_a, "payme")
        with organization_context(tenant_a.organization.id):
            record_payment(child=child, amount=invoice.amount_due, method="cash", invoice=invoice)
        _outcome, sent = _send(_text("💳 Toʻlash"))
        assert "Toʻlanadigan hisob-faktura yoʻq" in sent[0]["text"]


class TestIsolation:
    def test_a_parent_sees_only_their_own_child(self, bot, tenant_a):
        _link(tenant_a, chat=1, phone="+998901110001")
        _link(tenant_a, chat=2, phone="+998901110002", first="Madina")
        _outcome, sent = _send(_text("💰 Balans", chat=1))
        assert "Ali" in sent[0]["text"] and "Madina" not in sent[0]["text"]

    def test_one_chat_in_two_kindergartens_sees_both_under_their_names(
        self, bot, tenant_a, tenant_b
    ):
        _link(tenant_a)
        _link(tenant_b, first="Zarina")
        _outcome, sent = _send(_text("💰 Balans"))
        body = sent[0]["text"]
        assert tenant_a.organization.name in body and tenant_b.organization.name in body
        assert "Ali" in body and "Zarina" in body

    def test_an_archived_guardian_gets_nothing(self, bot, tenant_a):
        guardian, _child, _invoice = _link(tenant_a)
        with organization_context(tenant_a.organization.id):
            Guardian.objects.filter(pk=guardian.pk).update(is_active=False)
        assert _send(_text("💰 Balans"))[0] == "ignored"

    def test_stop_silences_the_bot_and_drops_the_chat_from_the_index(self, bot, tenant_a):
        _link(tenant_a)
        assert _send(_text("/stop"))[0] == "stopped"
        assert _send(_text("💰 Balans"))[0] == "ignored"
        with platform_context():
            assert not ContactIndex.all_objects.filter(kind="chat").exists()


class TestPhoneLinking:
    def test_own_phone_links_the_chat(self, bot, tenant_a):
        guardian, *_ = _family(tenant_a, phone="+998901112233")
        outcome, sent = _send(_contact("998901112233"))
        assert outcome == "linked_by_phone"
        assert "keyboard" in sent[0]["reply_markup"]
        with organization_context(tenant_a.organization.id):
            guardian.refresh_from_db()
        assert guardian.telegram_chat_id == str(CHAT)
        assert _send(_text("💰 Balans"))[0] == "balance"

    def test_a_forwarded_contact_links_nobody(self, bot, tenant_a):
        guardian, *_ = _family(tenant_a, phone="+998901112233")
        assert _send(_contact("+998901112233", owner=999))[0] == "not_own_phone"
        with organization_context(tenant_a.organization.id):
            guardian.refresh_from_db()
        assert guardian.telegram_chat_id == ""

    def test_an_unknown_phone_says_so(self, bot, tenant_a):
        assert _send(_contact("+998935554433"))[0] == "phone_unknown"

    def test_the_phone_links_only_where_it_is_registered(self, bot, tenant_a, tenant_b):
        _family(tenant_a, phone="+998901112233")
        other, *_ = _family(tenant_b, phone="+998907778899")
        _send(_contact("+998901112233"))
        with organization_context(tenant_b.organization.id):
            other.refresh_from_db()
        assert other.telegram_chat_id == ""

    def test_a_legacy_unnormalised_phone_is_still_found(self, bot, tenant_a):
        guardian, *_ = _family(tenant_a, phone="+998901112233")
        with organization_context(tenant_a.organization.id):
            Guardian.objects.filter(pk=guardian.pk).update(phone="90 111 22 33")
        call_command("rebuild_contact_index", "--apply", stdout=StringIO())
        assert _send(_contact("+998901112233"))[0] == "linked_by_phone"

    def test_plain_start_offers_the_phone_button(self, bot):
        outcome, sent = _send(_text("/start", language="ru"))
        assert outcome == "help"
        (button,) = sent[0]["reply_markup"]["keyboard"][0]
        assert button["request_contact"] is True
        assert "Здравствуйте" in sent[0]["text"]


class TestIndex:
    def test_no_phone_or_chat_id_is_stored(self, bot, tenant_a):
        _link(tenant_a, phone="+998901112233")
        with platform_context():
            digests = list(ContactIndex.all_objects.values_list("digest", flat=True))
        assert digests and all(len(d) == 64 for d in digests)
        assert not any("901112233" in d or str(CHAT) in d for d in digests)

    def test_another_tenant_cannot_read_the_rows(self, bot, tenant_a, tenant_b):
        _link(tenant_a)
        with organization_context(tenant_b.organization.id):
            assert not ContactIndex.all_objects.exists()

    def test_rebuild_is_a_dry_run_by_default(self, bot, tenant_a):
        _family(tenant_a)
        with platform_context():
            ContactIndex.all_objects.all().delete()
        out = StringIO()
        call_command("rebuild_contact_index", stdout=out)
        assert "Dry run" in out.getvalue()
        with platform_context():
            assert not ContactIndex.all_objects.exists()
        call_command("rebuild_contact_index", "--apply", stdout=StringIO())
        with platform_context():
            assert ContactIndex.all_objects.filter(kind="phone").count() == 1

    def test_rebuild_drops_rows_nobody_accounts_for(self, bot, tenant_a):
        guardian, *_ = _family(tenant_a, phone="+998901112233")
        with organization_context(tenant_a.organization.id):
            guardian.phone = "+998907770000"
            guardian.save()
        call_command("rebuild_contact_index", "--apply", stdout=StringIO())
        with platform_context():
            assert ContactIndex.all_objects.filter(kind="phone").count() == 1
