"""
Storno sababsiz boʻlmaydi va komissiyani ham yopadi (audit, 2026-10-30).

Auditda ikkita kamchilik:

* `POST /payments/{id}/reverse` boʻsh sabab bilan qabul qilinardi —
  keyin jurnalda "qaytarildi" degan qator turardi va nega ekani hech
  qayerda yoʻq edi;
* terminal toʻlovi storno qilinganda bank komissiyasi xarajati egasiz
  qolardi: toʻlov yoʻq, komissiyasi bor.

Ikkinchisi avvalgi qarorni (Bosqich 12.5: "bank komissiyani
qaytarmaydi") almashtiradi — bogʻcha egasining 2026-10-30 dagi
koʻrsatmasi: storno toʻlovning butun izini yopadi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.urls import reverse

from apps.children.models import Child
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


def test_a_reversal_without_a_reason_is_refused(tenant_a):
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        payment = finance.record_payment(
            child=child, amount=Decimal("1500000"), method="cash", received_by=tenant_a.owner
        )

    response = tenant_a.client().post(
        reverse("v1:payment-reverse", args=[payment.id]), {"reason": ""}, format="json"
    )
    assert response.status_code == 400, response.data


def test_a_two_letter_reason_is_refused(tenant_a):
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        payment = finance.record_payment(
            child=child, amount=Decimal("1500000"), method="cash", received_by=tenant_a.owner
        )

    response = tenant_a.client().post(
        reverse("v1:payment-reverse", args=[payment.id]), {"reason": "xa"}, format="json"
    )
    assert response.status_code == 400, response.data


def test_the_reversal_closes_the_bank_commission_too(tenant_a):
    """Terminal 0,2 % — 1 500 000 dan 3 000 soʻm."""
    from apps.cash.selectors import account_balances

    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        payment = finance.record_payment(
            child=child, amount=Decimal("1500000"), method="terminal", received_by=tenant_a.owner
        )
        commission = Expense.objects.get(payment=payment)
        assert commission.amount == Decimal("3000.00")

        finance.reverse_payment(
            payment=payment, reason="Xato summa kiritilgan", created_by=tenant_a.owner
        )

        commission.refresh_from_db()
        # Hujjat QOLADI (D3), lekin u endi "boʻlmagan" deb belgilanadi
        # va qopdagi izi nolga keltiriladi.
        assert commission.status == "rejected"
        rows = account_balances(organization_id=tenant_a.organization.id)
        assert {row["kind"]: Decimal(row["balance"]) for row in rows}["bank"] == Decimal("0.00")


def test_the_child_balance_returns_to_where_it_was(tenant_a):
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        child.refresh_from_db()
        before = child.balance
        payment = finance.record_payment(
            child=child, amount=Decimal("1500000"), method="terminal", received_by=tenant_a.owner
        )
        finance.reverse_payment(
            payment=payment, reason="Xato summa kiritilgan", created_by=tenant_a.owner
        )
        child.refresh_from_db()
    assert child.balance == before
