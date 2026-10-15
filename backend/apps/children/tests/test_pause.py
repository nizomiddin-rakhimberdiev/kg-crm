"""
"Bir oylik ariza" — API (Bosqich 12.1).

Pauza oyi uchun hisob-faktura 0 so'm. Agar o'sha oy uchun faktura
allaqachon chiqarilgan va to'lanmagan bo'lsa (masalan ariza oyning
3-kunida keldi, 1-kungi avtomatik faktura chiqib bo'lgan), u mavjud yo'l
bilan bekor qilinadi va 0 so'mlik qayta yoziladi — tahrirlanmaydi. To'lov
tushgan bo'lsa, tizim to'xtaydi va sababini aytadi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.finance.models import Invoice, InvoiceStatus, TariffPlan

pytestmark = pytest.mark.django_db


def _child(tenant: Any) -> Child:
    with organization_context(tenant.organization.id):
        tariff = TariffPlan.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            name="Asosiy",
            amount=Decimal("3050000"),
        )
        return Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Ali",
            last_name="Valiyev",
            date_of_birth=date(2021, 3, 14),
            gender="male",
            tariff=tariff,
            is_existing_client=True,
        )


def _url(child: Child) -> str:
    return f"/api/v1/children/{child.id}/pauses"


def test_a_pause_is_created_and_listed(tenant_a: Any):
    child = _child(tenant_a)
    client = tenant_a.client()
    created = client.post(
        _url(child), {"month": "2026-11", "reason": "1 oylik ariza"}, format="json"
    )
    assert created.status_code == 201, created.json()
    listed = client.get(_url(child)).json()["data"]
    assert [row["month_from"] for row in listed] == ["2026-11-01"]


def test_a_reason_is_required(tenant_a: Any):
    response = tenant_a.client().post(
        _url(_child(tenant_a)), {"month": "2026-11", "reason": " "}, format="json"
    )
    assert response.status_code == 422


def test_an_unpaid_invoice_for_that_month_is_reissued_at_zero(tenant_a: Any):
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        finance.issue_invoice(child=child, period_year=2026, period_month=11)

    response = tenant_a.client().post(
        _url(child), {"month": "2026-11", "reason": "1 oylik ariza"}, format="json"
    )

    assert response.status_code == 201, response.json()
    with organization_context(tenant_a.organization.id):
        live = Invoice.objects.exclude(status=InvoiceStatus.CANCELLED).get(
            child=child, period_year=2026, period_month=11
        )
        cancelled = Invoice.objects.filter(child=child, status=InvoiceStatus.CANCELLED).count()
        child.refresh_from_db()
    assert live.amount_due == Decimal("0")
    assert cancelled == 1
    assert child.balance == Decimal("0")


def test_a_paid_month_cannot_be_paused_silently(tenant_a: Any):
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        finance.issue_invoice(child=child, period_year=2026, period_month=11)
        finance.record_payment(child=child, amount=Decimal("1000000"), method="cash")

    response = tenant_a.client().post(
        _url(child), {"month": "2026-11", "reason": "1 oylik ariza"}, format="json"
    )
    assert response.status_code == 422


@pytest.mark.tenancy
def test_another_tenants_child_is_404(tenant_a: Any, tenant_b: Any):
    child = _child(tenant_a)
    response = tenant_b.client().post(
        _url(child), {"month": "2026-11", "reason": "x"}, format="json"
    )
    assert response.status_code == 404
