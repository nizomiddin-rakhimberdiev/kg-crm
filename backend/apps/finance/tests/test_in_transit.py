"""
Yo'ldagi pul (Bosqich 13.2c, brif §3.1, test 8).

Terminal, Click va Payme orqali olingan pul bir kunda bankka tushmaydi:
to'lov tizimi uni komissiyasini ushlab, keyinroq o'tkazadi. Shu orada pul
bank hisobida "yo'lda" turadi — kutilgan summa = to'lov − komissiya,
kutilgan sana = to'lov kuni + `transit.settle_days`. Bank tushumi
tasdiqlanganda yopiladi; o'z vaqtida tushmasa — kechikkan.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

import pytest
from django.utils import timezone

from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import services as finance

pytestmark = pytest.mark.django_db

URL = "/api/v1/payments/in-transit"


def _pay(tenant: Any, method: str, amount: str, day: date | None = None) -> Any:
    with organization_context(tenant.organization.id):
        child = Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Ali",
            last_name="Valiyev",
            date_of_birth=date(2021, 3, 14),
            gender="male",
        )
        kwargs: dict[str, Any] = {}
        if day is not None:
            kwargs["paid_at"] = timezone.make_aware(datetime.combine(day, time(10)))
        return finance.record_payment(child=child, amount=Decimal(amount), method=method, **kwargs)


def _rows(tenant: Any) -> list[dict[str, Any]]:
    response = tenant.client().get(URL)
    assert response.status_code == 200, response.json()
    return response.json()["data"]["items"]


def test_8_a_click_payment_is_expected_next_day_net_of_commission(tenant_a: Any):
    today = timezone.localdate()
    payment = _pay(tenant_a, "click", "10000000", today)

    rows = _rows(tenant_a)

    assert len(rows) == 1
    row = rows[0]
    assert row["payment_id"] == str(payment.id)
    assert Decimal(row["commission"]) == Decimal("100000")
    assert Decimal(row["expected_amount"]) == Decimal("9900000")
    assert row["expected_on"] == (today + timedelta(days=1)).isoformat()
    assert row["overdue"] is False


def test_cash_and_bank_transfers_are_never_in_transit(tenant_a: Any):
    _pay(tenant_a, "cash", "500000")
    _pay(tenant_a, "bank_transfer", "500000")
    assert _rows(tenant_a) == []


def test_money_that_did_not_arrive_in_time_is_overdue(tenant_a: Any):
    _pay(tenant_a, "terminal", "1000000", timezone.localdate() - timedelta(days=5))
    row = _rows(tenant_a)[0]
    assert row["overdue"] is True


def test_a_confirmed_arrival_closes_it(tenant_a: Any):
    first = _pay(tenant_a, "payme", "2000000")
    second = _pay(tenant_a, "payme", "1000000")

    response = tenant_a.client().post(
        "/api/v1/payments/settle",
        {
            "payment_ids": [str(first.id), str(second.id)],
            "settled_on": timezone.localdate().isoformat(),
            "reference": "Payme reestr 15.10",
        },
        format="json",
    )

    assert response.status_code == 201, response.json()
    assert Decimal(response.json()["data"]["expected_total"]) == Decimal("2970000")
    assert _rows(tenant_a) == []


def test_a_payment_is_settled_once(tenant_a: Any):
    payment = _pay(tenant_a, "click", "1000000")
    body = {"payment_ids": [str(payment.id)], "settled_on": timezone.localdate().isoformat()}
    assert tenant_a.client().post("/api/v1/payments/settle", body, format="json").status_code == 201
    assert tenant_a.client().post("/api/v1/payments/settle", body, format="json").status_code == 422


def test_the_bank_balance_shows_what_arrived_and_what_is_on_the_way(tenant_a: Any):
    _pay(tenant_a, "bank_transfer", "3000000")
    _pay(tenant_a, "click", "1000000")
    rows = tenant_a.client().get("/api/v1/cash-accounts/balances").json()["data"]
    bank = next(row for row in rows if row["kind"] == "bank")
    assert Decimal(bank["balance"]) == Decimal("3990000")
    assert Decimal(bank["in_transit"]) == Decimal("990000")
    assert Decimal(bank["arrived"]) == Decimal("3000000")


def test_the_settle_days_are_a_setting(tenant_a: Any):
    from apps.settings_app.services import set_setting

    with organization_context(tenant_a.organization.id):
        set_setting(
            organization=tenant_a.organization,
            key="transit.settle_days",
            value=3,
            branch=tenant_a.branch,
        )
    today = timezone.localdate()
    _pay(tenant_a, "terminal", "1000000", today)
    assert _rows(tenant_a)[0]["expected_on"] == (today + timedelta(days=3)).isoformat()


@pytest.mark.tenancy
def test_another_tenants_payment_cannot_be_settled(tenant_a: Any, tenant_b: Any):
    payment = _pay(tenant_a, "click", "1000000")
    response = tenant_b.client().post(
        "/api/v1/payments/settle",
        {"payment_ids": [str(payment.id)], "settled_on": timezone.localdate().isoformat()},
        format="json",
    )
    assert response.status_code in (400, 404)
    assert len(_rows(tenant_a)) == 1
