"""
Individual narx — tarifsiz bola (docs/03 §11.1, 2026-10).

Mijozning so'rovi: xususiy bog'chada standart narx yo'q, har bir oila bilan
alohida kelishiladi. Narx manbai BITTA bo'lishi kerak — yo tarif, yo
individual summa — aks holda hisob-fakturaga qaysi biri tushishi noaniq.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.children.models import Child
from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context
from apps.finance import services
from apps.finance.models import Discount, InvoiceLine, TariffPlan
from apps.finance.selectors import child_monthly_price

pytestmark = pytest.mark.django_db


@pytest.fixture
def tariff(tenant_a) -> TariffPlan:
    with organization_context(tenant_a.organization.id):
        return TariffPlan.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            name="To'liq kun",
            amount=Decimal("1500000.00"),
        )


def _child(tenant, *, fee: str | None = None, tariff=None, name: str = "Ali") -> Child:
    with organization_context(tenant.organization.id):
        return Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name=name,
            last_name="Valiyev",
            date_of_birth=date(2021, 3, 14),
            gender="male",
            tariff=tariff,
            monthly_fee=Decimal(fee) if fee else None,
        )


class TestInvoiceFromIndividualPrice:
    def test_invoice_uses_the_individual_amount(self, tenant_a):
        child = _child(tenant_a, fee="1250000")
        with organization_context(tenant_a.organization.id):
            invoice = services.issue_invoice(child=child, period_year=2026, period_month=9)
            line = InvoiceLine.objects.filter(invoice=invoice).first()

        assert invoice.amount_due == Decimal("1250000.00")
        # Hujjat qaysi tarifdan EMASligini ochiq ko'rsatadi.
        assert invoice.tariff_id is None
        assert line is not None
        assert line.description.startswith("Individual narx")
        assert line.line_total == Decimal("1250000.00")

    def test_discount_applies_to_the_individual_amount(self, tenant_a):
        child = _child(tenant_a, fee="1000000")
        with organization_context(tenant_a.organization.id):
            Discount.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                child=child,
                discount_type="percent",
                value=Decimal("10"),
                valid_from=date(2026, 1, 1),
                reason="Aka-uka",
            )
            invoice = services.issue_invoice(child=child, period_year=2026, period_month=9)
        assert invoice.amount_due == Decimal("900000.00")

    def test_changing_the_price_does_not_rewrite_past_invoices(self, tenant_a):
        """Narx hisob-fakturaga NUSXALANADI — tarif bilan bir xil qoida."""
        child = _child(tenant_a, fee="1000000")
        with organization_context(tenant_a.organization.id):
            september = services.issue_invoice(child=child, period_year=2026, period_month=9)
            Child.objects.filter(pk=child.pk).update(monthly_fee=Decimal("1200000"))
            child.refresh_from_db()
            october = services.issue_invoice(child=child, period_year=2026, period_month=10)
            september.refresh_from_db()

        assert september.amount_due == Decimal("1000000.00")
        assert october.amount_due == Decimal("1200000.00")

    def test_child_without_any_price_is_refused_with_a_clear_message(self, tenant_a):
        child = _child(tenant_a)
        with (
            organization_context(tenant_a.organization.id),
            pytest.raises(BusinessRuleViolation, match="narx belgilanmagan"),
        ):
            services.issue_invoice(child=child, period_year=2026, period_month=9)

    def test_monthly_run_includes_individual_price_and_skips_unpriced(self, tenant_a, tariff):
        _child(tenant_a, fee="900000", name="Individual")
        _child(tenant_a, tariff=tariff, name="Tarifli")
        _child(tenant_a, name="Narxsiz")
        with organization_context(tenant_a.organization.id):
            result = services.generate_monthly_invoices(
                organization=tenant_a.organization, period_year=2026, period_month=9
            )
        assert result.created == 2
        assert [name for name in result.skipped_no_tariff if "Narxsiz" in name]
        assert not [name for name in result.skipped_no_tariff if "Individual" in name]


class TestOnePriceSource:
    def test_database_refuses_both_sources(self, tenant_a, tariff):
        with (
            organization_context(tenant_a.organization.id),
            pytest.raises(IntegrityError),
            transaction.atomic(),
        ):
            Child.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                first_name="Ikki",
                last_name="Narx",
                date_of_birth=date(2021, 3, 14),
                gender="male",
                tariff=tariff,
                monthly_fee=Decimal("100000"),
            )

    @pytest.mark.parametrize("fee", ["0.00", "-1.00"])
    def test_database_refuses_zero_or_negative_fee(self, tenant_a, fee):
        with (
            organization_context(tenant_a.organization.id),
            pytest.raises(IntegrityError),
            transaction.atomic(),
        ):
            Child.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                first_name="Nol",
                last_name="Narx",
                date_of_birth=date(2021, 3, 14),
                gender="male",
                monthly_fee=Decimal(fee),
            )

    def test_price_helper(self, tenant_a, tariff):
        with organization_context(tenant_a.organization.id):
            by_tariff = child_monthly_price(_child(tenant_a, tariff=tariff, name="A"))
            by_fee = child_monthly_price(_child(tenant_a, fee="700000", name="B"))
            nothing = child_monthly_price(_child(tenant_a, name="C"))
        assert by_tariff is not None and by_tariff.amount == Decimal("1500000.00")
        assert by_tariff.tariff == tariff
        assert by_fee is not None and by_fee.amount == Decimal("700000.00")
        assert by_fee.tariff is None
        assert nothing is None


class TestApi:
    def _url(self, child: Child) -> str:
        return f"/api/v1/children/{child.id}"

    def test_setting_a_fee_clears_the_tariff(self, tenant_a, tariff):
        child = _child(tenant_a, tariff=tariff)
        response = tenant_a.client().patch(
            self._url(child), {"monthly_fee": "1100000"}, format="json"
        )
        assert response.status_code == 200, response.json()
        data = response.json()["data"]
        assert data["monthly_fee"] == "1100000.00"
        assert data["tariff"] is None

    def test_choosing_a_tariff_clears_the_fee(self, tenant_a, tariff):
        child = _child(tenant_a, fee="1100000")
        response = tenant_a.client().patch(
            self._url(child), {"tariff_id": str(tariff.id)}, format="json"
        )
        assert response.status_code == 200, response.json()
        data = response.json()["data"]
        assert data["tariff"] == str(tariff.id)
        assert data["monthly_fee"] is None

    def test_both_at_once_is_a_validation_error(self, tenant_a, tariff):
        child = _child(tenant_a)
        response = tenant_a.client().patch(
            self._url(child),
            {"tariff_id": str(tariff.id), "monthly_fee": "500000"},
            format="json",
        )
        assert response.status_code == 400
        assert "monthly_fee" in response.json()["error"]["details"]

    def test_zero_fee_is_refused(self, tenant_a):
        child = _child(tenant_a)
        response = tenant_a.client().patch(self._url(child), {"monthly_fee": "0"}, format="json")
        assert response.status_code == 400

    def test_create_with_individual_price(self, tenant_a):
        response = tenant_a.client().post(
            "/api/v1/children",
            {
                "first_name": "Yangi",
                "last_name": "Bola",
                "date_of_birth": "2021-05-01",
                "gender": "female",
                "monthly_fee": "1350000",
            },
            format="json",
        )
        assert response.status_code == 201, response.json()
        assert response.json()["data"]["monthly_fee"] == "1350000.00"

    def test_cross_tenant_child_is_404(self, tenant_a, tenant_b):
        """Begona tashkilotning bolasiga narx qo'yib bo'lmaydi — `404`, `403` emas."""
        foreign = _child(tenant_b, name="Begona")
        response = tenant_a.client().patch(
            self._url(foreign), {"monthly_fee": "1000"}, format="json"
        )
        assert response.status_code == 404
        with organization_context(tenant_b.organization.id):
            foreign.refresh_from_db()
            assert foreign.monthly_fee is None
