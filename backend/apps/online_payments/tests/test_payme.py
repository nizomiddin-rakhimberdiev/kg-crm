"""
Payme Merchant API (PLAN 6.1).

Each test is one rule the money depends on: the key is checked first,
amounts arrive in tiyin, a retried call never records money twice, a
cancellation after payment is a reversal, and another kindergarten's
invoice is "not found".
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from apps.core.tenancy import organization_context
from apps.online_payments.tests.conftest import make_invoice, payme_auth

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]


def _call(api_client, tenant, method: str, params: dict, *, auth: str | None = None, rpc_id=1):
    response = api_client.post(
        f"/api/v1/public/pay/payme/{tenant.organization.id}",
        {"method": method, "params": params, "id": rpc_id},
        format="json",
        HTTP_AUTHORIZATION=auth if auth is not None else payme_auth(),
    )
    assert response.status_code == 200  # Payme always gets 200
    return response.json()


def _account(invoice) -> dict:
    return {"invoice": str(invoice.id)}


def _balance(tenant, invoice):
    from apps.finance.balance import child_balance

    with organization_context(tenant.organization.id):
        invoice.refresh_from_db()
        return invoice, child_balance(invoice.child)


def _pay(api_client, tenant, invoice, txn_id: str = "p-1", tiyin: int = 150_000_000):
    params = {
        "id": txn_id,
        "time": 1_700_000_000_000,
        "amount": tiyin,
        "account": _account(invoice),
    }
    created = _call(api_client, tenant, "CreateTransaction", params)
    assert "result" in created, created
    return _call(api_client, tenant, "PerformTransaction", {"id": txn_id})


class TestAuth:
    def test_a_wrong_key_is_refused_before_anything_else(
        self, api_client, tenant_a, payme, invoice
    ):
        body = _call(
            api_client,
            tenant_a,
            "CheckPerformTransaction",
            {"amount": 100, "account": _account(invoice)},
            auth=payme_auth("wrong"),
        )
        assert body["error"]["code"] == -32504

    def test_without_configured_keys_nothing_works(self, api_client, tenant_a, invoice):
        body = _call(api_client, tenant_a, "CheckPerformTransaction", {"amount": 100})
        assert body["error"]["code"] == -32504

    def test_the_key_is_stored_encrypted(self, tenant_a, payme):
        from apps.online_payments.models import MerchantCredential
        from apps.online_payments.tests.conftest import PAYME_KEY

        with organization_context(tenant_a.organization.id):
            row = MerchantCredential.objects.get(pk=payme.pk)
        assert PAYME_KEY not in row.secret_encrypted
        assert row.secret_hint == PAYME_KEY[-4:]


class TestCheck:
    def test_an_open_invoice_is_payable(self, api_client, tenant_a, payme, invoice):
        body = _call(
            api_client,
            tenant_a,
            "CheckPerformTransaction",
            {"amount": 150_000_000, "account": _account(invoice)},
        )
        assert body["result"] == {"allow": True}

    def test_more_than_the_outstanding_amount_is_refused(
        self, api_client, tenant_a, payme, invoice
    ):
        body = _call(
            api_client,
            tenant_a,
            "CheckPerformTransaction",
            {"amount": 150_000_001, "account": _account(invoice)},
        )
        assert body["error"]["code"] == -31001

    def test_an_unknown_invoice_is_not_found(self, api_client, tenant_a, payme):
        body = _call(
            api_client,
            tenant_a,
            "CheckPerformTransaction",
            {"amount": 100, "account": {"invoice": "00000000-0000-0000-0000-000000000000"}},
        )
        assert body["error"]["code"] == -31050

    def test_another_kindergartens_invoice_is_not_found(
        self, api_client, tenant_a, tenant_b, payme
    ):
        """Payme calls tenant A's URL with tenant B's invoice — RLS hides it."""
        foreign = make_invoice(tenant_b)
        body = _call(
            api_client,
            tenant_a,
            "CheckPerformTransaction",
            {"amount": 100, "account": _account(foreign)},
        )
        assert body["error"]["code"] == -31050


class TestPerform:
    def test_payment_is_recorded_like_a_cashiers(self, api_client, tenant_a, payme, invoice):
        from apps.cash.models import CashMovement
        from apps.finance.models import Payment

        body = _pay(api_client, tenant_a, invoice)
        assert body["result"]["state"] == 2

        invoice, balance = _balance(tenant_a, invoice)
        assert invoice.status == "paid"
        assert balance.balance == Decimal("0")
        with organization_context(tenant_a.organization.id):
            payment = Payment.objects.get()
            assert payment.method == "payme"
            assert payment.amount == Decimal("1500000.00")
            movement = CashMovement.objects.get(source_id=payment.id)
            # Payme puli bank hisobiga tushadi (2026-10-14); usul — toʻlovda.
            assert movement.cash_account.handles_method == "bank_transfer"

    def test_a_retried_perform_records_money_once(self, api_client, tenant_a, payme, invoice):
        from apps.finance.models import Payment

        _pay(api_client, tenant_a, invoice)
        again = _call(api_client, tenant_a, "PerformTransaction", {"id": "p-1"})
        assert again["result"]["state"] == 2
        with organization_context(tenant_a.organization.id):
            assert Payment.objects.count() == 1

    def test_a_retried_create_returns_the_same_transaction(
        self, api_client, tenant_a, payme, invoice
    ):
        params = {"id": "p-2", "time": 1, "amount": 100_000, "account": _account(invoice)}
        first = _call(api_client, tenant_a, "CreateTransaction", params)
        second = _call(api_client, tenant_a, "CreateTransaction", params)
        assert first["result"]["transaction"] == second["result"]["transaction"]

    def test_a_second_pending_transaction_on_one_invoice_is_refused(
        self, api_client, tenant_a, payme, invoice
    ):
        _call(
            api_client,
            tenant_a,
            "CreateTransaction",
            {"id": "a", "time": 1, "amount": 100_000, "account": _account(invoice)},
        )
        body = _call(
            api_client,
            tenant_a,
            "CreateTransaction",
            {"id": "b", "time": 1, "amount": 100_000, "account": _account(invoice)},
        )
        assert body["error"]["code"] == -31051

    def test_an_expired_transaction_cannot_be_performed(self, api_client, tenant_a, payme, invoice):
        from datetime import timedelta

        from django.utils import timezone

        from apps.online_payments.models import OnlineTransaction

        _call(
            api_client,
            tenant_a,
            "CreateTransaction",
            {"id": "old", "time": 1, "amount": 100_000, "account": _account(invoice)},
        )
        with organization_context(tenant_a.organization.id):
            OnlineTransaction.objects.update(created_at=timezone.now() - timedelta(hours=13))
        body = _call(api_client, tenant_a, "PerformTransaction", {"id": "old"})
        assert body["error"]["code"] == -31008
        state = _call(api_client, tenant_a, "CheckTransaction", {"id": "old"})["result"]
        assert state["state"] == -1 and state["reason"] == 4


class TestCancel:
    def test_cancelling_before_payment_touches_no_money(self, api_client, tenant_a, payme, invoice):
        _call(
            api_client,
            tenant_a,
            "CreateTransaction",
            {"id": "c", "time": 1, "amount": 100_000, "account": _account(invoice)},
        )
        body = _call(api_client, tenant_a, "CancelTransaction", {"id": "c", "reason": 3})
        assert body["result"]["state"] == -1
        _invoice, balance = _balance(tenant_a, invoice)
        assert balance.balance == Decimal("1500000.00")

    def test_cancelling_after_payment_is_a_reversal(self, api_client, tenant_a, payme, invoice):
        from apps.finance.models import Payment

        _pay(api_client, tenant_a, invoice)
        body = _call(api_client, tenant_a, "CancelTransaction", {"id": "p-1", "reason": 5})
        assert body["result"]["state"] == -2

        invoice, balance = _balance(tenant_a, invoice)
        assert balance.balance == Decimal("1500000.00")
        with organization_context(tenant_a.organization.id):
            # Append-only: the payment row stays, marked as reversed.
            assert Payment.objects.get().is_reversed


class TestStatement:
    def test_statement_lists_transactions_in_the_window(self, api_client, tenant_a, payme, invoice):
        _pay(api_client, tenant_a, invoice)
        body = _call(api_client, tenant_a, "GetStatement", {"from": 0, "to": 9_999_999_999_999})
        (row,) = body["result"]["transactions"]
        assert row["id"] == "p-1" and row["amount"] == 150_000_000 and row["state"] == 2
