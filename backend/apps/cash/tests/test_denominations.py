"""Kun yopilishi kupyuralar bo'yicha (Bosqich 13.3b, brif §4) — 1 daqiqada."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from apps.cash import services as cash
from apps.cash.models import CashAccount
from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import services as finance

pytestmark = pytest.mark.django_db


def _till(tenant: Any) -> CashAccount:
    with organization_context(tenant.organization.id):
        cash.ensure_branch_accounts(branch=tenant.branch)
        return CashAccount.objects.get(branch=tenant.branch, kind="cash", is_active=True)


def _take(tenant: Any, amount: str) -> None:
    with organization_context(tenant.organization.id):
        child = Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Ali",
            last_name="Valiyev",
            date_of_birth=date(2021, 3, 14),
            gender="male",
        )
        finance.record_payment(child=child, amount=Decimal(amount), method="cash")


def test_the_count_is_the_sum_of_the_notes(tenant_a: Any):
    _take(tenant_a, "1250000")
    response = tenant_a.client().post(
        "/api/v1/cash-counts",
        {
            "cash_account_id": str(_till(tenant_a).id),
            "denominations": {"200000": 5, "100000": 2, "50000": 1},
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    data = response.json()["data"]
    assert Decimal(data["counted"]) == Decimal("1250000")
    assert data["denominations"] == {"200000": 5, "100000": 2, "50000": 1}
    assert Decimal(data["difference"]) == 0


def test_notes_and_a_different_total_disagree(tenant_a: Any):
    _take(tenant_a, "1000000")
    response = tenant_a.client().post(
        "/api/v1/cash-counts",
        {
            "cash_account_id": str(_till(tenant_a).id),
            "counted": "900000",
            "reason": "Sinov",
            "denominations": {"200000": 5},
        },
        format="json",
    )
    assert response.status_code == 422


def test_a_bad_note_is_refused(tenant_a: Any):
    response = tenant_a.client().post(
        "/api/v1/cash-counts",
        {"cash_account_id": str(_till(tenant_a).id), "counted": "0", "denominations": {"abc": 2}},
        format="json",
    )
    assert response.status_code in (400, 422)
