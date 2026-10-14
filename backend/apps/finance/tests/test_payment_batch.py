"""
Bitta kassir harakati — bir nechta to'lov usuli (docs/03 §13.5a).

Mijozdagi holat: ota-ona 1 400 000 ni naqd, 100 000 ni terminalda
to'ladi. Bu BITTA hodisa va u to'rtta narsani bir vaqtda to'g'ri
qoldirishi kerak: naqd kassa, terminal, hisob-faktura va oilaning
balansi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from apps.cash import selectors as cash_selectors
from apps.children.models import Child
from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context
from apps.finance import services
from apps.finance.models import Invoice, Payment, TariffPlan

pytestmark = pytest.mark.django_db


def _child_with_invoice(tenant: Any, amount: str = "1500000") -> tuple[Child, Invoice]:
    with organization_context(tenant.organization.id):
        tariff = TariffPlan.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            name="Toʻliq kun",
            amount=Decimal(amount),
        )
        child = Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Javohir",
            last_name="Karimov",
            date_of_birth=date(2021, 3, 14),
            gender="male",
            tariff=tariff,
        )
        invoice = services.issue_invoice(child=child, period_year=2026, period_month=9)
        return child, invoice


def _balances(tenant: Any) -> dict[str, Decimal]:
    rows = cash_selectors.account_balances(organization_id=tenant.organization.id)
    return {row["kind"]: Decimal(row["balance"]) for row in rows}


def test_two_methods_settle_one_invoice(tenant_a: Any):
    child, invoice = _child_with_invoice(tenant_a)
    with organization_context(tenant_a.organization.id):
        payments = services.record_payment_batch(
            child=child,
            invoice=invoice,
            lines=[
                {"method": "cash", "amount": Decimal("1400000")},
                {"method": "terminal", "amount": Decimal("100000")},
            ],
        )
        invoice.refresh_from_db()
        child.refresh_from_db()
        balances = _balances(tenant_a)

    assert len(payments) == 2
    # Bitta harakat — bitta to'plam.
    assert len({p.batch_id for p in payments}) == 1
    assert payments[0].batch_id is not None

    assert invoice.amount_paid == Decimal("1500000.00")
    assert invoice.status == "paid"
    assert child.balance == Decimal("0.00")

    # Terminal puli bankka tushadi; usul toʻlovning oʻzida qoladi.
    assert balances["cash"] == Decimal("1400000.00")
    assert balances["bank"] == Decimal("100000.00")
    assert sorted(p.method for p in payments) == ["cash", "terminal"]


def test_overpayment_becomes_an_advance_instead_of_an_error(tenant_a: Any):
    """
    Eski xatti-harakat kassa oldida noto'g'ri edi: pul allaqachon
    kassirning qo'lida, va uni rad etish tizimning ishi emas.
    """
    child, invoice = _child_with_invoice(tenant_a, "1000000")
    with organization_context(tenant_a.organization.id):
        payments = services.record_payment_batch(
            child=child,
            invoice=invoice,
            lines=[
                {"method": "cash", "amount": Decimal("800000")},
                {"method": "terminal", "amount": Decimal("500000")},
            ],
        )
        invoice.refresh_from_db()
        child.refresh_from_db()

    # Terminal qatori ikkiga bo'lindi: 200 000 fakturaga, 300 000 avansga.
    assert [(p.method, str(p.amount), p.invoice_id is not None) for p in payments] == [
        ("cash", "800000.00", True),
        ("terminal", "200000.00", True),
        ("terminal", "300000.00", False),
    ]
    assert invoice.amount_paid == Decimal("1000000.00")
    # Ortiqcha pul balansni MANFIY qiladi — bog'cha oilaga qarzdor.
    assert child.balance == Decimal("-300000.00")


def test_allocation_follows_the_order_of_the_lines(tenant_a: Any):
    """Kassir qaysi usul avansga tushishini oldindan koʻradi."""
    child, invoice = _child_with_invoice(tenant_a, "1000000")
    with organization_context(tenant_a.organization.id):
        payments = services.record_payment_batch(
            child=child,
            invoice=invoice,
            lines=[
                {"method": "terminal", "amount": Decimal("1200000")},
                {"method": "cash", "amount": Decimal("100000")},
            ],
        )

    assert [(p.method, str(p.amount), p.invoice_id is not None) for p in payments] == [
        ("terminal", "1000000.00", True),
        ("terminal", "200000.00", False),
        ("cash", "100000.00", False),
    ]


def test_invoiceless_batch_is_a_pure_advance(tenant_a: Any):
    child, _ = _child_with_invoice(tenant_a)
    with organization_context(tenant_a.organization.id):
        payments = services.record_payment_batch(
            child=child,
            lines=[{"method": "cash", "amount": Decimal("250000")}],
        )

    assert len(payments) == 1
    assert payments[0].invoice_id is None


def test_an_empty_batch_is_refused(tenant_a: Any):
    child, invoice = _child_with_invoice(tenant_a)
    with organization_context(tenant_a.organization.id), pytest.raises(BusinessRuleViolation):
        services.record_payment_batch(child=child, invoice=invoice, lines=[])


def test_a_repeated_submission_writes_the_batch_only_once(tenant_a: Any):
    """
    Kassir tugmani ikki marta bossa, ikkita to'plam yozilmasligi kerak.

    Har bir qator O'Z kalitini oladi (`key:0a`, `key:1a`) — bitta
    kalitni takrorlash ikkinchi qatorni birinchisining nusxasi deb
    qaytarib yuborardi va to'plam yarim bo'lardi.
    """
    child, invoice = _child_with_invoice(tenant_a)
    lines = [
        {"method": "cash", "amount": Decimal("1400000")},
        {"method": "terminal", "amount": Decimal("100000")},
    ]
    with organization_context(tenant_a.organization.id):
        first = services.record_payment_batch(
            child=child, invoice=invoice, lines=lines, idempotency_key="forma-1"
        )
        second = services.record_payment_batch(
            child=child, invoice=invoice, lines=lines, idempotency_key="forma-1"
        )
        total = Payment.objects.filter(child=child).count()

    assert [p.id for p in first] == [p.id for p in second]
    assert total == 2


def test_a_cancelled_invoice_refuses_the_whole_batch(tenant_a: Any):
    child, invoice = _child_with_invoice(tenant_a)
    with organization_context(tenant_a.organization.id):
        services.cancel_invoice(invoice=invoice, reason="Xato chiqarilgan")
        with pytest.raises(BusinessRuleViolation):
            services.record_payment_batch(
                child=child,
                invoice=invoice,
                lines=[{"method": "cash", "amount": Decimal("100000")}],
            )
        assert Payment.objects.filter(child=child).count() == 0
