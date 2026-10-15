"""Click SHOP-API — prepare/complete, signature and cancellation (PLAN 6.1)."""

from __future__ import annotations

import hashlib
from decimal import Decimal

import pytest

from apps.core.tenancy import organization_context
from apps.online_payments.tests.conftest import CLICK_KEY, make_invoice

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]


def _signed(fields: dict[str, str], key: str = CLICK_KEY) -> dict[str, str]:
    parts = [fields["click_trans_id"], fields["service_id"], key, fields["merchant_trans_id"]]
    if fields["action"] == "1":
        parts.append(fields["merchant_prepare_id"])
    parts += [fields["amount"], fields["action"], fields["sign_time"]]
    sign = hashlib.md5("".join(parts).encode(), usedforsecurity=False).hexdigest()
    return {**fields, "sign_string": sign}


def _post(api_client, tenant, fields: dict[str, str]) -> dict:
    response = api_client.post(f"/api/v1/public/pay/click/{tenant.organization.id}", fields)
    assert response.status_code == 200
    return response.json()


def _prepare(api_client, tenant, invoice, *, txn="9001", amount="1500000", key=CLICK_KEY):
    fields = {
        "click_trans_id": txn,
        "service_id": "777",
        "click_paydoc_id": "1",
        "merchant_trans_id": str(invoice.id),
        "amount": amount,
        "action": "0",
        "error": "0",
        "error_note": "",
        "sign_time": "2026-10-03 10:00:00",
    }
    return _post(api_client, tenant, _signed(fields, key))


def _complete(api_client, tenant, invoice, *, txn="9001", amount="1500000", error="0"):
    fields = {
        "click_trans_id": txn,
        "service_id": "777",
        "click_paydoc_id": "1",
        "merchant_trans_id": str(invoice.id),
        "merchant_prepare_id": txn,
        "amount": amount,
        "action": "1",
        "error": error,
        "error_note": "",
        "sign_time": "2026-10-03 10:00:05",
    }
    return _post(api_client, tenant, _signed(fields))


def _balance(tenant, invoice) -> Decimal:
    from apps.finance.balance import child_balance

    with organization_context(tenant.organization.id):
        return child_balance(invoice.child).balance


def test_prepare_then_complete_records_the_payment(api_client, tenant_a, click, invoice):
    from apps.finance.models import Payment

    prepared = _prepare(api_client, tenant_a, invoice)
    assert prepared["error"] == 0 and prepared["merchant_prepare_id"] == 9001
    completed = _complete(api_client, tenant_a, invoice)
    assert completed["error"] == 0 and completed["merchant_confirm_id"] == 9001

    assert _balance(tenant_a, invoice) == Decimal("0")
    with organization_context(tenant_a.organization.id):
        assert Payment.objects.get().method == "click"


def test_a_repeated_complete_records_money_once(api_client, tenant_a, click, invoice):
    from apps.finance.models import Payment

    _prepare(api_client, tenant_a, invoice)
    _complete(api_client, tenant_a, invoice)
    assert _complete(api_client, tenant_a, invoice)["error"] == 0
    with organization_context(tenant_a.organization.id):
        assert Payment.objects.count() == 1


def test_a_bad_signature_is_refused(api_client, tenant_a, click, invoice):
    assert _prepare(api_client, tenant_a, invoice, key="forged")["error"] == -1


def test_without_configured_keys_nothing_works(api_client, tenant_a, invoice):
    assert _prepare(api_client, tenant_a, invoice)["error"] == -1


def test_more_than_the_outstanding_amount_is_refused(api_client, tenant_a, click, invoice):
    assert _prepare(api_client, tenant_a, invoice, amount="1500001")["error"] == -2


def test_a_paid_invoice_answers_already_paid(api_client, tenant_a, click, invoice):
    _prepare(api_client, tenant_a, invoice)
    _complete(api_client, tenant_a, invoice)
    assert _prepare(api_client, tenant_a, invoice, txn="9002")["error"] == -4


def test_complete_without_prepare_is_unknown(api_client, tenant_a, click, invoice):
    assert _complete(api_client, tenant_a, invoice, txn="404")["error"] == -6


def test_another_kindergartens_invoice_is_not_found(api_client, tenant_a, tenant_b, click):
    foreign = make_invoice(tenant_b)
    assert _prepare(api_client, tenant_a, foreign)["error"] == -5


def test_click_side_failure_after_payment_is_reversed(api_client, tenant_a, click, invoice):
    _prepare(api_client, tenant_a, invoice)
    _complete(api_client, tenant_a, invoice)
    assert _balance(tenant_a, invoice) == Decimal("0")

    failed = _complete(api_client, tenant_a, invoice, error="-5017")
    assert failed["error"] == -9
    assert _balance(tenant_a, invoice) == Decimal("1500000.00")
