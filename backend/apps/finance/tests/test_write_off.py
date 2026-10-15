"""
Qarz faqat hujjat bilan kechiriladi (Bosqich 12.3, brif §3 va 16-test).

Excel'da qarz qoldig'i ba'zan qo'lda 0 deb yozilardi va yashirin qarz paydo
bo'lardi. Tizimda qarz har doim `faktura − taqsimlangan to'lov`; uni qo'lda
o'zgartirishning yo'li yo'q. Kechirish — `hisobdan chiqarish` yozuvi:
summasi, SABABI va kim qilgani bilan, fakturada minus qator bo'lib.

Shu yerda bola kartasidagi oyma-oy qarz ham: "qaysi oylar uchun qancha?"
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.accounts.authentication import issue_token_pair
from apps.accounts.models import User
from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.finance.models import Invoice, TariffPlan

pytestmark = pytest.mark.django_db

URL = "/api/v1/debtors/write-off"


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


def _invoice(tenant: Any, child: Child, month: int = 9) -> Invoice:
    with organization_context(tenant.organization.id):
        return finance.issue_invoice(child=child, period_year=2026, period_month=month)


def _as(tenant: Any, role: str) -> APIClient:
    with organization_context(tenant.organization.id):
        user = User.objects.create_user(
            email=f"{role}@alfa.uz",
            password="Juda-Kuchli-Parol-2026",  # noqa: S106
            full_name=role,
            organization=tenant.organization,
            role=tenant.role(role),
            branch=tenant.branch,
        )
        tokens = issue_token_pair(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


def _balance(tenant: Any, child: Child) -> dict[str, Any]:
    response = tenant.client().get("/api/v1/ledger/balance", {"child": str(child.id)})
    assert response.status_code == 200
    return response.json()["data"]


# --- 16: qarzni qo'lda 0 qilib bo'lmaydi ---


def test_16_debt_cannot_be_zeroed_by_hand(tenant_a: Any):
    child = _child(tenant_a)
    invoice = _invoice(tenant_a, child)
    client = tenant_a.client()

    client.patch(f"/api/v1/children/{child.id}", {"balance": "0"}, format="json")
    assert client.patch(
        f"/api/v1/invoices/{invoice.id}", {"amount_due": "0"}, format="json"
    ).status_code in (403, 405)
    assert client.post(
        "/api/v1/ledger",
        {"child_id": str(child.id), "amount": "3050000", "direction": "credit"},
        format="json",
    ).status_code in (403, 404, 405)

    assert Decimal(_balance(tenant_a, child)["balance"]) == Decimal("3050000")


# --- Hisobdan chiqarish ---


def test_a_write_off_forgives_the_debt_with_reason_and_author(tenant_a: Any):
    child = _child(tenant_a)
    invoice = _invoice(tenant_a, child)

    response = tenant_a.client().post(
        URL,
        {"invoice_id": str(invoice.id), "amount": "50000", "reason": "Yaxlitlash farqi"},
        format="json",
    )

    assert response.status_code == 201, response.json()
    assert Decimal(_balance(tenant_a, child)["balance"]) == Decimal("3000000")
    with organization_context(tenant_a.organization.id):
        invoice.refresh_from_db()
        line = invoice.lines.get(kind="write_off")
        record = invoice.write_offs.get()
    assert invoice.amount_due == Decimal("3000000")
    assert "Yaxlitlash farqi" in line.description
    assert record.created_by_id == tenant_a.owner.id
    assert record.reason == "Yaxlitlash farqi"


def test_writing_off_everything_closes_the_invoice(tenant_a: Any):
    child = _child(tenant_a)
    invoice = _invoice(tenant_a, child)
    tenant_a.client().post(
        URL,
        {"invoice_id": str(invoice.id), "amount": "3050000", "reason": "Vafot — oila iltimosi"},
        format="json",
    )
    with organization_context(tenant_a.organization.id):
        invoice.refresh_from_db()
    assert invoice.status == "paid"
    assert Decimal(_balance(tenant_a, child)["balance"]) == Decimal("0")


def test_a_write_off_needs_a_reason(tenant_a: Any):
    invoice = _invoice(tenant_a, _child(tenant_a))
    response = tenant_a.client().post(
        URL, {"invoice_id": str(invoice.id), "amount": "1000", "reason": " "}, format="json"
    )
    assert response.status_code == 422


def test_more_than_is_owed_cannot_be_written_off(tenant_a: Any):
    child = _child(tenant_a)
    invoice = _invoice(tenant_a, child)
    with organization_context(tenant_a.organization.id):
        finance.record_payment(child=child, amount=Decimal("3000000"), method="cash")
    response = tenant_a.client().post(
        URL, {"invoice_id": str(invoice.id), "amount": "60000", "reason": "x"}, format="json"
    )
    assert response.status_code == 422


def test_a_cashier_cannot_forgive_debt(tenant_a: Any):
    invoice = _invoice(tenant_a, _child(tenant_a))
    response = _as(tenant_a, "cashier").post(
        URL, {"invoice_id": str(invoice.id), "amount": "1000", "reason": "x"}, format="json"
    )
    assert response.status_code == 403


@pytest.mark.tenancy
def test_another_tenants_invoice_is_404(tenant_a: Any, tenant_b: Any):
    invoice = _invoice(tenant_a, _child(tenant_a))
    response = tenant_b.client().post(
        URL, {"invoice_id": str(invoice.id), "amount": "1000", "reason": "x"}, format="json"
    )
    assert response.status_code in (400, 404)
    with organization_context(tenant_a.organization.id):
        invoice.refresh_from_db()
    assert invoice.amount_due == Decimal("3050000")


# --- Oyma-oy qarz ---


def test_the_balance_lists_debt_month_by_month(tenant_a: Any):
    child = _child(tenant_a)
    _invoice(tenant_a, child, 9)
    _invoice(tenant_a, child, 10)
    with organization_context(tenant_a.organization.id):
        finance.record_payment(child=child, amount=Decimal("1000000"), method="cash")

    months = _balance(tenant_a, child)["months"]

    assert [(row["period"], Decimal(row["outstanding"])) for row in months] == [
        ("2026-09", Decimal("2050000")),
        ("2026-10", Decimal("3050000")),
    ]
