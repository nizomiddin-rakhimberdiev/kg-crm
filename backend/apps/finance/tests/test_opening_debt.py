"""
Mavjud mijoz va uning eski qarzi (PLAN 7.8).

Bog'cha tizimga o'tganda bolalarning bir qismi allaqachon qatnab
yurgan bo'ladi. Ular uchun ikki narsa boshqacha:

* birinchi oy proporsional EMAS — ular butun oy qatnagan;
* eski qarzi bor bo'lsa, u ledger'ga tushadi va qarzdorlar ro'yxatida
  darhol ko'rinadi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from apps.children.models import Child
from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context
from apps.finance.balance import child_balance
from apps.finance.models import TariffPlan
from apps.finance.selectors import debtor_queryset
from apps.finance.services import first_month_share, issue_invoice, record_opening_debt

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]

PRICE = Decimal("3050000")


def _child(tenant, *, existing: bool, enrolled_on: date | None = date(2026, 9, 25)) -> Child:
    with organization_context(tenant.organization.id):
        tariff = TariffPlan.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            name=f"Tarif {existing}{enrolled_on}",
            amount=PRICE,
        )
        return Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Ali",
            last_name="Valiyev",
            date_of_birth=date(2021, 1, 1),
            gender="male",
            tariff=tariff,
            enrolled_on=enrolled_on,
            is_existing_client=existing,
        )


class TestProration:
    def test_an_existing_client_pays_the_full_month(self, tenant_a):
        """Oyning 25-kuni kiritilgan, lekin u allaqachon qatnab yurgan."""
        child = _child(tenant_a, existing=True)
        with organization_context(tenant_a.organization.id):
            assert first_month_share(child=child, period_year=2026, period_month=9) is None
            invoice = issue_invoice(child=child, period_year=2026, period_month=9)
        assert invoice.amount_due == PRICE

    def test_a_new_client_on_the_same_day_pays_for_four_days(self, tenant_a):
        child = _child(tenant_a, existing=False)
        with organization_context(tenant_a.organization.id):
            invoice = issue_invoice(child=child, period_year=2026, period_month=9)
        assert invoice.amount_due == Decimal("554545.00")


class TestOpeningDebt:
    def test_the_debt_shows_up_in_the_debtors_list(self, tenant_a):
        child = _child(tenant_a, existing=True)
        with organization_context(tenant_a.organization.id):
            record_opening_debt(child=child, amount=Decimal("1200000"))
            assert child_balance(child).balance == Decimal("1200000.00")
            assert list(debtor_queryset().values_list("id", flat=True)) == [child.id]

    def test_zero_writes_nothing(self, tenant_a):
        child = _child(tenant_a, existing=True)
        with organization_context(tenant_a.organization.id):
            assert record_opening_debt(child=child, amount=Decimal("0")) is None
            assert child_balance(child).balance == Decimal("0")
            assert not debtor_queryset().exists()

    def test_it_refuses_to_double_the_debt(self, tenant_a):
        """Import ikki marta ishga tushsa qarz ikkilanmaydi."""
        child = _child(tenant_a, existing=True)
        with organization_context(tenant_a.organization.id):
            record_opening_debt(child=child, amount=Decimal("1200000"))
            with pytest.raises(BusinessRuleViolation):
                record_opening_debt(child=child, amount=Decimal("1200000"))
            assert child_balance(child).balance == Decimal("1200000.00")

    def test_a_payment_closes_it_like_any_other_debt(self, tenant_a):
        from apps.finance.services import record_payment

        child = _child(tenant_a, existing=True)
        with organization_context(tenant_a.organization.id):
            record_opening_debt(child=child, amount=Decimal("1200000"))
            record_payment(child=child, amount=Decimal("1200000"), method="cash")
            assert child_balance(child).balance == Decimal("0")
            assert not debtor_queryset().exists()
