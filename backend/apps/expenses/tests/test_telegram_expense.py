"""
Telegram orqali chiqim (Bosqich 13.3c, brif §4).

Xodim o'z profilidan havola oladi va botga ulanadi. Keyin summa va chek
rasmini yuboradi — toifa tugma bilan tanlanadi va chiqim naqd kassadan
yoziladi. Kod tashkilotni o'z ichida olib yuradi: webhook tenant
chegarasidan chiqmaydi (ADR-23 bilan bir xil yo'l).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from apps.accounts.models import User
from apps.core.tenancy import organization_context
from apps.expenses.models import Expense, ExpenseCategory
from apps.notifications import telegram_updates

pytestmark = pytest.mark.django_db

CHAT = "700100200"
PNG = b"\x89PNG\r\n\x1a\nfake"


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, Any]]:
    messages: list[tuple[str, str, Any]] = []
    monkeypatch.setattr(
        telegram_updates,
        "reply",
        lambda chat, text, markup=None: messages.append((chat, text, markup)),
    )
    monkeypatch.setattr("apps.expenses.telegram.download_photo", lambda file_id: PNG)
    return messages


def _link(tenant: Any, client: Any = None) -> None:
    response = (client or tenant.client()).post("/api/v1/auth/telegram")
    assert response.status_code == 200, response.json()
    url = response.json()["data"]["link"]
    code = url.split("start=", 1)[1]
    assert code.startswith("s_")
    outcome = telegram_updates.handle_update(
        {
            "message": {
                "chat": {"id": int(CHAT)},
                "from": {"id": int(CHAT)},
                "text": f"/start {code}",
            }
        }
    )
    assert outcome == "staff_linked"


def _photo(caption: str) -> dict[str, Any]:
    return {
        "message": {
            "chat": {"id": int(CHAT)},
            "from": {"id": int(CHAT)},
            "photo": [{"file_id": "small"}, {"file_id": "big"}],
            "caption": caption,
        }
    }


def _press(data: str) -> dict[str, Any]:
    return {
        "callback_query": {
            "id": "cb1",
            "from": {"id": int(CHAT)},
            "message": {"chat": {"id": int(CHAT)}},
            "data": data,
        }
    }


def test_staff_link_their_own_account(tenant_a: Any, sent: list):
    _link(tenant_a)
    with organization_context(tenant_a.organization.id):
        owner = User.objects.get(pk=tenant_a.owner.pk)
    assert owner.telegram_chat_id == CHAT
    status = tenant_a.client().get("/api/v1/auth/telegram").json()["data"]
    assert status["linked"] is True


def test_an_expense_is_a_photo_an_amount_and_one_button(tenant_a: Any, sent: list):
    tenant_a.fund(kind="all")
    with organization_context(tenant_a.organization.id):
        ExpenseCategory.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Bozorlik"
        )
    _link(tenant_a)

    assert telegram_updates.handle_update(_photo("150 000 kartoshka, piyoz")) == "expense_draft"
    _chat, _text, markup = sent[-1]
    buttons = [button for row in markup["inline_keyboard"] for button in row]
    pick = next(button for button in buttons if button["text"] == "Bozorlik")

    assert telegram_updates.handle_update(_press(pick["callback_data"])) == "expense_created"

    with organization_context(tenant_a.organization.id):
        expense = Expense.objects.select_related("category", "cash_account").get()
    assert expense.amount == Decimal("150000")
    assert expense.category.name == "Bozorlik"
    assert expense.description == "kartoshka, piyoz"
    assert expense.cash_account.kind == "cash"
    assert expense.receipt.read().startswith(b"\x89PNG")
    assert "150 000" in sent[-1][1]


def test_a_button_pressed_twice_writes_one_expense(tenant_a: Any, sent: list):
    tenant_a.fund(kind="all")
    with organization_context(tenant_a.organization.id):
        ExpenseCategory.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Non"
        )
    _link(tenant_a)
    telegram_updates.handle_update(_photo("40000"))
    data = sent[-1][2]["inline_keyboard"][0][0]["callback_data"]
    telegram_updates.handle_update(_press(data))
    telegram_updates.handle_update(_press(data))
    with organization_context(tenant_a.organization.id):
        assert Expense.objects.count() == 1


def test_without_an_amount_the_bot_asks_for_it(tenant_a: Any, sent: list):
    _link(tenant_a)
    assert telegram_updates.handle_update(_photo("bozorlik")) == "expense_needs_amount"


def test_someone_without_expense_rights_is_refused(tenant_a: Any, sent: list):
    from rest_framework.test import APIClient

    from apps.accounts.authentication import issue_token_pair

    with organization_context(tenant_a.organization.id):
        user = User.objects.create_user(
            email="davomat@alfa.uz",
            password="Juda-Kuchli-Parol-2026",  # noqa: S106
            full_name="Davomat",
            organization=tenant_a.organization,
            role=tenant_a.role("attendance_manager"),
            branch=tenant_a.branch,
        )
        tokens = issue_token_pair(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    _link(tenant_a, client)
    assert telegram_updates.handle_update(_photo("40000")) == "expense_forbidden"


def test_an_unknown_chat_sending_a_photo_is_ignored(tenant_a: Any, sent: list):
    assert telegram_updates.handle_update(_photo("40000")) == "ignored"
