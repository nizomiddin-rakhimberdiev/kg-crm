"""
Usulni oʻsha kuni tuzatish (mijoz soʻrovi, 2026-10-28).

Mijoz: "toʻlov qabul qilgan odam, toʻlov maʼlumotlari oʻsha kuni
oʻzgartira olishi kerak, misol uchun terminalni paymega yoki naqdni
terminalga, va barcha hisoblangan summalar ham oʻzgarishi kerak".

Bu amalda eng koʻp uchraydigan xato: kassir shoshib "naqd" ni bosadi,
pul esa terminaldan tushadi. Ilgari yagona yoʻl butun toʻlovni bekor
qilib, qaytadan yozish edi — ya'ni ota-onadagi kvitansiya raqami
oʻzgarardi va jurnalda bitta pul ikki marta koʻrinardi.

SUMMA bu yerda oʻzgarmaydi: notoʻgʻri summa — bu boshqa hodisa, uni
qaytarish bilan tuzatiladi. Oʻzgaradigan narsa — pul QAYSI qopda
yotgani, va u bilan birga bankning komissiyasi.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.cash.selectors import account_balances
from apps.children.models import Child
from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context
from apps.expenses.models import Expense
from apps.finance import services as finance
from apps.finance.models import TariffPlan

pytestmark = pytest.mark.django_db


def _child(tenant_a: Any) -> Child:
    with organization_context(tenant_a.organization.id):
        tariff = TariffPlan.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            name="Toʻliq kun",
            amount=Decimal("1500000"),
        )
        return Child.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Aziza",
            last_name="Safarova",
            date_of_birth=date(2021, 5, 4),
            gender="female",
            tariff=tariff,
        )


def _balances(tenant_a: Any) -> dict[str, Decimal]:
    rows = account_balances(organization_id=tenant_a.organization.id)
    return {row["kind"]: Decimal(row["balance"]) for row in rows}


def test_cash_becomes_terminal_and_the_money_moves_pots(tenant_a):
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        payment = finance.record_payment(
            child=child, amount=Decimal("500000"), method="cash", received_by=tenant_a.owner
        )
        finance.correct_payment_method(
            payment=payment, method="terminal", created_by=tenant_a.owner
        )
        balances = _balances(tenant_a)
        payment.refresh_from_db()

    assert payment.method == "terminal"
    # Naqd kassa boʻshadi, bank esa toʻlovni oldi — komissiyasi ayrilgan
    # holda (terminal 0,2 % = 1 000).
    assert balances["cash"] == Decimal("0.00")
    assert balances["bank"] == Decimal("499000.00")


def test_terminal_becomes_cash_and_the_commission_goes_away(tenant_a):
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        payment = finance.record_payment(
            child=child, amount=Decimal("500000"), method="terminal", received_by=tenant_a.owner
        )
        assert Expense.objects.filter(payment=payment, status="paid").exists()

        finance.correct_payment_method(payment=payment, method="cash", created_by=tenant_a.owner)
        balances = _balances(tenant_a)
        # Komissiya hujjati QOLADI, lekin u endi "boʻlmagan" deb
        # belgilanadi — oʻchirish tarixdan yozuv yoʻqotardi (D3).
        assert not Expense.objects.filter(payment=payment, status="paid").exists()

    assert balances["cash"] == Decimal("500000.00")
    assert balances["bank"] == Decimal("0.00")


def test_the_child_balance_does_not_move(tenant_a):
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        payment = finance.record_payment(
            child=child, amount=Decimal("500000"), method="cash", received_by=tenant_a.owner
        )
        child.refresh_from_db()
        before = child.balance
        finance.correct_payment_method(
            payment=payment, method="terminal", created_by=tenant_a.owner
        )
        child.refresh_from_db()

    assert child.balance == before


def test_yesterdays_payment_cannot_be_corrected(tenant_a):
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        payment = finance.record_payment(
            child=child, amount=Decimal("500000"), method="cash", received_by=tenant_a.owner
        )
        payment.paid_at = timezone.now() - timedelta(days=1)
        payment.save(update_fields=["paid_at"])

        with pytest.raises(BusinessRuleViolation):
            finance.correct_payment_method(
                payment=payment, method="terminal", created_by=tenant_a.owner
            )


def test_a_reversed_payment_cannot_be_corrected(tenant_a):
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        payment = finance.record_payment(
            child=child, amount=Decimal("500000"), method="cash", received_by=tenant_a.owner
        )
        finance.reverse_payment(
            payment=payment, reason="Kassir xato kiritdi", created_by=tenant_a.owner
        )
        with pytest.raises(BusinessRuleViolation):
            finance.correct_payment_method(
                payment=payment, method="terminal", created_by=tenant_a.owner
            )


def test_the_endpoint_corrects_the_method(tenant_a):
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        payment = finance.record_payment(
            child=child, amount=Decimal("500000"), method="cash", received_by=tenant_a.owner
        )

    response = tenant_a.client().post(
        reverse("v1:payment-correct-method", args=[payment.id]),
        {"method": "payme", "reason": "Kassir xato bosgan"},
        format="json",
    )
    assert response.status_code == 200, response.data
    assert response.json()["data"]["method"] == "payme"


def test_another_tenant_cannot_correct_it(tenant_a, tenant_b):
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        payment = finance.record_payment(
            child=child, amount=Decimal("500000"), method="cash", received_by=tenant_a.owner
        )

    response = tenant_b.client().post(
        reverse("v1:payment-correct-method", args=[payment.id]),
        {"method": "payme", "reason": "Oʻzgartiraman"},
        format="json",
    )
    assert response.status_code == 404
