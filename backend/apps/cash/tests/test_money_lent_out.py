"""
Qarzga berilgan pul (mijoz soʻrovi, 2026-10-28).

Mijoz: "Qoralama pullar kiritish, chiqimlar boʻlimida alohida windowda
boʻlsin. summadan ayrilaversin, lekin xisob kitobga ham tushaversin, u
qarz pullar boʻlishi mumkin, uni qaytarish imkoniyati ham boʻlishi
kerak qaytsa yana umumiy summaga tushib qolaversin."

Ya'ni bu CHIQIM emas: pul ketdi, lekin yoʻqolmadi — u kimdadir turibdi
va qaytishi kutilmoqda. Shuning uchun u foyda-zararga tushmaydi
(bogʻcha bu puldan kambagʻal boʻlib qolmadi), kassadan esa chiqadi
(pul haqiqatan qoʻldan ketdi).

Hujjat allaqachon bor — `MoneyOperation` (13.2b) — unga ikkita tur
qoʻshiladi: berildi va qaytdi. Qaytish ASL hujjatga bogʻlanadi, aks
holda "kimda qancha qoldi?" degan savolga javob yoʻq.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.cash import services as cash
from apps.cash.models import CashAccount, OperationKind
from apps.cash.selectors import account_balances
from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context

pytestmark = pytest.mark.django_db


def _till(tenant_a: Any) -> CashAccount:
    with organization_context(tenant_a.organization.id):
        return cash.account_for_method(branch=tenant_a.branch, method="cash")


def _balance(tenant_a: Any, kind: str = "cash") -> Decimal:
    rows = account_balances(organization_id=tenant_a.organization.id)
    return next(Decimal(row["balance"]) for row in rows if row["kind"] == kind)


@pytest.fixture
def funded(tenant_a) -> Any:
    """Kassada pul boʻlsin — qarz berish uchun avval pul kerak."""
    with organization_context(tenant_a.organization.id):
        cash.record_operation(
            kind=OperationKind.OWNER_CONTRIBUTION,
            account=_till(tenant_a),
            amount=Decimal("3000000"),
            occurred_on=timezone.localdate(),
            reason="Ishga tushirish uchun",
        )
    return tenant_a


def test_lending_money_takes_it_out_of_the_pot(funded, tenant_a):
    with organization_context(tenant_a.organization.id):
        loan = cash.lend_money(
            account=_till(tenant_a),
            amount=Decimal("500000"),
            occurred_on=timezone.localdate(),
            person="Feruza Abdullayeva",
            reason="Uyida tez yordam kerak boʻldi",
        )
        assert loan.kind == OperationKind.LOAN_OUT
        assert loan.outstanding == Decimal("500000.00")
        assert _balance(tenant_a) == Decimal("2500000.00")


def test_a_return_brings_the_money_back(funded, tenant_a):
    with organization_context(tenant_a.organization.id):
        loan = cash.lend_money(
            account=_till(tenant_a),
            amount=Decimal("500000"),
            occurred_on=timezone.localdate(),
            person="Feruza Abdullayeva",
            reason="Uyida tez yordam kerak boʻldi",
        )
        cash.return_loan(
            loan=loan,
            account=_till(tenant_a),
            amount=Decimal("500000"),
            occurred_on=timezone.localdate(),
        )
        loan.refresh_from_db()
        assert loan.outstanding == Decimal("0.00")
        assert _balance(tenant_a) == Decimal("3000000.00")


def test_a_partial_return_leaves_the_rest_outstanding(funded, tenant_a):
    with organization_context(tenant_a.organization.id):
        loan = cash.lend_money(
            account=_till(tenant_a),
            amount=Decimal("500000"),
            occurred_on=timezone.localdate(),
            person="Feruza Abdullayeva",
            reason="Uyida tez yordam kerak boʻldi",
        )
        cash.return_loan(
            loan=loan,
            account=_till(tenant_a),
            amount=Decimal("200000"),
            occurred_on=timezone.localdate(),
        )
        loan.refresh_from_db()
        assert loan.outstanding == Decimal("300000.00")
        assert _balance(tenant_a) == Decimal("2700000.00")


def test_more_than_the_loan_cannot_come_back(funded, tenant_a):
    with organization_context(tenant_a.organization.id):
        loan = cash.lend_money(
            account=_till(tenant_a),
            amount=Decimal("500000"),
            occurred_on=timezone.localdate(),
            person="Feruza Abdullayeva",
            reason="Uyida tez yordam kerak boʻldi",
        )
        with pytest.raises(BusinessRuleViolation):
            cash.return_loan(
                loan=loan,
                account=_till(tenant_a),
                amount=Decimal("600000"),
                occurred_on=timezone.localdate(),
            )


def test_lending_is_not_an_expense(funded, tenant_a):
    """
    Foyda-zararda koʻrinmaydi: bogʻcha bu puldan kambagʻal boʻlgani
    yoʻq — pul kimdadir turibdi.
    """
    from apps.reports.selectors import expense_report

    today = timezone.localdate()
    with organization_context(tenant_a.organization.id):
        cash.lend_money(
            account=_till(tenant_a),
            amount=Decimal("500000"),
            occurred_on=today,
            person="Feruza Abdullayeva",
            reason="Uyida tez yordam kerak boʻldi",
        )
        report = expense_report(
            organization_id=tenant_a.organization.id, date_from=today, date_to=today
        )
    assert Decimal(report["total"]) == Decimal("0")


def test_an_empty_pot_refuses_to_lend(tenant_a):
    with organization_context(tenant_a.organization.id), pytest.raises(BusinessRuleViolation):
        cash.lend_money(
            account=_till(tenant_a),
            amount=Decimal("500000"),
            occurred_on=timezone.localdate(),
            person="Feruza Abdullayeva",
            reason="Uyida tez yordam kerak boʻldi",
        )


def test_the_endpoint_lists_open_loans(funded, tenant_a):
    with organization_context(tenant_a.organization.id):
        cash.lend_money(
            account=_till(tenant_a),
            amount=Decimal("500000"),
            occurred_on=timezone.localdate(),
            person="Feruza Abdullayeva",
            reason="Uyida tez yordam kerak boʻldi",
        )

    response = tenant_a.client().get(reverse("v1:loan-list"))
    assert response.status_code == 200, response.data
    rows = response.json()["data"]
    assert len(rows) == 1
    assert rows[0]["person"] == "Feruza Abdullayeva"
    assert rows[0]["outstanding"] == "500000.00"


def test_another_tenant_cannot_see_the_loan(funded, tenant_a, tenant_b):
    with organization_context(tenant_a.organization.id):
        loan = cash.lend_money(
            account=_till(tenant_a),
            amount=Decimal("500000"),
            occurred_on=timezone.localdate(),
            person="Feruza Abdullayeva",
            reason="Uyida tez yordam kerak boʻldi",
        )

    response = tenant_b.client().post(
        reverse("v1:loan-return", args=[loan.id]),
        {"amount": "100000", "occurred_on": str(timezone.localdate())},
        format="json",
    )
    assert response.status_code == 404
    with organization_context(tenant_a.organization.id):
        # Hech narsa qaytmadi: qarz butun qoldi.
        loan.refresh_from_db()
        assert loan.outstanding == Decimal("500000.00")
