"""
Rahbar uchun buyruqli bot (2026-10-20, mijoz so'rovi).

Botga ulangan xodim (13.3) "bugungi tushum", "bu oy foyda", "bu oy chiqim",
"faol bolalar" deb yozsa — raqam keladi. Sun'iy intellekt yo'q (egasining
qarori): so'zlar va davr so'zlari bo'yicha aniq moslik. Raqamlar tizimdagi
hisobotlar bilan bir xil funksiyalardan; har xodim faqat o'z roli
ko'radigan raqamni oladi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.utils import timezone

from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.finance.models import TariffPlan
from apps.reports import bot

pytestmark = pytest.mark.django_db

TODAY = timezone.localdate()


def _ctx(tenant: Any) -> Any:
    return organization_context(tenant.organization.id)


def _child(tenant: Any, name: str = "Ali") -> Child:
    with _ctx(tenant):
        tariff, _ = TariffPlan.objects.get_or_create(
            organization=tenant.organization,
            branch=tenant.branch,
            name="Asosiy",
            defaults={"amount": Decimal("3050000")},
        )
        return Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name=name,
            last_name="Valiyev",
            date_of_birth=date(2021, 3, 14),
            gender="male",
            tariff=tariff,
            enrolled_on=date(2025, 9, 1),
            is_existing_client=True,
        )


def _pay(tenant: Any, amount: str, method: str = "cash", received_by: Any = None) -> None:
    with _ctx(tenant):
        finance.record_payment(
            child=_child(tenant, f"T{amount}"),
            amount=Decimal(amount),
            method=method,
            received_by=received_by,
        )


def _ask(tenant: Any, text: str, user: Any = None) -> str | None:
    with _ctx(tenant):
        return bot.answer(user=user or tenant.owner, text=text)


def _user(tenant: Any, role: str, email: str) -> Any:
    from apps.accounts.models import User

    with _ctx(tenant):
        return User.objects.create_user(
            email=email,
            password="Juda-Kuchli-Parol-2026",  # noqa: S106
            full_name=email.split("@")[0].title(),
            organization=tenant.organization,
            role=tenant.role(role),
            branch=tenant.branch,
        )


# --- Tushunish ---


@pytest.mark.parametrize(
    ("text", "intent", "period"),
    [
        ("bugungi tushum", "revenue", "today"),
        ("Tushum", "revenue", "today"),
        ("kechagi tushum", "revenue", "yesterday"),
        ("bu oydagi foyda", "profit", "month"),
        ("foyda", "profit", "month"),
        ("oʻtgan oy foyda", "profit", "last_month"),
        ("shu oydagi chiqim", "expenses", "month"),
        ("bugungi xarajat", "expenses", "today"),
        ("faol bolalar soni", "children", "today"),
        ("Bolalar", "children", "today"),
        ("qarzdorlik", "debts", "today"),
        ("kassada qancha pul bor", "cash", "today"),
        ("выручка за сегодня", "revenue", "today"),
        ("прибыль за месяц", "profit", "month"),
        ("расход за неделю", "expenses", "week"),
        ("тушум", "revenue", "today"),
        ("profit last month", "profit", "last_month"),
    ],
)
def test_the_question_is_understood(text: str, intent: str, period: str):
    assert bot.classify(text) == (intent, period)


@pytest.mark.parametrize("text", ["150 000 kartoshka", "", "1234"])
def test_other_text_is_not_a_question(text: str):
    assert bot.classify(text) is None


# --- Javoblar ---


def test_todays_revenue_is_the_sum_of_todays_payments(tenant_a: Any):
    _pay(tenant_a, "1000000")
    _pay(tenant_a, "440909", method="terminal")
    reply = _ask(tenant_a, "bugungi tushum")
    assert reply is not None
    assert "1 440 909" in reply


def test_this_months_profit_is_the_pnl_figure(tenant_a: Any):
    from apps.reports import money

    _pay(tenant_a, "500000")
    with _ctx(tenant_a):
        pnl = money.profit_and_loss(
            organization_id=tenant_a.organization.id, year=TODAY.year, month=TODAY.month
        )
    expected = f"{int(Decimal(pnl['operating_profit'])):,}".replace(",", " ").replace("-", "−")
    reply = _ask(tenant_a, "bu oy foyda")
    assert reply is not None
    assert expected in reply


def test_this_months_expenses(tenant_a: Any):
    from apps.cash.models import CashAccount
    from apps.expenses.models import Expense, ExpenseCategory
    from apps.expenses.services import approve_expense

    tenant_a.fund("10000000")
    with _ctx(tenant_a):
        category = ExpenseCategory.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Bozor"
        )
        expense = Expense.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            category=category,
            amount=Decimal("750000"),
            expense_date=TODAY,
            cash_account=CashAccount.objects.get(branch=tenant_a.branch, kind="cash"),
            receipt="r.png",
        )
        approve_expense(expense=expense, approved_by=tenant_a.owner)
    reply = _ask(tenant_a, "shu oydagi chiqim")
    assert reply is not None
    assert "750 000" in reply
    assert "Bozor" in reply


def test_active_children(tenant_a: Any):
    _child(tenant_a, "A")
    _child(tenant_a, "B")
    reply = _ask(tenant_a, "faol bolalar")
    assert reply is not None
    assert "2" in reply


def test_help_lists_what_can_be_asked(tenant_a: Any):
    reply = _ask(tenant_a, "/help")
    assert reply is not None
    assert "tushum" in reply.lower()


def test_unknown_text_is_left_alone(tenant_a: Any):
    assert _ask(tenant_a, "1234") is None


# --- Mijozning haqiqiy savollari (2026-10-21, skrinshot) ---


@pytest.mark.parametrize(
    ("text", "intent", "period"),
    [
        ("bu oy qancha daromad qildik?", "revenue", "month"),
        ("bu oy qancha chiqim boʻldi", "expenses", "month"),
        ("kunlik hisobotni ber", "summary", "today"),
        ("kunlik hisobot qanaqa", "summary", "today"),
        ("qarzdorliklar qancha", "debts", "today"),
        ("obuna summasi qancha?", "subscription", "month"),
        ("bugun nechta bola keldi", "attendance", "today"),
        ("davomat qanaqa", "attendance", "today"),
        ("xodimlar soni", "staff", "today"),
        ("bu oy oylik maosh qancha", "payroll", "month"),
        ("tushm", "revenue", "today"),
        ("bugungi chiqm", "expenses", "today"),
        ("umumiy holat", "summary", "today"),
        ("kassada pul qancha", "cash", "today"),
    ],
)
def test_the_customers_own_questions_are_understood(text: str, intent: str, period: str):
    assert bot.classify(text) == (intent, period)


def test_a_vague_question_gets_the_help(tenant_a: Any):
    reply = _ask(tenant_a, "nima")
    assert reply is not None
    assert "tushum" in reply.lower()


def test_a_greeting_is_answered_with_the_help(tenant_a: Any):
    reply = _ask(tenant_a, "salom")
    assert reply is not None
    assert "tushum" in reply.lower()


def test_the_daily_summary(tenant_a: Any):
    _pay(tenant_a, "600000")
    reply = _ask(tenant_a, "kunlik hisobotni ber")
    assert reply is not None
    assert "600 000" in reply
    assert "Chiqim" in reply


def test_the_subscription_amount_for_the_owner(tenant_a: Any):
    reply = _ask(tenant_a, "obuna summasi qancha?")
    assert reply is not None
    assert "soʻm" in reply


def test_a_cashier_gets_no_subscription_figure(tenant_a: Any):
    cashier = _user(tenant_a, "cashier", "kassir@alfa.uz")
    reply = _ask(tenant_a, "obuna summasi qancha?", cashier)
    assert reply is not None
    assert "ruxsat" in reply.lower()


def test_todays_attendance(tenant_a: Any):
    reply = _ask(tenant_a, "bugun nechta bola keldi")
    assert reply is not None
    assert "Keldi" in reply


# --- Huquqlar ---


def test_a_cashier_cannot_ask_for_profit(tenant_a: Any):
    cashier = _user(tenant_a, "cashier", "kassir@alfa.uz")
    reply = _ask(tenant_a, "bu oy foyda", cashier)
    assert reply is not None
    assert "ruxsat" in reply.lower()


def test_an_own_only_cashier_hears_only_their_own_takings(tenant_a: Any):
    cashier = _user(tenant_a, "cashier", "kassir@alfa.uz")
    _pay(tenant_a, "300000", received_by=cashier)
    _pay(tenant_a, "900000", received_by=tenant_a.owner)
    reply = _ask(tenant_a, "bugungi tushum", cashier)
    assert reply is not None
    assert "300 000" in reply
    assert "1 200 000" not in reply


@pytest.mark.tenancy
def test_another_tenants_money_is_never_counted(tenant_a: Any, tenant_b: Any):
    _pay(tenant_a, "777000")
    reply = _ask(tenant_b, "bugungi tushum")
    assert reply is not None
    assert "777 000" not in reply


# --- Telegram orqali ---


def test_a_linked_staff_chat_gets_the_answer(tenant_a: Any, monkeypatch: Any):
    from apps.accounts.models import User
    from apps.notifications import telegram_updates

    sent: list[str] = []
    monkeypatch.setattr(telegram_updates, "reply", lambda chat, text, *a, **k: sent.append(text))
    with _ctx(tenant_a):
        User.objects.filter(pk=tenant_a.owner.pk).update(telegram_chat_id="5005")
    _remember_staff(tenant_a, "5005")
    _pay(tenant_a, "250000")

    outcome = telegram_updates.handle_update(
        {"message": {"chat": {"id": 5005}, "text": "bugungi tushum", "from": {}}}
    )
    assert outcome == "staff_query"
    assert any("250 000" in text for text in sent)


def _remember_staff(tenant: Any, chat: str) -> None:
    """Xodim chat'ini ContactIndex'ga yozadi — haqiqiy ulanish (13.3) kabi."""
    from apps.accounts import telegram as staff

    with _ctx(tenant):
        code = staff.link_url(tenant.owner).rsplit("start=", 1)[-1]
    assert staff.link_staff(code=code, chat_id=chat) is not None


@pytest.mark.parametrize("language", ["uz", "ru", "en"])
def test_every_example_in_the_help_is_understood(language: str):
    """Yordam matni o'zi tanimaydigan savolni maslahat bermasin."""
    from django.utils import translation

    with translation.override(language):
        examples = [line[2:] for line in bot.help_text().splitlines() if line.startswith("• ")]
    assert len(examples) == 13
    for example in examples:
        assert bot.classify(example) is not None, (language, example)


