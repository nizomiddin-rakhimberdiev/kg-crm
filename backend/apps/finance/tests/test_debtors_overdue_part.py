"""
Brifingdan ochilgan ro'yxat — faqat muddati o'tgan qism (audit 2026-11-12, F5).

Radix AI "15 kundan ortiq kechikkan: 1 500 000" deydi, "Ro'yxatni
ochish" esa bolaning BUTUN qarzini (3 000 000) ko'rsatardi — muddati
hali kelmagan oyni ham. Egasi ikki raqamni ko'rib qaysi biri to'g'ri
ekanini bilmasdi.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.finance.models import Invoice, TariffPlan

pytestmark = pytest.mark.django_db


def test_the_threshold_list_shows_only_the_overdue_part(tenant_a):
    today = timezone.localdate()
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
            first_name="Ali",
            last_name="Valiyev",
            date_of_birth=date(2021, 3, 14),
            gender="male",
            tariff=tariff,
            enrolled_on=date(2026, 1, 5),
            is_existing_client=True,
        )
        old = finance.issue_invoice(child=child, period_year=2026, period_month=9)
        new = finance.issue_invoice(child=child, period_year=2026, period_month=10)
        Invoice.objects.filter(pk=old.pk).update(due_date=today - timedelta(days=40))
        Invoice.objects.filter(pk=new.pk).update(due_date=today - timedelta(days=5))

    body = tenant_a.client().get("/api/v1/debtors", {"min_days": 15}).json()["data"]
    row = body["results"][0]
    assert Decimal(row["balance"]) == Decimal("3000000")
    assert Decimal(row["overdue_amount"]) == Decimal("1500000")
    assert Decimal(body["total_overdue"]) == Decimal("1500000")
