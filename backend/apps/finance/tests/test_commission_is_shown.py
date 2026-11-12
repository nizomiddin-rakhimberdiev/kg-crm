"""
Komissiya to'lov paytida ham, kvitansiyada ham ko'rinadi (audit 2026-11-12, H4).

Terminal 0,2 %, Click va Payme 1 % — bu bog'chaning puli, va kassir uni
to'lov oynasida, ota-ona esa kvitansiyada ko'rmasdi. Usuli tuzatilgan
to'lov esa jurnalda boshqalaridan farq qilmasdi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.finance.models import TariffPlan

pytestmark = pytest.mark.django_db


def _child(tenant_a) -> Child:
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


def test_the_receipt_names_the_commission(tenant_a):
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        payment = finance.record_payment(
            child=child, amount=Decimal("1500000"), method="terminal", received_by=tenant_a.owner
        )
        receipt = finance.receipt_for(payment)
    assert receipt["lines"][0]["commission"] == "3000.00"


def test_the_cashier_can_read_the_rates(tenant_a):
    response = tenant_a.client().get(reverse("v1:payment-commission-rates"))
    assert response.status_code == 200, response.json()
    rates = response.json()["data"]
    assert Decimal(rates["terminal"]) == Decimal("0.2")
    assert Decimal(rates["payme"]) == Decimal("1")
    assert Decimal(rates["cash"]) == Decimal("0")


def test_a_corrected_payment_says_so(tenant_a):
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        payment = finance.record_payment(
            child=child, amount=Decimal("500000"), method="cash", received_by=tenant_a.owner
        )
        finance.correct_payment_method(
            payment=payment,
            method="terminal",
            reason="Kassir xato bosgan",
            created_by=tenant_a.owner,
        )
    row = tenant_a.client().get(reverse("v1:payment-detail", args=[payment.id])).json()["data"]
    assert row["method"] == "terminal"
    assert row["method_corrected_from"] == "cash"
