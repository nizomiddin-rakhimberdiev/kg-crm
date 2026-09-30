"""
To'lovlar jurnali — PLAN 1.8.

Buxgalterga ba'zan kesim emas, QATORLAR kerak: "1–15 sentabr orasida
terminal orqali kim nima to'lagan". Ilgari bunday ro'yxatni olishning
yagona yo'li ekrandan ko'chirib yozish edi.

Asosiy talab: ekrandagi filtr EKSPORTDA ham saqlanadi. Ikkalasi bitta
so'rovdan chiqadi, aks holda "ekranda 12 qator, faylda 40" degan farq
paydo bo'lardi va buxgalter qaysi biriga ishonishni bilmasdi.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import services
from apps.finance.models import TariffPlan
from apps.reports import selectors

pytestmark = pytest.mark.django_db


@pytest.fixture
def paid(tenant_a):
    """Ikki bola, uch to'lov, bittasi qaytarilgan."""
    with organization_context(tenant_a.organization.id):
        tariff = TariffPlan.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            name="To'liq kun",
            amount=Decimal("1500000"),
        )
        children = [
            Child.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                first_name=name,
                last_name="Testov",
                date_of_birth=date(2021, 3, 14),
                gender="female",
                tariff=tariff,
            )
            for name in ("Robiya", "Malika")
        ]
        services.record_payment(child=children[0], amount=Decimal("500000"), method="cash")
        services.record_payment(child=children[0], amount=Decimal("300000"), method="terminal")
        reversed_payment = services.record_payment(
            child=children[1], amount=Decimal("200000"), method="cash"
        )
        services.reverse_payment(payment=reversed_payment, reason="Xato")
    return children


def _summary(tenant, **params):
    return selectors.payment_journal_summary(
        organization_id=tenant.organization.id,
        date_from=timezone.localdate() - timedelta(days=1),
        date_to=timezone.localdate(),
        **params,
    )


class TestSummary:
    def test_reversed_payments_are_counted_but_not_totalled(self, tenant_a, paid):
        with organization_context(tenant_a.organization.id):
            summary = _summary(tenant_a)

        # 500 000 + 300 000 — qaytarilgan 200 000 pul emas.
        assert Decimal(summary["total"]) == Decimal("800000.00")
        assert summary["count"] == 2
        assert summary["reversed_count"] == 1

    def test_method_filter_narrows_the_total(self, tenant_a, paid):
        with organization_context(tenant_a.organization.id):
            summary = _summary(tenant_a, method="terminal")

        assert Decimal(summary["total"]) == Decimal("300000.00")
        assert summary["count"] == 1

    def test_child_filter_narrows_the_total(self, tenant_a, paid):
        with organization_context(tenant_a.organization.id):
            summary = _summary(tenant_a, child_id=paid[0].id)

        assert Decimal(summary["total"]) == Decimal("800000.00")

    def test_by_method_breaks_the_total_down(self, tenant_a, paid):
        with organization_context(tenant_a.organization.id):
            rows = {row["method"]: Decimal(row["total"]) for row in _summary(tenant_a)["by_method"]}

        assert rows == {"cash": Decimal("500000.00"), "terminal": Decimal("300000.00")}


class TestScreenAndExportAgree:
    def test_the_export_uses_the_same_filters(self, tenant_a, paid):
        """Ekranda "terminal" tanlansa, faylda ham faqat terminal chiqadi."""
        with organization_context(tenant_a.organization.id):
            summary = _summary(tenant_a, method="terminal")
            rows = selectors.revenue_rows(
                organization_id=tenant_a.organization.id,
                date_from=timezone.localdate() - timedelta(days=1),
                date_to=timezone.localdate(),
                method="terminal",
            )

        assert len(rows) == summary["count"]
        assert all(row["method"] == "Terminal" for row in rows)


class TestEndpoint:
    def test_summary_endpoint_is_scoped_to_the_tenant(self, tenant_a, tenant_b, paid):
        response = tenant_b.client().get(reverse("v1:payment-journal-summary"))
        assert response.status_code == 200
        assert Decimal(response.data["total"]) == Decimal("0.00")

    def test_summary_endpoint_returns_the_total(self, tenant_a, paid):
        response = tenant_a.client().get(reverse("v1:payment-journal-summary"))
        assert response.status_code == 200
        assert Decimal(response.data["total"]) == Decimal("800000.00")
