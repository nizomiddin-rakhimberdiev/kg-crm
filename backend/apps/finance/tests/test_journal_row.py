"""
Toʻlovlar jurnalidagi qator haqiqatni aytishi kerak (audit, 2026-10-21).

Jurnal "Hisob-faktura" ustunini `payment.invoice` dan olardi. Lekin ADR-20
dan keyin pul hujjatga `payment_allocation` orqali tegishli boʻladi: kassir
hisob-fakturani TANLAMASA ham pul FIFO boʻyicha eng eski qarzni yopadi.
Natijada bolaning kartasida "MAIN-202610-0004 toʻlangan" deb yozilgan pul
jurnalda "— avans —" deb koʻrinardi — bitta toʻlov, ikki xil javob.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import services
from apps.finance.models import TariffPlan

pytestmark = pytest.mark.django_db

AMOUNT = Decimal("1500000.00")


@pytest.fixture
def child(tenant_a: Any) -> Child:
    with organization_context(tenant_a.organization.id):
        tariff = TariffPlan.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            name="Toʻliq kun",
            amount=AMOUNT,
        )
        return Child.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Ali",
            last_name="Valiyev",
            date_of_birth=date(2021, 3, 14),
            gender="male",
            tariff=tariff,
        )


def _row(client: Any, payment_id: Any) -> dict[str, Any]:
    response = client.get("/api/v1/payments", {"child": str(payment_id[1])})
    assert response.status_code == 200, response.content
    rows = {row["id"]: row for row in response.json()["data"]}
    return rows[str(payment_id[0])]


def test_a_payment_that_settled_an_invoice_is_never_shown_as_an_advance(
    tenant_a: Any, child: Child
):
    with organization_context(tenant_a.organization.id):
        invoice = services.issue_invoice(child=child, period_year=2026, period_month=7)
        # Kassir hujjatni tanlamadi — pul oʻzi FIFO boʻyicha ketdi.
        payment = services.record_payment(child=child, amount=AMOUNT, method="cash")

    row = _row(tenant_a.client(), (payment.id, child.id))

    assert row["settled_invoices"] == [invoice.number]
    assert Decimal(row["advance_amount"]) == Decimal("0.00")


def test_money_with_no_open_invoice_stays_an_advance(tenant_a: Any, child: Child):
    with organization_context(tenant_a.organization.id):
        payment = services.record_payment(child=child, amount=AMOUNT, method="cash")

    row = _row(tenant_a.client(), (payment.id, child.id))

    assert row["settled_invoices"] == []
    assert Decimal(row["advance_amount"]) == AMOUNT


def test_an_overpayment_names_the_invoice_and_the_remainder(tenant_a: Any, child: Child):
    with organization_context(tenant_a.organization.id):
        invoice = services.issue_invoice(child=child, period_year=2026, period_month=7)
        payment = services.record_payment(
            child=child, amount=AMOUNT + Decimal("200000.00"), method="cash"
        )

    row = _row(tenant_a.client(), (payment.id, child.id))

    assert row["settled_invoices"] == [invoice.number]
    assert Decimal(row["advance_amount"]) == Decimal("200000.00")


def test_a_reversed_payment_releases_its_invoice(tenant_a: Any, child: Child):
    with organization_context(tenant_a.organization.id):
        services.issue_invoice(child=child, period_year=2026, period_month=7)
        payment = services.record_payment(child=child, amount=AMOUNT, method="cash")
        services.reverse_payment(payment=payment, reason="Kassir xato kiritdi")

    row = _row(tenant_a.client(), (payment.id, child.id))

    assert row["settled_invoices"] == []
