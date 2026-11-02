"""
Qarzdorlik tarixi davr boʻyicha (PLAN 9.2).

Egasining savoli aynan shunday edi: sentabrda 15 boladan 28 mln qolgan,
oktabrda 24 mln yopilgan, 4 mln qolgan, ustiga oktabrning oʻz qarzi —
"qachonniki? qachon toʻlandi? nima orqali? qancha qoldi?".

Javob allaqachon bazada bor: `payment_allocation` qaysi pul qaysi
hisob-fakturani yopganini yozadi (ADR-20). Bu test shu bogʻlanish
hisobotga toʻgʻri chiqishini qoʻriqlaydi — yaʼni oktabrda toʻlangan pul
SENTABRNING qarzini kamaytirishini, oktabrnikini emas.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import selectors, services
from apps.finance.models import TariffPlan

pytestmark = pytest.mark.django_db


def _child(tenant, name: str, amount: str = "2000000") -> Child:
    tariff = TariffPlan.objects.create(
        organization=tenant.organization,
        branch=tenant.branch,
        name=f"Tarif {name}",
        amount=Decimal(amount),
    )
    return Child.objects.create(
        organization=tenant.organization,
        branch=tenant.branch,
        first_name=name,
        last_name="Testov",
        date_of_birth=date(2021, 5, 5),
        gender="male",
        tariff=tariff,
        is_existing_client=True,
    )


class TestDebtByPeriod:
    def test_a_later_payment_closes_the_earlier_month(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            child = _child(tenant_a, "Ali", "2000000")
            september = services.issue_invoice(child=child, period_year=2026, period_month=9)
            services.issue_invoice(child=child, period_year=2026, period_month=10)
            # Oktabrda sentabr qarzi yopiladi (FIFO — eng eski muddat).
            services.record_payment(
                child=child,
                amount=Decimal("1500000"),
                method="cash",
                paid_at=date(2026, 10, 12),
            )

            rows = {
                row["period"]: row
                for row in selectors.debt_by_period(
                    date_from=date(2026, 9, 1), date_to=date(2026, 10, 31)
                )
            }

            assert rows["2026-09"]["invoiced"] == "2000000.00"
            assert rows["2026-09"]["paid"] == "1500000.00"
            assert rows["2026-09"]["outstanding"] == "500000.00"
            # Oktabrga tegilmagan: pul eski oyni yopdi.
            assert rows["2026-10"]["paid"] == "0.00"
            assert rows["2026-10"]["outstanding"] == "2000000.00"
            assert september.id is not None

    def test_a_period_row_counts_children_and_debtors(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            paid_child = _child(tenant_a, "Bek", "1000000")
            debtor = _child(tenant_a, "Dilnoza", "1000000")
            services.issue_invoice(child=paid_child, period_year=2026, period_month=9)
            services.issue_invoice(child=debtor, period_year=2026, period_month=9)
            services.record_payment(
                child=paid_child,
                amount=Decimal("1000000"),
                method="bank_transfer",
                paid_at=date(2026, 9, 8),
            )

            row = selectors.debt_by_period(date_from=date(2026, 9, 1), date_to=date(2026, 9, 30))[0]
            assert row["children"] == 2
            assert row["debtors"] == 1
            assert row["paid"] == "1000000.00"
            assert row["outstanding"] == "1000000.00"

    def test_the_detail_says_when_how_and_how_much(self, tenant_a):
        """Oyni ochganda: kim, qancha, qachon va nima orqali toʻladi."""
        with organization_context(tenant_a.organization.id):
            child = _child(tenant_a, "Said", "1800000")
            services.issue_invoice(child=child, period_year=2026, period_month=9)
            services.record_payment(
                child=child, amount=Decimal("800000"), method="cash", paid_at=date(2026, 9, 20)
            )
            services.record_payment(
                child=child, amount=Decimal("600000"), method="online", paid_at=date(2026, 10, 3)
            )

            rows = selectors.debt_period_children(period_year=2026, period_month=9)
            assert len(rows) == 1
            row = rows[0]
            assert row["child_name"].startswith("Testov")
            assert row["invoiced"] == "1800000.00"
            assert row["paid"] == "1400000.00"
            assert row["outstanding"] == "400000.00"
            assert [p["method"] for p in row["payments"]] == ["cash", "online"]
            assert [p["amount"] for p in row["payments"]] == ["800000.00", "600000.00"]
            assert row["payments"][1]["paid_at"].startswith("2026-10-03")

    def test_a_reversed_payment_stops_counting(self, tenant_a):
        """Qaytarilgan toʻlov qarzni yopmaydi — taqsimot boʻshatiladi."""
        with organization_context(tenant_a.organization.id):
            child = _child(tenant_a, "Zilola", "1200000")
            services.issue_invoice(child=child, period_year=2026, period_month=9)
            payment = services.record_payment(
                child=child, amount=Decimal("1200000"), method="cash", paid_at=date(2026, 9, 11)
            )
            services.reverse_payment(payment=payment, reason="Kassir xato kiritdi")

            row = selectors.debt_by_period(date_from=date(2026, 9, 1), date_to=date(2026, 9, 30))[0]
            assert row["paid"] == "0.00"
            assert row["outstanding"] == "1200000.00"


class TestDebtByPeriodApi:
    def test_the_endpoint_returns_rows_and_totals(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            child = _child(tenant_a, "Asal", "1500000")
            services.issue_invoice(child=child, period_year=2026, period_month=9)

        response = tenant_a.client().get("/api/v1/debtors/by-period?from=2026-09&to=2026-09")
        assert response.status_code == 200, response.content
        data = response.json()["data"]
        assert data["results"][0]["period"] == "2026-09"
        assert data["totals"]["outstanding"] == "1500000.00"

    def test_a_single_period_returns_the_children(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            child = _child(tenant_a, "Jasur", "1500000")
            services.issue_invoice(child=child, period_year=2026, period_month=9)

        response = tenant_a.client().get("/api/v1/debtors/by-period?period=2026-09")
        data = response.json()["data"]
        assert data["count"] == 1
        assert data["results"][0]["child_id"] == str(child.id)

    def test_a_broken_period_is_a_422_not_a_500(self, tenant_a):
        response = tenant_a.client().get("/api/v1/debtors/by-period?period=sentabr")
        assert response.status_code == 422, response.content

    def test_another_organization_sees_nothing(self, tenant_a, tenant_b):
        """Begona tashkilotning qarzi bu hisobotda umuman mavjud emas."""
        with organization_context(tenant_a.organization.id):
            child = _child(tenant_a, "Oybek", "1500000")
            services.issue_invoice(child=child, period_year=2026, period_month=9)

        data = tenant_b.client().get("/api/v1/debtors/by-period?period=2026-09").json()["data"]
        assert data["results"] == []
