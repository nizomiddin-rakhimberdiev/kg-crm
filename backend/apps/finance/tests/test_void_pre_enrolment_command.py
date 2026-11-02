"""
Kelmagan oyga yozilgan fakturalarni tozalash buyrugʻi (audit, 2026-10-30).

Sukut — `--dry-run`: mijozning bazasida hech narsa oʻzgarmaydi, faqat
roʻyxat koʻrsatiladi. Oʻchirish yoʻq: faktura BEKOR qilinadi, qarshi
ledger yozuvi bilan (3-invariant).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command

from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance.models import Invoice, InvoiceStatus, TariffPlan

pytestmark = pytest.mark.django_db


@pytest.fixture
def stray(tenant_a) -> Invoice:
    """Qabuldan OLDINGI oyga yozilgan hujjat — audit topgan holat."""
    with organization_context(tenant_a.organization.id):
        tariff = TariffPlan.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            name="Toʻliq kun",
            amount=Decimal("1500000"),
        )
        child = Child.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Madina",
            last_name="Nazarova",
            date_of_birth=date(2021, 5, 4),
            gender="female",
            tariff=tariff,
            enrolled_on=date(2026, 10, 9),
        )
        return Invoice.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            child=child,
            number="INV-2026-05-0001",
            period_year=2026,
            period_month=5,
            issued_date=date(2026, 5, 1),
            due_date=date(2026, 5, 10),
            amount_due=Decimal("0"),
            status=InvoiceStatus.ISSUED,
        )


def test_the_dry_run_changes_nothing(tenant_a, stray):
    out = StringIO()
    call_command("void_pre_enrolment_invoices", "--slug", tenant_a.organization.slug, stdout=out)
    with organization_context(tenant_a.organization.id):
        stray.refresh_from_db()
    assert stray.status == InvoiceStatus.ISSUED
    assert "Bekor qilinadi: 1" in out.getvalue()


def test_apply_cancels_the_invoice(tenant_a, stray):
    call_command(
        "void_pre_enrolment_invoices",
        "--slug",
        tenant_a.organization.slug,
        "--apply",
        stdout=StringIO(),
    )
    with organization_context(tenant_a.organization.id):
        stray.refresh_from_db()
    assert stray.status == InvoiceStatus.CANCELLED
