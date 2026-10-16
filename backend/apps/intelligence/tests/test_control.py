"""
Nazorat: tekshiruvlar, "Diqqat" va darhol xabarlar (Bosqich 13.4,
brif §7, test 12).

Bitta reyestr: har qoida — id, jiddiylik, sarlavha, izoh, chegara
(sozlama). Tekshiruv yashil/qizil; "Diqqat" — g'ayrioddiy holat, dalili
bilan. Darhol xabarlar egaga Telegram'da, kunlik xulosa — sozlangan soatda.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
from django.utils import timezone

from apps.attendance.models import AttendanceRecord
from apps.cash.models import CashAccount
from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.expenses.models import Expense, ExpenseCategory
from apps.expenses.services import approve_expense
from apps.finance import services as finance
from apps.finance.models import TariffPlan
from apps.intelligence import alerts, control

pytestmark = pytest.mark.django_db

TODAY = timezone.localdate()
YEAR, MONTH = TODAY.year, TODAY.month


@pytest.fixture
def org(tenant_a: Any) -> Any:
    tenant_a.fund(kind="all")
    return tenant_a


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    messages: list[tuple[str, str]] = []
    monkeypatch.setattr(alerts, "_send", lambda chat, text: messages.append((chat, text)))
    # Xabar tranzaksiya tasdiqlangach ketadi; test tranzaksiyasi esa hech
    # qachon tasdiqlanmaydi — shuning uchun bu yerda darhol.
    monkeypatch.setattr(alerts, "transaction", SimpleNamespace(on_commit=lambda fn: fn()))
    return messages


def _ctx(tenant: Any) -> Any:
    return organization_context(tenant.organization.id)


def _expense(
    tenant: Any, amount: str, *, name: str = "Bozor", day: date = TODAY, receipt: str = ""
) -> Expense:
    with _ctx(tenant):
        category, _ = ExpenseCategory.objects.get_or_create(
            organization=tenant.organization, branch=tenant.branch, name=name
        )
        till = CashAccount.objects.get(branch=tenant.branch, kind="cash", is_active=True)
        expense = Expense.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            category=category,
            amount=Decimal(amount),
            expense_date=day,
            cash_account=till,
            receipt=receipt,
        )
        approve_expense(expense=expense, approved_by=tenant.owner)
        return expense


def _items(tenant: Any) -> list[dict[str, Any]]:
    with _ctx(tenant):
        return control.attention(organization_id=tenant.organization.id, year=YEAR, month=MONTH)


def _checks(tenant: Any) -> dict[str, dict[str, Any]]:
    with _ctx(tenant):
        rows = control.checks(organization_id=tenant.organization.id, year=YEAR, month=MONTH)
    return {row["id"]: row for row in rows}


# --- Tekshiruvlar ---


def test_every_check_has_an_answer_and_a_definition(org: Any):
    rows = _checks(org)
    for key in (
        "revenue_equation",
        "cash_bridge",
        "negative_balance",
        "transit_on_time",
        "benefits_have_reason",
        "big_expense_documents",
        "cash_counts",
        "bank_statement",
    ):
        assert key in rows, key
        assert rows[key]["status"] in ("ok", "fail", "na")
        assert rows[key]["title"]


def test_a_big_expense_without_a_receipt_turns_its_check_red(org: Any):
    assert _checks(org)["big_expense_documents"]["status"] == "ok"
    _expense(org, "1500000")
    row = _checks(org)["big_expense_documents"]
    assert row["status"] == "fail"
    assert "1" in row["detail"]


def test_a_negative_pot_turns_red(org: Any):
    from apps.cash import services as cash

    with _ctx(org):
        till = CashAccount.objects.get(branch=org.branch, kind="cash", is_active=True)
        cash.adjust_balance(account=till, amount=Decimal("-200000000"), reason="Sinov")
    assert _checks(org)["negative_balance"]["status"] == "fail"


# --- Diqqat ---


def test_12_a_child_in_attendance_with_a_zero_invoice_needs_attention(org: Any):
    from apps.finance.models import Discount

    with _ctx(org):
        tariff = TariffPlan.objects.create(
            organization=org.organization,
            branch=org.branch,
            name="Asosiy",
            amount=Decimal("3050000"),
        )
        child = Child.objects.create(
            organization=org.organization,
            branch=org.branch,
            first_name="Ali",
            last_name="Valiyev",
            date_of_birth=date(2021, 3, 14),
            gender="male",
            tariff=tariff,
            is_existing_client=True,
        )
        Discount.objects.create(
            organization=org.organization,
            branch=org.branch,
            child=child,
            kind="low_income",
            discount_type="percent",
            value=Decimal("0"),
            reason="Maʼlumotnoma",
            valid_from=TODAY.replace(day=1),
        )
        invoice = finance.issue_invoice(child=child, period_year=YEAR, period_month=MONTH)
        assert invoice.amount_due == 0
        AttendanceRecord.objects.create(
            organization=org.organization,
            branch=org.branch,
            child=child,
            attendance_date=TODAY.replace(day=1),
            status="present",
        )
    rules = {item["rule"] for item in _items(org)}
    assert "attendance_without_invoice" in rules


def test_an_expense_without_a_document_over_the_limit_needs_attention(org: Any):
    _expense(org, "1500000")
    _expense(org, "900000", name="Non")
    items = [item for item in _items(org) if item["rule"] == "expense_without_document"]
    assert len(items) == 1
    assert Decimal(items[0]["amount"]) == Decimal("1500000")


def test_the_same_expense_twice_is_flagged(org: Any):
    _expense(org, "300000")
    _expense(org, "300000")
    assert any(item["rule"] == "duplicate_expense" for item in _items(org))


def test_small_expenses_adding_up_past_the_limit_are_flagged(org: Any):
    for _ in range(3):
        _expense(org, "400000", name="Taʼmir", receipt="r.png")
    assert any(item["rule"] == "split_expenses" for item in _items(org))


def test_a_write_off_is_listed_with_its_reason(org: Any):
    with _ctx(org):
        tariff = TariffPlan.objects.create(
            organization=org.organization,
            branch=org.branch,
            name="Asosiy",
            amount=Decimal("3050000"),
        )
        child = Child.objects.create(
            organization=org.organization,
            branch=org.branch,
            first_name="Ali",
            last_name="Valiyev",
            date_of_birth=date(2021, 3, 14),
            gender="male",
            tariff=tariff,
            is_existing_client=True,
        )
        invoice = finance.issue_invoice(child=child, period_year=YEAR, period_month=MONTH)
        finance.write_off_invoice(
            invoice=invoice, amount=Decimal("50000"), reason="Yaxlitlash", created_by=org.owner
        )
    item = next(item for item in _items(org) if item["rule"] == "write_off")
    assert "Yaxlitlash" in item["message"]


def test_every_attention_rule_explains_itself(org: Any):
    _expense(org, "1500000")
    for item in _items(org):
        assert (
            item["title"]
            and item["message"]
            and item["severity"] in ("info", "warning", "critical")
        )


# --- Darhol xabarlar ---


def _link_owner(tenant: Any, chat: str = "9001") -> None:
    from apps.accounts.models import User

    with _ctx(tenant):
        User.objects.filter(pk=tenant.owner.pk).update(telegram_chat_id=chat)


def test_a_big_expense_reaches_the_owner_at_once(org: Any, sent: list):
    _link_owner(org)
    _expense(org, "6000000", receipt="r.png")
    assert any("6 000 000" in text for _chat, text in sent)


def test_a_small_expense_does_not_disturb_the_owner(org: Any, sent: list):
    _link_owner(org)
    _expense(org, "200000", receipt="r.png")
    assert sent == []


def test_a_write_off_reaches_the_owner(org: Any, sent: list):
    _link_owner(org)
    with _ctx(org):
        tariff = TariffPlan.objects.create(
            organization=org.organization,
            branch=org.branch,
            name="Asosiy",
            amount=Decimal("3050000"),
        )
        child = Child.objects.create(
            organization=org.organization,
            branch=org.branch,
            first_name="Ali",
            last_name="Valiyev",
            date_of_birth=date(2021, 3, 14),
            gender="male",
            tariff=tariff,
            is_existing_client=True,
        )
        invoice = finance.issue_invoice(child=child, period_year=YEAR, period_month=MONTH)
        finance.write_off_invoice(
            invoice=invoice, amount=Decimal("50000"), reason="Yaxlitlash", created_by=org.owner
        )
    assert any("Yaxlitlash" in text for _chat, text in sent)


def test_the_daily_digest_sums_the_day(org: Any, sent: list):
    _link_owner(org)
    _expense(org, "200000", receipt="r.png")
    with _ctx(org):
        delivered = alerts.send_digest(organization=org.organization, day=TODAY)
    assert delivered == 1
    assert "200 000" in sent[-1][1]


# --- Bosh sahifa va kunlik ko'rinish ---


def test_home_answers_the_six_questions(org: Any):
    data = org.client().get("/api/v1/reports/home").json()["data"]
    assert [card["key"] for card in data["cards"]] == [
        "money",
        "debts",
        "spending",
        "profit",
        "checks",
        "growth",
    ]
    for card in data["cards"]:
        assert card["status"] in ("ok", "warning", "critical")
        assert card["note"]
    assert "all_clear" in data


def test_the_daily_view_shows_the_day(org: Any):
    _expense(org, "200000", receipt="r.png")
    data = org.client().get("/api/v1/reports/daily", {"date": TODAY.isoformat()}).json()["data"]
    assert Decimal(data["expenses"]["total"]) == Decimal("200000")
    assert "receipts" in data and "attention" in data


def test_a_cashier_does_not_see_the_home_page(org: Any):
    from rest_framework.test import APIClient

    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.models import User

    with _ctx(org):
        user = User.objects.create_user(
            email="kassir@alfa.uz",
            password="Juda-Kuchli-Parol-2026",  # noqa: S106
            full_name="Kassir",
            organization=org.organization,
            role=org.role("cashier"),
            branch=org.branch,
        )
        tokens = issue_token_pair(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert client.get("/api/v1/reports/home").status_code == 403


@pytest.mark.tenancy
def test_another_tenants_attention_never_shows(org: Any, tenant_b: Any):
    _expense(org, "1500000")
    data = (
        tenant_b.client()
        .get(
            "/api/v1/reports/attention",
            {"year": YEAR, "month": MONTH, "branch": str(org.branch.id)},
        )
        .json()["data"]
    )
    assert data["items"] == []


def test_the_digest_task_runs_only_at_the_chosen_hour(
    org: Any, sent: list, monkeypatch: pytest.MonkeyPatch
):
    from apps.intelligence.tasks import send_daily_digests
    from apps.settings_app.services import set_setting

    _link_owner(org)
    now = timezone.localtime()
    with _ctx(org):
        set_setting(
            organization=org.organization, key="alerts.digest_hour", value=(now.hour + 1) % 24
        )
    assert send_daily_digests()["delivered"] == 0
    with _ctx(org):
        set_setting(organization=org.organization, key="alerts.digest_hour", value=now.hour)
    assert send_daily_digests()["delivered"] == 1
