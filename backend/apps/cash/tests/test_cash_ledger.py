"""
Kassa jurnali (ADR-17, docs/03 §13a).

Bu jurnal "hozir qoʻlimizda qancha pul bor?" degan savolga javob beradi,
va u pul haqidagi savol — shuning uchun testlar ikki narsani qattiq
ushlaydi: **qoldiq yozuvlardan hisoblanadi** va **hech bir yozuv
o'zgartirilmaydi**.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.utils import timezone

from apps.cash import selectors
from apps.cash import services as cash
from apps.cash.models import CashAccount, CashMovement, MovementDirection, MovementSource
from apps.children.models import Child
from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context
from apps.expenses import services as expenses
from apps.expenses.models import Expense, ExpenseCategory
from apps.finance import services as finance

pytestmark = pytest.mark.django_db


def _child(tenant: Any, name: str = "Ali") -> Child:
    with organization_context(tenant.organization.id):
        return Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name=name,
            last_name="Valiyev",
            date_of_birth=date(2021, 3, 14),
            gender="male",
        )


def _balances(tenant: Any) -> dict[str, Decimal]:
    rows = selectors.account_balances(organization_id=tenant.organization.id)
    return {row["kind"]: Decimal(row["balance"]) for row in rows}


# --- Qoplar ---


def test_branch_is_born_with_two_accounts(tenant_a: Any):
    """
    Roʻyxatdan oʻtish paytida ochiladi — birinchi toʻlovdan oldin.

    Ikkita: naqd va bank (mijoz soʻrovi, 2026-10-14). Terminal va
    Payme/Click puli bankka tushadi — `test_two_pots.py`.
    """
    with organization_context(tenant_a.organization.id):
        accounts = CashAccount.objects.filter(branch=tenant_a.branch, is_active=True)
        assert {a.kind for a in accounts} == {"cash", "bank"}
        assert {a.handles_method for a in accounts} == {"cash", "bank_transfer"}


def test_ensure_accounts_is_idempotent_and_keeps_renames(tenant_a: Any):
    """
    Bog'cha qopni qayta nomlagan bo'lsa, u shundayligicha qoladi.

    Funksiya har safar chaqirilishi mumkin (filial yaratish, to'lovda
    o'zini-o'zi tuzatish), shuning uchun u FAQAT yo'q qopni qo'shadi.
    """
    with organization_context(tenant_a.organization.id):
        account = CashAccount.objects.get(branch=tenant_a.branch, kind="cash")
        account.name = "Kassa №1"
        account.save(update_fields=["name"])

        created = cash.ensure_branch_accounts(branch=tenant_a.branch)
        account.refresh_from_db()

    assert created == []
    assert account.name == "Kassa №1"


def test_one_account_per_method_is_enforced_by_the_database(tenant_a: Any):
    """Ikkita qop `cash` ni daʼvo qilsa, pul qayerga tushgani tanga tashlash boʻlardi."""
    from django.db import IntegrityError

    with organization_context(tenant_a.organization.id), pytest.raises(IntegrityError):
        CashAccount.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            name="Ikkinchi kassa",
            kind="cash",
            handles_method="cash",
        )


# --- To'lovlar ---


def test_payment_lands_in_the_account_for_its_method(tenant_a: Any):
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        finance.record_payment(child=child, amount=Decimal("1400000"), method="cash")
        finance.record_payment(child=child, amount=Decimal("100000"), method="terminal")

        balances = _balances(tenant_a)

    assert balances["cash"] == Decimal("1400000.00")
    assert balances["bank"] == Decimal("100000.00")


def test_reversal_adds_a_counter_movement_and_keeps_the_original(tenant_a: Any):
    """
    Qaytarish — qarshi yozuv, o'chirish EMAS (D3).

    Jurnal "pul kirdi, keyin qaytarildi" deb ko'rsatishi kerak, "hech
    narsa bo'lmagan" emas.
    """
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        payment = finance.record_payment(child=child, amount=Decimal("500000"), method="cash")
        finance.reverse_payment(payment=payment, reason="Xato summa")

        movements = list(
            CashMovement.objects.filter(
                source_type=MovementSource.PAYMENT, source_id=payment.id
            ).order_by("created_at")
        )
        balances = _balances(tenant_a)

    assert [m.direction for m in movements] == [MovementDirection.IN, MovementDirection.OUT]
    assert balances["cash"] == Decimal("0.00")


def test_reversing_twice_does_not_double_the_counter_entry(tenant_a: Any):
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        payment = finance.record_payment(child=child, amount=Decimal("500000"), method="cash")
        finance.reverse_payment(payment=payment, reason="Birinchi")
        # Ikkinchi urinish biznes qoidasi bilan to'xtaydi; kassa ham
        # ikkinchi qarshi yozuvni olmaydi.
        with pytest.raises(BusinessRuleViolation):
            finance.reverse_payment(payment=payment, reason="Ikkinchi")

        assert _balances(tenant_a)["cash"] == Decimal("0.00")


# --- Chiqimlar ---


def test_approving_an_expense_is_what_moves_the_money(tenant_a: Any):
    """
    Pul TASDIQLASHDA chiqadi, "toʻlandi" tugmasida emas.

    Hisobotlar boshidan beri `approved` ni xarajat deb sanaydi. Kassa
    faqat `paid` da kamasa, ikkita ekran bir xil savolga ikki xil javob
    berardi — ko'p bog'cha esa "toʻlandi" tugmasini umuman bosmaydi.
    """
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        finance.record_payment(child=child, amount=Decimal("2000000"), method="cash")
        category = ExpenseCategory.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Kommunal"
        )
        expense = Expense.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            category=category,
            amount=Decimal("300000"),
            expense_date=timezone.localdate(),
        )
        expenses.approve_expense(expense=expense, approved_by=None)
        assert _balances(tenant_a)["cash"] == Decimal("1700000.00")

        # "Toʻlandi" — faqat bayroq. Pul IKKINCHI marta chiqmaydi.
        expenses.mark_expense_paid(expense=expense)
        assert _balances(tenant_a)["cash"] == Decimal("1700000.00")


def test_paid_expense_leaves_the_till(tenant_a: Any):
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        finance.record_payment(child=child, amount=Decimal("2000000"), method="cash")
        category = ExpenseCategory.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Kommunal"
        )
        expense = Expense.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            category=category,
            amount=Decimal("300000"),
            expense_date=timezone.localdate(),
        )
        expenses.approve_expense(expense=expense, approved_by=None)
        expenses.mark_expense_paid(expense=expense)
        expense.refresh_from_db()

        assert expense.cash_account is not None
        assert _balances(tenant_a)["cash"] == Decimal("1700000.00")


def test_a_pending_request_does_not_move_money(tenant_a: Any):
    """Tasdiqlanmagan soʻrov hali pul emas — u kassadan chiqmagan."""
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        finance.record_payment(child=child, amount=Decimal("2000000"), method="cash")
        category = ExpenseCategory.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Taʼmirlash"
        )
        Expense.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            category=category,
            amount=Decimal("900000"),
            expense_date=timezone.localdate(),
        )
        assert _balances(tenant_a)["cash"] == Decimal("2000000.00")


# --- O'tkazma ---


def test_transfer_moves_money_between_pots_without_changing_the_total(tenant_a: Any):
    """Kun oxirida naqdni bankka topshirish — jami oʻzgarmasligi SHART."""
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        finance.record_payment(child=child, amount=Decimal("3000000"), method="cash")
        before = selectors.total_balance(organization_id=tenant_a.organization.id)

        till = CashAccount.objects.get(branch=tenant_a.branch, kind="cash")
        bank = CashAccount.objects.get(branch=tenant_a.branch, kind="bank")
        cash.transfer(source=till, target=bank, amount=Decimal("2500000"))

        after = selectors.total_balance(organization_id=tenant_a.organization.id)
        balances = _balances(tenant_a)

    assert before == after == Decimal("3000000.00")
    assert balances["cash"] == Decimal("500000.00")
    assert balances["bank"] == Decimal("2500000.00")


def test_transfer_to_the_same_account_is_refused(tenant_a: Any):
    with organization_context(tenant_a.organization.id):
        till = CashAccount.objects.get(branch=tenant_a.branch, kind="cash")
        with pytest.raises(BusinessRuleViolation):
            cash.transfer(source=till, target=till, amount=Decimal("100"))


# --- Tenant chegarasi ---


@pytest.mark.tenancy
def test_balances_never_mix_organizations(tenant_a: Any, tenant_b: Any):
    """
    Ikki bog'chaning pulini qo'shib yuborish — bazadan sizib chiqish
    emas, lekin ekranda ko'rgan odam uchun farqi yo'q.
    """
    child_a = _child(tenant_a, "Alfa")
    child_b = _child(tenant_b, "Beta")
    with organization_context(tenant_a.organization.id):
        finance.record_payment(child=child_a, amount=Decimal("1000000"), method="cash")
    with organization_context(tenant_b.organization.id):
        finance.record_payment(child=child_b, amount=Decimal("7000000"), method="cash")

    with organization_context(tenant_a.organization.id):
        assert selectors.total_balance(organization_id=tenant_a.organization.id) == Decimal(
            "1000000.00"
        )
    with organization_context(tenant_b.organization.id):
        assert selectors.total_balance(organization_id=tenant_b.organization.id) == Decimal(
            "7000000.00"
        )


# --- Qopda yoʻq pul (ADR-29) ---


def test_spending_more_than_the_pot_holds_is_refused(tenant_a: Any):
    """
    Kassada 6 mln turib 12 mln chiqib ketmaydi.

    Jonli bogʻchada aynan shu boʻldi: oylik "toʻlangan" deb
    belgilandi va qoldiq −6 752 500 ga tushdi. Manfiy qoldiq hech
    qanday haqiqatni anglatmaydi — u "kassaga tushmagan pul bor"
    degani, va buni tizim SOʻRASHI kerak, jimgina yozib qoʻyishi
    emas.
    """
    with organization_context(tenant_a.organization.id):
        account = CashAccount.objects.get(branch=tenant_a.branch, kind="cash")
        cash.post_movement(
            account=account,
            direction=MovementDirection.IN,
            amount=Decimal("6000000"),
            source_type=MovementSource.PAYMENT,
        )
        with pytest.raises(BusinessRuleViolation) as excinfo:
            cash.post_movement(
                account=account,
                direction=MovementDirection.OUT,
                amount=Decimal("12000000"),
                source_type=MovementSource.PAYROLL,
            )
        # Xabar aynan nima yetishmayotganini aytadi.
        assert "6 000 000" in str(excinfo.value).replace(" ", " ")
        assert selectors.total_balance(organization_id=tenant_a.organization.id) == Decimal(
            "6000000"
        )


def test_the_owner_can_still_record_it_knowingly(tenant_a: Any):
    """
    Taqiq emas, savol.

    Kassaga tushmagan pul (egasining oʻz puli, yozilmagan tushum)
    haqiqatan ham boʻlishi mumkin. Shunda yozuv yoziladi — lekin
    foydalanuvchi buni koʻrib turib tasdiqlagan boʻladi.
    """
    with organization_context(tenant_a.organization.id):
        account = CashAccount.objects.get(branch=tenant_a.branch, kind="cash")
        cash.post_movement(
            account=account,
            direction=MovementDirection.OUT,
            amount=Decimal("500000"),
            source_type=MovementSource.EXPENSE,
            allow_negative=True,
        )
        assert selectors.total_balance(organization_id=tenant_a.organization.id) == Decimal(
            "-500000"
        )


def test_a_counter_movement_is_never_blocked(tenant_a: Any):
    """
    Tuzatish — hamisha mumkin.

    Qaytarilgan toʻlovning qarshi yozuvi qopni manfiyga tushirishi
    mumkin (pul allaqachon chiqib ketgan boʻlsa), lekin uni toʻsish
    jurnalni yolgʻon holatda qoldirardi.
    """
    child = _child(tenant_a, "Bekzod")
    with organization_context(tenant_a.organization.id):
        payment = finance.record_payment(child=child, amount=Decimal("1000000"), method="cash")
        account = CashAccount.objects.get(branch=tenant_a.branch, kind="cash")
        cash.post_movement(
            account=account,
            direction=MovementDirection.OUT,
            amount=Decimal("1000000"),
            source_type=MovementSource.EXPENSE,
        )
        # Endi qopda 0; qaytarish qarshi yozuvi uni manfiyga tushiradi.
        finance.reverse_payment(payment=payment, reason="Xato")
        assert selectors.total_balance(organization_id=tenant_a.organization.id) == Decimal(
            "-1000000"
        )


def test_an_opening_balance_makes_the_pot_usable(tenant_a: Any):
    """
    Bogʻcha tizimga yil oʻrtasida keladi — seyfida allaqachon pul bor.

    Busiz qoldiq doim noldan boshlanardi va birinchi chiqimdayoq
    manfiyga tushardi. Boshlangʻich qoldiq — oddiy harakat, sababi
    bilan: jurnal append-only qoladi.
    """
    with organization_context(tenant_a.organization.id):
        account = CashAccount.objects.get(branch=tenant_a.branch, kind="cash")
        cash.adjust_balance(
            account=account,
            amount=Decimal("20000000"),
            reason="Seyfdagi boshlangʻich qoldiq",
            opening=True,
        )
        # Endi oylik toʻlanadi — hech narsa toʻsmaydi.
        cash.post_movement(
            account=account,
            direction=MovementDirection.OUT,
            amount=Decimal("12000000"),
            source_type=MovementSource.PAYROLL,
        )
        assert selectors.account_balance(account_id=account.id) == Decimal("8000000")


def test_an_adjustment_without_a_reason_is_refused(tenant_a: Any):
    """Qoldiq oʻzgarsa-yu, nega oʻzgargani yozilmasa — buni keyin hech kim tushuntira olmaydi."""
    with organization_context(tenant_a.organization.id):
        account = CashAccount.objects.get(branch=tenant_a.branch, kind="cash")
        with pytest.raises(BusinessRuleViolation):
            cash.adjust_balance(account=account, amount=Decimal("100"), reason="   ")
