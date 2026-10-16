"""
Xarajat bo'lmagan pul harakatlari (Bosqich 13.2b, brif §3.2, test 6).

Excel'da dividend xarajat bilan aralashardi yoki umuman ko'rinmasdi;
egadan kiritilgan pul tushum bo'lib sanalardi. Endi har biri o'z turi
bilan: boshqa daromad (subsidiya, to'garak, ijara), egaga to'lov
(dividend — soliq majburiyati bilan), egadan kiritma, kredit olish va
qaytarish, soliq to'lovi, ota-onaga pul qaytarish.
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
from apps.cash.models import CashAccount, MoneyOperation
from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.expenses.models import Expense
from apps.finance import services as finance

pytestmark = pytest.mark.django_db

URL = "/api/v1/money-operations"


@pytest.fixture(autouse=True)
def _funded(tenant_a: Any) -> None:
    tenant_a.fund("100000000", kind="all")


def _pot(tenant: Any, kind: str = "bank") -> CashAccount:
    with organization_context(tenant.organization.id):
        return CashAccount.objects.get(branch=tenant.branch, kind=kind, is_active=True)


def _balance(tenant: Any, kind: str = "bank") -> Decimal:
    with organization_context(tenant.organization.id):
        return selectors.account_balance(account_id=_pot(tenant, kind).id)


def _post(tenant: Any, client: Any = None, **payload: Any) -> Any:
    body = {
        "cash_account_id": str(_pot(tenant).id),
        "occurred_on": "2026-10-10",
        "reason": "Taʼsischilar qarori №3",
        **payload,
    }
    return (client or tenant.client()).post(URL, body, format="json")


# --- 6: dividend ---


def test_6_a_dividend_is_not_an_expense_and_accrues_its_tax(tenant_a: Any):
    before = _balance(tenant_a)

    response = _post(tenant_a, kind="owner_draw", subtype="dividend", amount="60000000")

    assert response.status_code == 201, response.json()
    data = response.json()["data"]
    assert Decimal(data["tax_amount"]) == Decimal("3000000")
    assert _balance(tenant_a) == before - Decimal("60000000")
    with organization_context(tenant_a.organization.id):
        assert not Expense.objects.exists()


def test_the_dividend_tax_rate_is_a_setting(tenant_a: Any):
    from apps.settings_app.services import set_setting

    with organization_context(tenant_a.organization.id):
        set_setting(organization=tenant_a.organization, key="tax.dividend_percent", value=10)
    data = _post(tenant_a, kind="owner_draw", subtype="dividend", amount="1000000").json()["data"]
    assert Decimal(data["tax_amount"]) == Decimal("100000")


def test_an_individual_entrepreneurs_draw_carries_no_dividend_tax(tenant_a: Any):
    data = _post(tenant_a, kind="owner_draw", subtype="draw", amount="5000000").json()["data"]
    assert Decimal(data["tax_amount"]) == 0


def test_a_draw_cannot_take_more_than_the_pot_holds(tenant_a: Any):
    assert _post(tenant_a, kind="owner_draw", subtype="draw", amount="500000000").status_code == 422


# --- Kiritma, kredit, boshqa daromad, soliq ---


@pytest.mark.parametrize(
    ("kind", "subtype", "sign"),
    [
        ("owner_contribution", "", 1),
        ("loan_in", "", 1),
        ("loan_repay", "", -1),
        ("other_income", "subsidy", 1),
        ("tax_payment", "dividend_tax", -1),
    ],
)
def test_each_kind_moves_money_its_own_way(tenant_a: Any, kind: str, subtype: str, sign: int):
    before = _balance(tenant_a)
    response = _post(tenant_a, kind=kind, subtype=subtype, amount="2000000")
    assert response.status_code == 201, response.json()
    assert _balance(tenant_a) == before + sign * Decimal("2000000")


def test_other_income_has_a_month(tenant_a: Any):
    response = _post(
        tenant_a, kind="other_income", subtype="subsidy", amount="7000000", period="2026-09"
    )
    with organization_context(tenant_a.organization.id):
        operation = MoneyOperation.objects.get(pk=response.json()["data"]["id"])
    assert (operation.period_year, operation.period_month) == (2026, 9)


def test_a_reason_is_required(tenant_a: Any):
    assert _post(tenant_a, kind="loan_in", amount="1000", reason="  ").status_code == 400


def test_an_unknown_subtype_is_refused(tenant_a: Any):
    assert _post(tenant_a, kind="owner_draw", subtype="bonus", amount="1000").status_code == 400


def test_a_cashier_does_not_pay_the_owner(tenant_a: Any):
    with organization_context(tenant_a.organization.id):
        user = User.objects.create_user(
            email="kassir@alfa.uz",
            password="Juda-Kuchli-Parol-2026",  # noqa: S106
            full_name="Kassir",
            organization=tenant_a.organization,
            role=tenant_a.role("cashier"),
            branch=tenant_a.branch,
        )
        tokens = issue_token_pair(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    response = _post(tenant_a, client=client, kind="owner_draw", subtype="draw", amount="1000")
    assert response.status_code == 403


@pytest.mark.tenancy
def test_another_tenants_operation_is_404(tenant_a: Any, tenant_b: Any):
    operation_id = _post(tenant_a, kind="loan_in", amount="1000").json()["data"]["id"]
    assert tenant_b.client().get(f"{URL}/{operation_id}").status_code == 404


# --- Ota-onaga pul qaytarish ---


def _advance(tenant: Any, amount: str = "3050000") -> Any:
    with organization_context(tenant.organization.id):
        child = Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Ali",
            last_name="Valiyev",
            date_of_birth=date(2021, 3, 14),
            gender="male",
        )
        return finance.record_payment(child=child, amount=Decimal(amount), method="cash")


def test_an_advance_is_returned_with_its_own_document(tenant_a: Any):
    payment = _advance(tenant_a)
    till = _balance(tenant_a, "cash")

    response = tenant_a.client().post(
        f"/api/v1/payments/{payment.id}/refund",
        {
            "amount": "1000000",
            "cash_account_id": str(_pot(tenant_a, "cash").id),
            "reason": "Oila koʻchib ketdi",
        },
        format="json",
    )

    assert response.status_code == 201, response.json()
    assert _balance(tenant_a, "cash") == till - Decimal("1000000")
    with organization_context(tenant_a.organization.id):
        assert finance.child_advance(payment.child) == Decimal("2050000")
        assert finance.payment_unallocated(payment) == Decimal("2050000")
        assert finance.child_balance(payment.child_id) == Decimal("-2050000")


def test_more_than_the_unused_advance_cannot_be_returned(tenant_a: Any):
    payment = _advance(tenant_a, "500000")
    response = tenant_a.client().post(
        f"/api/v1/payments/{payment.id}/refund",
        {
            "amount": "600000",
            "cash_account_id": str(_pot(tenant_a, "cash").id),
            "reason": "x",
        },
        format="json",
    )
    assert response.status_code == 422