def _link_guardian_chat(tenant: Any, chat: str) -> None:
    """Shu chat ota-ona sifatida ham ulangan (egasi test qilgan holat)."""
    from apps.children.models import ChildGuardian, Guardian
    from apps.children.telegram import build_code, link_from_start

    with _ctx(tenant):
        guardian = Guardian.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Ota",
            last_name="Ona",
            phone="+998901112233",
        )
        ChildGuardian.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            child=_child(tenant, "Farzand"),
            guardian=guardian,
            is_primary=True,
        )
        guardian.telegram_code = build_code(tenant.organization.id)
        guardian.save(update_fields=["telegram_code"])
        code = guardian.telegram_code
    assert link_from_start(code=code, chat_id=chat) is not None


def test_a_staff_chat_never_gets_the_parent_menu_for_free_text(tenant_a: Any, monkeypatch: Any):
    from apps.notifications import telegram_updates

    sent: list[str] = []
    monkeypatch.setattr(telegram_updates, "reply", lambda chat, text, *a, **k: sent.append(text))
    _remember_staff(tenant_a, "6006")
    _link_guardian_chat(tenant_a, "6006")

    outcome = telegram_updates.handle_update(
        {"message": {"chat": {"id": 6006}, "text": "bu nima ekan", "from": {}}}
    )
    assert outcome == "staff_help"
    assert not any("tugmalardan birini" in text for text in sent)


def test_a_parent_button_still_reaches_the_parent_bot(tenant_a: Any, monkeypatch: Any):
    from apps.notifications import telegram_updates

    sent: list[str] = []
    monkeypatch.setattr(telegram_updates, "reply", lambda chat, text, *a, **k: sent.append(text))
    _remember_staff(tenant_a, "7007")
    _link_guardian_chat(tenant_a, "7007")

    outcome = telegram_updates.handle_update(
        {"message": {"chat": {"id": 7007}, "text": "💰 Balans", "from": {}}}
    )
    assert outcome not in ("staff_help", "staff_query")
