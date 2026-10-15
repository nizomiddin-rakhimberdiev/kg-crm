"""
Kassa va bank: komissiya, o'tkazma, topshirish, kun yopilishi
(Bosqich 12.5, brif §5, testlar 13–14).

Excel'dagi muammolar: bank↔kassa o'tkazmalari kirim/chiqim bo'lib
yozilardi; kassa qoldig'i "tenglashtiruvchi qator" bilan nolga
keltirilardi; bank qoldig'i manfiy bo'lib qolgan. Endi:

* usul komissiyasi (terminal 0,2 %, Click/Payme 1 % — sozlama) bank
  xarajati bo'lib O'ZI yoziladi;
* inkassa va bankdan naqd yechish — o'tkazma: tushum ham, xarajat ham
  o'zgarmaydi;
* naqd pul kassirdan mas'ul shaxsga — qabul qiluvchi tasdiqlaydi, kimning
  qo'lida qancha turgani ko'rinadi;
* kun yopilishi — sanoq tizim bilan solishtiriladi, farq SABABI bilan
  "kamomad/ortiqcha" bo'lib yoziladi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.accounts.authentication import issue_token_pair
from apps.accounts.models import User
from apps.cash import selectors
from apps.cash.models import CashAccount, CashMovement
from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.expenses.models import Expense
from apps.finance import services as finance
from apps.finance.models import Payment
from apps.settings_app.services import set_setting

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


def _pot(tenant: Any, kind: str) -> CashAccount:
    with organization_context(tenant.organization.id):
        from apps.cash import services as cash

        cash.ensure_branch_accounts(branch=tenant.branch)
        return CashAccount.objects.filter(branch=tenant.branch, kind=kind, is_active=True).first()


def _balance(tenant: Any, kind: str) -> Decimal:
    with organization_context(tenant.organization.id):
        return selectors.account_balance(account_id=_pot(tenant, kind).id)


def _user(tenant: Any, role: str, email: str) -> tuple[User, APIClient]:
    with organization_context(tenant.organization.id):
        user = User.objects.create_user(
            email=email,
            password="Juda-Kuchli-Parol-2026",  # noqa: S106
            full_name=email.split("@")[0].title(),
            organization=tenant.organization,
            role=tenant.role(role),
            branch=tenant.branch,
        )
        tokens = issue_token_pair(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return user, client


def _pay(tenant: Any, method: str, amount: str, received_by: Any = None) -> Payment:
    with organization_context(tenant.organization.id):
        return finance.record_payment(
            child=_child(tenant),
            amount=Decimal(amount),
            method=method,
            received_by=received_by or tenant.owner,
        )


# --- 13: komissiya ---


def test_13_a_terminal_payment_books_its_commission_as_a_bank_expense(tenant_a: Any):
    payment = _pay(tenant_a, "terminal", "10000000")

    with organization_context(tenant_a.organization.id):
        expense = Expense.objects.select_related("category", "cash_account").get(payment=payment)
    assert expense.amount == Decimal("20000")
    assert expense.category.name == "Bank komissiyasi"
    assert expense.status == "paid"
    assert expense.cash_account.kind == "bank"
    assert _balance(tenant_a, "bank") == Decimal("9980000")


@pytest.mark.parametrize("method", ["click", "payme"])
def test_click_and_payme_cost_one_percent(tenant_a: Any, method: str):
    payment = _pay(tenant_a, method, "1525000")
    with organization_context(tenant_a.organization.id):
        assert Expense.objects.get(payment=payment).amount == Decimal("15250")


def test_cash_carries_no_commission(tenant_a: Any):
    _pay(tenant_a, "cash", "3050000")
    with organization_context(tenant_a.organization.id):
        assert not Expense.objects.exists()


def test_the_commission_rate_is_a_setting(tenant_a: Any):
    with organization_context(tenant_a.organization.id):
        set_setting(
            organization=tenant_a.organization,
            key="commission.terminal_percent",
            value="0",
            branch=tenant_a.branch,
        )
    _pay(tenant_a, "terminal", "10000000")
    with organization_context(tenant_a.organization.id):
        assert not Expense.objects.exists()


# --- 14: o'tkazma ---


def test_14_cash_collection_moves_money_and_changes_neither_income_nor_expense(tenant_a: Any):
    _pay(tenant_a, "cash", "45000000")
    cash_before, bank_before = _balance(tenant_a, "cash"), _balance(tenant_a, "bank")
    with organization_context(tenant_a.organization.id):
        payments_before = Payment.objects.count()

    response = tenant_a.client().post(
        "/api/v1/cash-accounts/transfer",
        {
            "from_account_id": str(_pot(tenant_a, "cash").id),
            "to_account_id": str(_pot(tenant_a, "bank").id),
            "amount": "40000000",
            "reason": "Inkassa",
        },
        format="json",
    )

    assert response.status_code == 201, response.json()
    assert _balance(tenant_a, "cash") == cash_before - Decimal("40000000")
    assert _balance(tenant_a, "bank") == bank_before + Decimal("40000000")
    with organization_context(tenant_a.organization.id):
        assert Payment.objects.count() == payments_before
        assert not Expense.objects.exists()
        legs = CashMovement.objects.filter(source_type="transfer")
        assert sorted(legs.values_list("direction", flat=True)) == ["in", "out"]
        assert len({leg.transfer_group for leg in legs}) == 1


def test_a_transfer_cannot_take_more_than_the_pot_holds(tenant_a: Any):
    response = tenant_a.client().post(
        "/api/v1/cash-accounts/transfer",
        {
            "from_account_id": str(_pot(tenant_a, "cash").id),
            "to_account_id": str(_pot(tenant_a, "bank").id),
            "amount": "1000",
            "reason": "Inkassa",
        },
        format="json",
    )
    assert response.status_code == 422


def test_a_cashier_does_not_move_money_between_pots(tenant_a: Any):
    _pay(tenant_a, "cash", "1000000")
    _cashier, client = _user(tenant_a, "cashier", "kassir@alfa.uz")
    response = client.post(
        "/api/v1/cash-accounts/transfer",
        {
            "from_account_id": str(_pot(tenant_a, "cash").id),
            "to_account_id": str(_pot(tenant_a, "bank").id),
            "amount": "1000",
            "reason": "x",
        },
        format="json",
    )
    assert response.status_code == 403


@pytest.mark.tenancy
def test_another_tenants_pot_is_not_a_transfer_target(tenant_a: Any, tenant_b: Any):
    _pay(tenant_a, "cash", "1000000")
    response = tenant_a.client().post(
        "/api/v1/cash-accounts/transfer",
        {
            "from_account_id": str(_pot(tenant_a, "cash").id),
            "to_account_id": str(_pot(tenant_b, "bank").id),
            "amount": "1000",
            "reason": "x",
        },
        format="json",
    )
    assert response.status_code in (400, 404)
    assert _balance(tenant_a, "cash") == Decimal("1000000")


# --- Naqd pulni topshirish ---


def test_cash_handed_over_moves_to_the_receiver_only_when_confirmed(tenant_a: Any):
    cashier, cashier_client = _user(tenant_a, "cashier", "kassir@alfa.uz")
    director, director_client = _user(tenant_a, "director", "direktor@alfa.uz")
    _pay(tenant_a, "cash", "500000", received_by=cashier)

    def held() -> dict[str, Decimal]:
        rows = director_client.get("/api/v1/cash-accounts/custody").json()["data"]
        return {row["user_id"]: Decimal(row["amount"]) for row in rows}

    assert held()[str(cashier.id)] == Decimal("500000")

    created = cashier_client.post(
        "/api/v1/cash-handovers",
        {"to_user_id": str(director.id), "amount": "500000", "note": "Kun oxiri"},
        format="json",
    )
    assert created.status_code == 201, created.json()
    assert created.json()["data"]["status"] == "pending"
    assert held()[str(cashier.id)] == Decimal("500000")  # hali tasdiqlanmagan

    handover_id = created.json()["data"]["id"]
    confirmed = director_client.post(f"/api/v1/cash-handovers/{handover_id}/confirm")

    assert confirmed.status_code == 200, confirmed.json()
    assert held().get(str(cashier.id), Decimal("0")) == 0
    assert held()[str(director.id)] == Decimal("500000")
    # Qopdagi pul o'zgarmaydi — u bitta kassada, faqat qo'l almashdi.
    assert _balance(tenant_a, "cash") == Decimal("500000")


def test_only_the_receiver_confirms(tenant_a: Any):
    cashier, cashier_client = _user(tenant_a, "cashier", "kassir@alfa.uz")
    director, _ = _user(tenant_a, "director", "direktor@alfa.uz")
    _pay(tenant_a, "cash", "500000", received_by=cashier)
    handover_id = cashier_client.post(
        "/api/v1/cash-handovers",
        {"to_user_id": str(director.id), "amount": "500000"},
        format="json",
    ).json()["data"]["id"]

    url = f"/api/v1/cash-handovers/{handover_id}/confirm"
    assert cashier_client.post(url).status_code == 403
    assert tenant_a.client().post(url).status_code == 403


def test_the_receiver_can_refuse_with_a_reason(tenant_a: Any):
    cashier, cashier_client = _user(tenant_a, "cashier", "kassir@alfa.uz")
    director, director_client = _user(tenant_a, "director", "direktor@alfa.uz")
    _pay(tenant_a, "cash", "500000", received_by=cashier)
    handover_id = cashier_client.post(
        "/api/v1/cash-handovers",
        {"to_user_id": str(director.id), "amount": "500000"},
        format="json",
    ).json()["data"]["id"]

    assert (
        director_client.post(f"/api/v1/cash-handovers/{handover_id}/reject", {"reason": ""})
    ).status_code == 422
    refused = director_client.post(
        f"/api/v1/cash-handovers/{handover_id}/reject", {"reason": "Sanoqda 450 000 chiqdi"}
    )
    assert refused.status_code == 200
    assert refused.json()["data"]["status"] == "rejected"


def test_nobody_hands_over_more_than_they_hold(tenant_a: Any):
    cashier, cashier_client = _user(tenant_a, "cashier", "kassir@alfa.uz")
    director, _ = _user(tenant_a, "director", "direktor@alfa.uz")
    _pay(tenant_a, "cash", "500000", received_by=cashier)
    response = cashier_client.post(
        "/api/v1/cash-handovers",
        {"to_user_id": str(director.id), "amount": "600000"},
        format="json",
    )
    assert response.status_code == 422


def test_a_cashier_sees_only_what_they_hold(tenant_a: Any):
    cashier, cashier_client = _user(tenant_a, "cashier", "kassir@alfa.uz")
    _pay(tenant_a, "cash", "500000", received_by=cashier)
    _pay(tenant_a, "cash", "700000")  # egasi qabul qildi
    rows = cashier_client.get("/api/v1/cash-accounts/custody").json()["data"]
    assert [(row["user_id"], Decimal(row["amount"])) for row in rows] == [
        (str(cashier.id), Decimal("500000"))
    ]


@pytest.mark.tenancy
def test_another_tenants_handover_is_404(tenant_a: Any, tenant_b: Any):
    cashier, cashier_client = _user(tenant_a, "cashier", "kassir@alfa.uz")
    director, _ = _user(tenant_a, "director", "direktor@alfa.uz")
    _pay(tenant_a, "cash", "500000", received_by=cashier)
    handover_id = cashier_client.post(
        "/api/v1/cash-handovers",
        {"to_user_id": str(director.id), "amount": "500000"},
        format="json",
    ).json()["data"]["id"]
    stranger = tenant_b.client()
    assert stranger.get(f"/api/v1/cash-handovers/{handover_id}").status_code == 404
    assert stranger.post(f"/api/v1/cash-handovers/{handover_id}/confirm").status_code == 404


# --- Kun yopilishi ---


def _count(tenant: Any, counted: str, reason: str = "") -> Any:
    return tenant.client().post(
        "/api/v1/cash-counts",
        {"cash_account_id": str(_pot(tenant, "cash").id), "counted": counted, "reason": reason},
        format="json",
    )


def test_a_matching_count_closes_the_day_without_a_movement(tenant_a: Any):
    _pay(tenant_a, "cash", "1200000")
    response = _count(tenant_a, "1200000")
    assert response.status_code == 201, response.json()
    assert Decimal(response.json()["data"]["difference"]) == 0
    with organization_context(tenant_a.organization.id):
        assert not CashMovement.objects.filter(source_type="count").exists()


def test_a_shortage_needs_a_reason(tenant_a: Any):
    _pay(tenant_a, "cash", "1200000")
    assert _count(tenant_a, "1150000").status_code == 422


def test_a_shortage_is_recorded_with_its_reason_not_as_a_balancing_line(tenant_a: Any):
    _pay(tenant_a, "cash", "1200000")

    response = _count(tenant_a, "1150000", reason="Qaytim xato berilgan")

    assert response.status_code == 201, response.json()
    data = response.json()["data"]
    assert Decimal(data["system_balance"]) == Decimal("1200000")
    assert Decimal(data["difference"]) == Decimal("-50000")
    assert _balance(tenant_a, "cash") == Decimal("1150000")
    with organization_context(tenant_a.organization.id):
        movement = CashMovement.objects.get(source_type="count")
    assert movement.direction == "out"
    assert "Qaytim xato berilgan" in movement.description


def test_a_surplus_comes_in_the_same_way(tenant_a: Any):
    _pay(tenant_a, "cash", "1200000")
    response = _count(tenant_a, "1210000", reason="Qaytim olinmagan")
    assert Decimal(response.json()["data"]["difference"]) == Decimal("10000")
    assert _balance(tenant_a, "cash") == Decimal("1210000")


def test_one_close_per_pot_per_day(tenant_a: Any):
    _pay(tenant_a, "cash", "1200000")
    _count(tenant_a, "1200000")
    assert _count(tenant_a, "1200000").status_code == 422


def test_a_cashier_does_not_close_the_day(tenant_a: Any):
    _cashier, client = _user(tenant_a, "cashier", "kassir@alfa.uz")
    response = client.post(
        "/api/v1/cash-counts",
        {"cash_account_id": str(_pot(tenant_a, "cash").id), "counted": "0"},
        format="json",
    )
    assert response.status_code == 403


@pytest.mark.tenancy
def test_another_tenants_count_is_404(tenant_a: Any, tenant_b: Any):
    _pay(tenant_a, "cash", "1200000")
    count_id = _count(tenant_a, "1200000").json()["data"]["id"]
    assert tenant_b.client().get(f"/api/v1/cash-counts/{count_id}").status_code == 404


def test_a_cashier_hands_over_only_to_someone_responsible_for_the_whole_till(tenant_a: Any):
    cashier, cashier_client = _user(tenant_a, "cashier", "kassir@alfa.uz")
    director, _ = _user(tenant_a, "director", "direktor@alfa.uz")
    other_cashier, _ = _user(tenant_a, "cashier", "kassir2@alfa.uz")

    response = cashier_client.get("/api/v1/cash-handovers/receivers")

    assert response.status_code == 200
    ids = {row["id"] for row in response.json()["data"]}
    assert str(director.id) in ids
    assert str(tenant_a.owner.id) in ids
    assert str(other_cashier.id) not in ids
    assert str(cashier.id) not in ids


def test_a_broken_commission_setting_never_blocks_a_payment(tenant_a: Any):
    with organization_context(tenant_a.organization.id):
        set_setting(
            organization=tenant_a.organization,
            key="commission.terminal_percent",
            value="0,2",
            branch=tenant_a.branch,
        )
        set_setting(
            organization=tenant_a.organization,
            key="commission.click_percent",
            value="abc",
            branch=tenant_a.branch,
        )
    terminal = _pay(tenant_a, "terminal", "10000000")
    click = _pay(tenant_a, "click", "1000000")
    with organization_context(tenant_a.organization.id):
        assert Expense.objects.get(payment=terminal).amount == Decimal("20000")
        assert not Expense.objects.filter(payment=click).exists()


# --- Ikki qop: naqd va bank (egasining qoidasi, 2026-10-15) ---


def test_a_new_pot_is_either_cash_or_bank(tenant_a: Any):
    """Terminal, Click/Payme, oʻtkazma — usul, qop emas: pul bankka tushadi."""
    client = tenant_a.client()
    refused = client.post(
        "/api/v1/cash-accounts",
        {"name": "Terminal", "kind": "terminal", "handles_method": "terminal"},
        format="json",
    )
    assert refused.status_code == 400
    assert (
        client.post(
            "/api/v1/cash-accounts",
            {"name": "Payme", "kind": "bank", "handles_method": "payme"},
            format="json",
        ).status_code
        == 400
    )
    allowed = client.post(
        "/api/v1/cash-accounts", {"name": "Direktor seyfi", "kind": "cash"}, format="json"
    )
    assert allowed.status_code == 201, allowed.json()


def test_custody_shows_cash_and_bank_apart(tenant_a: Any):
    cashier, _ = _user(tenant_a, "cashier", "kassir@alfa.uz")
    _pay(tenant_a, "cash", "500000", received_by=cashier)
    _pay(tenant_a, "terminal", "1000000", received_by=cashier)
    rows = tenant_a.client().get("/api/v1/cash-accounts/custody").json()["data"]
    row = next(row for row in rows if row["user_id"] == str(cashier.id))
    assert Decimal(row["cash"]) == Decimal("500000")
    # Terminal 1 000 000 tushdi; komissiya chiqimini kassir emas, tizim yozdi.
    assert Decimal(row["bank"]) == Decimal("1000000")
    assert Decimal(row["amount"]) == Decimal("1500000")


def test_the_day_is_handed_over_by_bank_too(tenant_a: Any):
    cashier, cashier_client = _user(tenant_a, "cashier", "kassir@alfa.uz")
    director, director_client = _user(tenant_a, "director", "direktor@alfa.uz")
    _pay(tenant_a, "click", "800000", received_by=cashier)

    created = cashier_client.post(
        "/api/v1/cash-handovers",
        {
            "to_user_id": str(director.id),
            "cash_account_id": str(_pot(tenant_a, "bank").id),
            "amount": "800000",
        },
        format="json",
    )
    assert created.status_code == 201, created.json()
    director_client.post(f"/api/v1/cash-handovers/{created.json()['data']['id']}/confirm")

    rows = director_client.get("/api/v1/cash-accounts/custody").json()["data"]
    held = {row["user_id"]: Decimal(row["bank"]) for row in rows}
    assert held[str(director.id)] == Decimal("800000")
    assert held.get(str(cashier.id), Decimal("0")) == 0


def test_the_bank_balance_is_closed_against_the_statement(tenant_a: Any):
    _pay(tenant_a, "bank_transfer", "2000000")
    response = tenant_a.client().post(
        "/api/v1/cash-counts",
        {"cash_account_id": str(_pot(tenant_a, "bank").id), "counted": "2000000"},
        format="json",
    )
    assert response.status_code == 201, response.json()
    assert Decimal(response.json()["data"]["difference"]) == 0
