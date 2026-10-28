"""
Komissiya tushum yonida koʻrinadi (mijoz soʻrovi, 2026-10-28).

Mijoz: "payme, click, terminalda qancha komissiya toʻlovi toʻlangan
boʻlsa pastda kichkina qizil yozuvda koʻrsatib tursin".

Raqam allaqachon bor edi — komissiya bank xarajati sifatida yoziladi
(Bosqich 12.5) — lekin u faqat Chiqimlar roʻyxatida turardi. Ya'ni
"terminaldan 10 mln keldi" degan qator haqiqatni yarimtasini aytardi:
bankning ulushi boshqa ekranda edi.

Manba BITTA boʻlishi kerak: dashboard ham, Hisobotlar ham
`revenue_report` ni oʻqiydi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.utils import timezone

from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.finance.models import TariffPlan
from apps.reports import selectors

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


def test_the_terminal_row_carries_its_commission(tenant_a):
    child = _child(tenant_a)
    today = timezone.localdate()
    with organization_context(tenant_a.organization.id):
        finance.record_payment(child=child, amount=Decimal("500000"), method="terminal")
        report = selectors.revenue_report(
            organization_id=tenant_a.organization.id, date_from=today, date_to=today
        )

    rows = {row["method"]: row for row in report["by_method"]}
    # Terminal 0,2 % — 500 000 dan 1 000 soʻm.
    assert rows["terminal"]["total"] == "500000.00"
    assert rows["terminal"]["commission"] == "1000.00"


def test_cash_has_no_commission(tenant_a):
    child = _child(tenant_a)
    today = timezone.localdate()
    with organization_context(tenant_a.organization.id):
        finance.record_payment(child=child, amount=Decimal("300000"), method="cash")
        report = selectors.revenue_report(
            organization_id=tenant_a.organization.id, date_from=today, date_to=today
        )

    rows = {row["method"]: row for row in report["by_method"]}
    assert rows["cash"]["commission"] == "0.00"
