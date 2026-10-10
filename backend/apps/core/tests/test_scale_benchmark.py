"""
Miqyos oʻlchovi: 300 bolalik bogʻcha (PLAN 11.6).

Bu test **tezlikni** emas, **soʻrovlar SONINI** qoʻriqlaydi. Sabab:
vaqt mashinaga bogʻliq va CI'da foydasiz, N+1 esa mashinaga bogʻliq
emas — u bolalar soni bilan chiziqli oʻsadigan xato va kichik
maʼlumotda butunlay koʻrinmaydi. Jonli bazada hozir 82 ta bola bor,
yaʼni 300 ta bolali bogʻchada nima boʻlishini u yerda oʻlchab
boʻlmaydi.

Chegaralar ataylab biroz keng: maqsad — regressiyani ushlash
("qarzdorlar soʻrovi endi har bir bola uchun bittadan soʻrov
qiladi"), har bir qoʻshilgan `select_related` ni hisoblash emas.
"""

from __future__ import annotations

import time
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.core.tenancy import organization_context

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]

CHILDREN = 300


@pytest.fixture(scope="function")
def big_tenant(tenant_a: Any) -> Any:
    """300 bola, har birida tarif, hisob-faktura va qisman toʻlov."""
    from apps.children.models import Child
    from apps.finance import services as finance
    from apps.finance.models import TariffPlan

    tenant_a.fund(kind="all")
    with organization_context(tenant_a.organization.id):
        tariff = TariffPlan.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            name="Toʻliq kun",
            amount=Decimal("1500000"),
        )
        children = Child.objects.bulk_create(
            Child(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                first_name=f"Bola{i:03d}",
                last_name="Testov",
                date_of_birth=date(2021, 3, 14),
                gender="male",
                tariff=tariff,
            )
            for i in range(CHILDREN)
        )
        # Har uchinchi bola toʻlagan — qarzdorlar roʻyxati boʻsh ham,
        # toʻliq ham boʻlmasin.
        for index, child in enumerate(children):
            finance.issue_invoice(child=child, period_year=2026, period_month=10)
            if index % 3 == 0:
                finance.record_payment(child=child, amount=Decimal("1500000"), method="cash")
    return tenant_a


def _measure(label: str, fn: Any) -> int:
    with CaptureQueriesContext(connection) as ctx:
        started = time.perf_counter()
        fn()
        elapsed = (time.perf_counter() - started) * 1000
    print(f"  {label:<28} {len(ctx):>4} soʻrov  {elapsed:>7.0f} ms")
    return len(ctx)


class TestQueryCountDoesNotGrowWithChildren:
    """Har bir soʻrov soni BOLALAR SONIDAN qatʼi nazar bir xil boʻlsin."""

    def test_debtors_list(self, big_tenant: Any):
        client = big_tenant.client()
        count = _measure("qarzdorlar", lambda: client.get("/api/v1/debtors?page_size=50"))
        # 50 ta qator uchun ~15 so'rov yetarli; 300 ta bo'lsa — N+1.
        assert count < 40, f"qarzdorlar roʻyxati {count} ta soʻrov qildi — N+1 ehtimoli"

    def test_dashboard(self, big_tenant: Any):
        client = big_tenant.client()
        count = _measure("dashboard", lambda: client.get("/api/v1/dashboard"))
        assert count < 60, f"dashboard {count} ta soʻrov qildi"

    def test_payments_board(self, big_tenant: Any):
        client = big_tenant.client()
        count = _measure(
            "toʻlovlar doskasi", lambda: client.get("/api/v1/payments/board?page_size=50")
        )
        assert count < 40, f"toʻlovlar doskasi {count} ta soʻrov qildi"

    def test_revenue_report(self, big_tenant: Any):
        client = big_tenant.client()
        count = _measure(
            "tushum hisoboti",
            lambda: client.get("/api/v1/reports/revenue?date_from=2026-10-01&date_to=2026-10-31"),
        )
        assert count < 30, f"tushum hisoboti {count} ta soʻrov qildi"

    def test_children_list(self, big_tenant: Any):
        client = big_tenant.client()
        count = _measure("bolalar roʻyxati", lambda: client.get("/api/v1/children?page_size=50"))
        assert count < 30, f"bolalar roʻyxati {count} ta soʻrov qildi"
