"""
Kvitansiya — PLAN 1.7.

Ota-ona qo'lidagi qog'oz bilan tizimdagi raqam bir xil bo'lishi kerak.
Shuning uchun kvitansiyada faqat summa emas, TAQSIMOT ham bor: qaysi
oy uchun qancha ketgani nizoda eng kerakli qator.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import services
from apps.finance.models import TariffPlan

pytestmark = pytest.mark.django_db

TARIFF = Decimal("1500000.00")


@pytest.fixture
def child(tenant_a) -> Child:
    with organization_context(tenant_a.organization.id):
        tariff = TariffPlan.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            name="To'liq kun",
            amount=TARIFF,
        )
        return Child.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Robiya",
            last_name="Ibragimova",
            date_of_birth=date(2021, 3, 14),
            gender="female",
            tariff=tariff,
        )


class TestReceiptNumber:
    def test_the_number_is_stable_across_reprints(self, tenant_a, child):
        """Qayta chop etish AYNAN o'sha raqamni berishi kerak."""
        with organization_context(tenant_a.organization.id):
            payment = services.record_payment(child=child, amount=TARIFF, method="cash")
            first = services.receipt_number(payment)
            second = services.receipt_number(payment)

        assert first == second
        assert first.startswith("KVT-")

    def test_numbers_are_sequential_within_a_day(self, tenant_a, child):
        with organization_context(tenant_a.organization.id):
            one = services.record_payment(child=child, amount=Decimal("100000"), method="cash")
            two = services.record_payment(child=child, amount=Decimal("100000"), method="cash")
            numbers = [services.receipt_number(one), services.receipt_number(two)]

        assert numbers[0] != numbers[1]
        assert numbers == sorted(numbers)


class TestReceiptContent:
    def test_a_multi_method_payment_is_one_receipt(self, tenant_a, child):
        """
        Ota-ona 1 400 000 ni naqd, 100 000 ni terminalda to'lasa — bu
        BITTA hodisa. Ikkita qog'oz berish "men ikki marta to'ladimmi?"
        degan savolni tug'diradi.
        """
        with organization_context(tenant_a.organization.id):
            services.issue_invoice(child=child, period_year=2026, period_month=9)
            payments = services.record_payment_batch(
                child=child,
                lines=[
                    {"method": "cash", "amount": Decimal("1400000")},
                    {"method": "terminal", "amount": Decimal("100000")},
                ],
            )
            receipt = services.receipt_for(payments[0])

        assert len(receipt["lines"]) == 2
        assert Decimal(receipt["total"]) == TARIFF
        assert {line["method"] for line in receipt["lines"]} == {"Naqd", "Terminal"}

    def test_the_receipt_shows_which_invoices_it_settles(self, tenant_a, child):
        with organization_context(tenant_a.organization.id):
            services.issue_invoice(child=child, period_year=2026, period_month=8)
            services.issue_invoice(child=child, period_year=2026, period_month=9)
            payment = services.record_payment(
                child=child, amount=TARIFF + Decimal("500000"), method="cash"
            )
            receipt = services.receipt_for(payment)

        periods = {row["period"]: Decimal(row["amount"]) for row in receipt["allocations"]}
        assert periods == {"2026-08": TARIFF, "2026-09": Decimal("500000.00")}

    def test_the_receipt_answers_what_is_left(self, tenant_a, child):
        """Ota-onaning keyingi savoli har doim bitta: "yana qancha qoldi?"."""
        with organization_context(tenant_a.organization.id):
            services.issue_invoice(child=child, period_year=2026, period_month=9)
            payment = services.record_payment(child=child, amount=Decimal("500000"), method="cash")
            receipt = services.receipt_for(payment)

        assert Decimal(receipt["balance_after"]) == TARIFF - Decimal("500000")
        assert Decimal(receipt["advance_after"]) == Decimal("0.00")

    def test_an_advance_is_shown_as_an_advance(self, tenant_a, child):
        with organization_context(tenant_a.organization.id):
            payment = services.record_payment(child=child, amount=Decimal("200000"), method="cash")
            receipt = services.receipt_for(payment)

        assert receipt["allocations"] == []
        assert Decimal(receipt["advance_after"]) == Decimal("200000.00")
        assert Decimal(receipt["balance_after"]) == Decimal("0.00")


class TestEndpoint:
    def test_the_endpoint_returns_the_receipt(self, tenant_a, child):
        with organization_context(tenant_a.organization.id):
            payment = services.record_payment(child=child, amount=TARIFF, method="cash")

        response = tenant_a.client().get(reverse("v1:payment-receipt", args=[payment.id]))
        assert response.status_code == 200
        assert response.data["child"] == "Ibragimova Robiya"

    def test_another_tenant_cannot_read_it(self, tenant_a, tenant_b, child):
        with organization_context(tenant_a.organization.id):
            payment = services.record_payment(child=child, amount=TARIFF, method="cash")

        response = tenant_b.client().get(reverse("v1:payment-receipt", args=[payment.id]))
        assert response.status_code == 404
