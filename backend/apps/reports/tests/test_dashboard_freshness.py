"""
Dashboard keshi pul harakatidan keyin darhol yangilanadi.

`invalidate_dashboard()` mavjud edi va docstring'i "to'lov, chiqim yoki
oylik yozilganda keshni bekor qiladi" derdi — lekin uni hech kim
chaqirmasdi. Natija: to'lov yoki qaytarishdan keyin 120 soniya
davomida dashboard eski qarzni ko'rsatardi, qarzdorlar ro'yxati esa
yangisini — bitta bola, ikki raqam. Yakuniy qabul ssenariysi (brief §6,
6-qadam) topdi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from apps.core.tenancy import organization_context

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]


def _kpis(tenant):
    from apps.reports.services import dashboard_kpis

    with organization_context(tenant.organization.id):
        return dashboard_kpis(organization_id=tenant.organization.id)


def test_a_payment_and_its_reversal_show_up_immediately(
    tenant_a, django_capture_on_commit_callbacks
):
    from apps.children.models import Child
    from apps.finance.models import TariffPlan
    from apps.finance.services import issue_invoice, record_payment, reverse_payment

    org, branch = tenant_a.organization, tenant_a.branch
    with organization_context(org.id):
        tariff = TariffPlan.objects.create(
            organization=org, branch=branch, name="T", amount=Decimal("1000000")
        )
        child = Child.objects.create(
            organization=org,
            branch=branch,
            first_name="Ali",
            last_name="Valiyev",
            date_of_birth=date(2022, 1, 1),
            gender="male",
            tariff=tariff,
            enrolled_on=date(2026, 9, 1),
        )
        issue_invoice(child=child, period_year=2026, period_month=9)

    assert Decimal(_kpis(tenant_a)["outstanding_debt"]) == Decimal("1000000")  # keshga tushdi

    # `execute=True` — commit'ni taqlid qiladi: kesh aynan shunda bekor bo'ladi.
    with django_capture_on_commit_callbacks(execute=True), organization_context(org.id):
        payment = record_payment(child=child, amount=Decimal("1000000"), method="cash")
    assert Decimal(_kpis(tenant_a)["outstanding_debt"]) == Decimal("0")

    with django_capture_on_commit_callbacks(execute=True), organization_context(org.id):
        reverse_payment(payment=payment, reason="xato")
    assert Decimal(_kpis(tenant_a)["outstanding_debt"]) == Decimal("1000000")
