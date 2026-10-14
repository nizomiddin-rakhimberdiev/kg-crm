"""
Ikki qop: naqd va bank (mijoz soʻrovi, 2026-10-14).

Toʻlov USULI va pul tushgan QOP — ikki xil savol. Usul hisobot uchun
yoziladi ("bu oy terminal orqali qancha keldi?"); qop esa pul
haqiqatan qayerda turganini aytadi. Terminal, oʻtkazma va Payme/Click
orqali kelgan pul bogʻchaning bitta bank hisobiga tushadi — shuning
uchun ular uchun alohida qop ochish chiqimni "bankda pul yoʻq" deb
toʻxtatib qoʻyardi, holbuki pul bankda turibdi.

Mijozning oʻz soʻzi: *"barcha pullar bank hisobiga qoʻshilib borishi
kerak"*.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from io import StringIO
from typing import Any

import pytest
from django.core.management import call_command

from apps.cash import selectors
from apps.cash import services as cash
from apps.cash.models import CashAccount, MovementDirection, MovementSource
from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.expenses import services as expenses
from apps.expenses.models import ExpenseCategory
from apps.finance import services as finance
from apps.finance.models import Payment

pytestmark = pytest.mark.django_db


def _child(tenant: Any) -> Child:
    with organization_context(tenant.organization.id):
        return Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Ali",
            last_name="Valiyev",
            date_of_birth=date(2021, 3, 14),
            gender="male",
        )


def _balances(tenant: Any) -> dict[str, Decimal]:
    rows = selectors.account_balances(organization_id=tenant.organization.id)
    return {row["kind"]: Decimal(row["balance"]) for row in rows}


def _old_pot(tenant: Any, *, name: str, kind: str, method: str) -> CashAccount:
    """Oʻzgarishdan oldin ochilgan qop — productionda shunday qoplar bor."""
    with organization_context(tenant.organization.id):
        return CashAccount.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            name=name,
            kind=kind,
            handles_method=method,
        )


def _put(tenant: Any, account: CashAccount, amount: str) -> None:
    with organization_context(tenant.organization.id):
        cash.post_movement(
            account=account,
            direction=MovementDirection.IN,
            amount=Decimal(amount),
            source_type=MovementSource.PAYMENT,
            description="eski toʻlov",
        )


# --- Yangi filial ---


def test_a_new_branch_has_exactly_two_pots(tenant_a: Any):
    with organization_context(tenant_a.organization.id):
        accounts = CashAccount.objects.filter(branch=tenant_a.branch, is_active=True)
        assert sorted(a.kind for a in accounts) == ["bank", "cash"]


# --- Toʻlov: usul hisobot uchun, pul ikki qopdan biriga ---


@pytest.mark.parametrize("method", ["terminal", "bank_transfer", "online"])
def test_non_cash_payment_lands_in_the_bank(tenant_a: Any, method: str):
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        finance.record_payment(child=child, amount=Decimal("500000"), method=method)
        balances = _balances(tenant_a)
        payment = Payment.objects.get(child=child)

    assert balances == {"cash": Decimal("0"), "bank": Decimal("500000.00")}
    # Usul yoʻqolmaydi — hisobot "nimadan qancha keldi" ni shundan oladi.
    assert payment.method == method


def test_cash_payment_lands_in_the_till(tenant_a: Any):
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        finance.record_payment(child=child, amount=Decimal("300000"), method="cash")
        balances = _balances(tenant_a)

    assert balances == {"cash": Decimal("300000.00"), "bank": Decimal("0")}


def test_terminal_money_can_be_spent_from_the_bank(tenant_a: Any):
    """Mijoz koʻrgan nosozlikning oʻzi: terminalda olingan pul bankdan chiqim qilinmasdi."""
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        finance.record_payment(child=child, amount=Decimal("1440909"), method="terminal")
        bank = CashAccount.objects.get(branch=tenant_a.branch, kind="bank", is_active=True)
        category = ExpenseCategory.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Bozorlik"
        )
        expenses.create_expense_with_items(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            category=category,
            expense_date=date(2026, 10, 14),
            items=[{"name": "Goʻsht", "quantity": "10", "unit": "kg", "unit_price": "95000"}],
            cash_account=bank,
        )
        balances = _balances(tenant_a)

    assert balances["bank"] == Decimal("490909.00")


# --- Mavjud maʼlumot: birlashtirish buyrugʻi ---


def _run(*args: str) -> str:
    out = StringIO()
    call_command("consolidate_cash_accounts", *args, stdout=out)
    return out.getvalue()


def test_consolidation_dry_run_changes_nothing(tenant_a: Any):
    terminal = _old_pot(tenant_a, name="Terminal", kind="terminal", method="terminal")
    _put(tenant_a, terminal, "1440909")

    report = _run()

    with organization_context(tenant_a.organization.id):
        terminal.refresh_from_db()
        balances = _balances(tenant_a)
    assert terminal.is_active is True
    assert balances["terminal"] == Decimal("1440909.00")
    assert "1 440 909" in report
    assert "dry-run" in report.lower()


def test_consolidation_moves_old_pots_into_the_bank(tenant_a: Any):
    terminal = _old_pot(tenant_a, name="Terminal", kind="terminal", method="terminal")
    wallet = _old_pot(tenant_a, name="Payme / Click", kind="ewallet", method="online")
    _put(tenant_a, terminal, "1440909")
    _put(tenant_a, wallet, "300000")
    with organization_context(tenant_a.organization.id):
        total_before = sum(_balances(tenant_a).values())

    _run("--apply")

    with organization_context(tenant_a.organization.id):
        balances = _balances(tenant_a)
        active = sorted(
            CashAccount.objects.filter(branch=tenant_a.branch, is_active=True).values_list(
                "kind", flat=True
            )
        )
    assert active == ["bank", "cash"]
    assert balances["bank"] == Decimal("1740909.00")
    # Oʻtkazma pul topmaydi va yoʻqotmaydi.
    assert sum(balances.values()) == total_before


def test_consolidation_is_append_only_and_idempotent(tenant_a: Any):
    """Hech bir eski yozuv oʻzgarmaydi; ikkinchi ishga tushirish hech narsa qilmaydi."""
    from apps.cash.models import CashMovement

    terminal = _old_pot(tenant_a, name="Terminal", kind="terminal", method="terminal")
    _put(tenant_a, terminal, "500000")
    with organization_context(tenant_a.organization.id):
        original = list(CashMovement.objects.values_list("id", "cash_account_id", "amount"))

    _run("--apply")
    with organization_context(tenant_a.organization.id):
        after_first = CashMovement.objects.count()
        still = list(
            CashMovement.objects.filter(id__in=[r[0] for r in original]).values_list(
                "id", "cash_account_id", "amount"
            )
        )
    _run("--apply")
    with organization_context(tenant_a.organization.id):
        after_second = CashMovement.objects.count()

    assert sorted(still) == sorted(original)
    assert after_first == len(original) + 2  # bitta oʻtkazma = ikki yozuv
    assert after_second == after_first


def test_consolidation_carries_a_negative_pot_into_the_bank(tenant_a: Any):
    """
    Manfiy eski qop — undan bank puli chiqarilgan degani.

    Uni nolga keltirish uchun kamomad bankka oʻtadi: pul haqiqatan
    bankdan ketgan edi. Bu tuzatish, shuning uchun bank qoldigʻi
    yetmasa ham rad etilmaydi (ADR-29).
    """
    terminal = _old_pot(tenant_a, name="Terminal", kind="terminal", method="terminal")
    with organization_context(tenant_a.organization.id):
        cash.post_movement(
            account=terminal,
            direction=MovementDirection.OUT,
            amount=Decimal("200000"),
            source_type=MovementSource.EXPENSE,
            allow_negative=True,
        )

    _run("--apply")

    with organization_context(tenant_a.organization.id):
        balances = _balances(tenant_a)
    assert balances["bank"] == Decimal("-200000.00")
    assert "terminal" not in balances


def test_consolidation_stays_inside_each_tenant(tenant_a: Any, tenant_b: Any):
    a_terminal = _old_pot(tenant_a, name="Terminal", kind="terminal", method="terminal")
    b_terminal = _old_pot(tenant_b, name="Terminal", kind="terminal", method="terminal")
    _put(tenant_a, a_terminal, "100000")
    _put(tenant_b, b_terminal, "700000")

    _run("--apply")

    with organization_context(tenant_a.organization.id):
        a = _balances(tenant_a)
    with organization_context(tenant_b.organization.id):
        b = _balances(tenant_b)
    assert a["bank"] == Decimal("100000.00")
    assert b["bank"] == Decimal("700000.00")
