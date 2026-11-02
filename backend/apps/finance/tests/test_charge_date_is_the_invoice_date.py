"""
Hisob-faktura ledger yozuvi HUJJAT sanasi bilan yoziladi (audit, 2026-10-30).

Auditda 30.09 holatidagi balans blokida imkonsiz raqamlar bor edi:
avans majburiyati 526 785 200 (olti oylik butun tushum 666 mln
boʻlgani holda), ota-ona qarzi esa boʻsh.

Prod maʼlumoti sababni aniq koʻrsatdi: oʻsha sanaga ledger'da 446 ta
KREDIT (toʻlov) bor edi va birorta ham DEBET yoʻq — 600 ta faktura
chiqarilgan boʻlsa ham. Toʻlov oʻz sanasi bilan yoziladi
(`payment.paid_at`), faktura esa `timezone.now()` bilan: orqaga
sanab yozilgan yoki import qilingan hujjat ledger'da BUGUN paydo
boʻladi, va sanaga qarab tuzilgan har qanday hisobot buziladi.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.finance.models import ChildLedgerEntry, TariffPlan

pytestmark = pytest.mark.django_db


@pytest.fixture
def child(tenant_a) -> Child:
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
            enrolled_on=date(2026, 1, 5),
        )


def test_the_charge_carries_the_invoice_date(tenant_a, child):
    """Oʻtgan oyga yozilgan hujjat ledger'da ham oʻsha oyda turadi."""
    issued = (timezone.localdate().replace(day=1) - timedelta(days=1)).replace(day=5)

    with organization_context(tenant_a.organization.id):
        invoice = finance.issue_invoice(
            child=child,
            period_year=issued.year,
            period_month=issued.month,
            issued_date=issued,
        )
        entry = ChildLedgerEntry.objects.get(source_id=invoice.id, direction="debit")
        assert timezone.localtime(entry.occurred_at).date() == issued


def test_the_balance_at_that_date_sees_the_charge(tenant_a, child):
    """
    Sanaga qarab tuzilgan hisobot debetni ham koʻradi — avans boʻlib
    koʻrinmaydi.
    """
    issued = (timezone.localdate().replace(day=1) - timedelta(days=1)).replace(day=5)
    moment = timezone.make_aware(datetime.combine(issued, time.max))

    with organization_context(tenant_a.organization.id):
        finance.issue_invoice(
            child=child,
            period_year=issued.year,
            period_month=issued.month,
            issued_date=issued,
        )
        rows = ChildLedgerEntry.objects.filter(child=child, occurred_at__lte=moment)
        debits = sum((row.amount for row in rows if row.direction == "debit"), Decimal("0"))
    assert debits == Decimal("1500000.00")
