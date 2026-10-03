"""
Click SHOP-API — Prepare (action 0) and Complete (action 1), PLAN 6.1.

Click posts form fields and expects JSON. Authenticity is the
`sign_string` — MD5 over the request fields and the kindergarten's secret:

    prepare:  click_trans_id service_id SECRET merchant_trans_id amount action sign_time
    complete: click_trans_id service_id SECRET merchant_trans_id merchant_prepare_id
              amount action sign_time

`merchant_trans_id` is the ledger's account — our invoice id for tuition,
the subscription invoice number for Radix (PLAN 6.4). Click wants an INTEGER
`merchant_prepare_id`; its own `click_trans_id` is unique and integer, so
it is echoed back and checked on Complete.

A Complete that arrives with `error < 0` means Click failed on its side:
the transaction is cancelled (reversed if the money was already recorded)
and answered with `-9`.
"""

from __future__ import annotations

import hashlib
import hmac
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import IntegrityError, transaction

from apps.online_payments.ledger import TUITION
from apps.online_payments.merchant import CannotCancel, Ledger, Merchant
from apps.online_payments.models import Provider, TxnState

__all__ = ["handle"]

OK = 0
SIGN_FAILED = -1
BAD_AMOUNT = -2
NO_ACTION = -3
ALREADY_PAID = -4
NOT_FOUND = -5
NO_TXN = -6
BAD_REQUEST = -8
CANCELLED = -9

NOTES = {
    OK: "Success",
    SIGN_FAILED: "SIGN CHECK FAILED!",
    BAD_AMOUNT: "Incorrect parameter amount",
    NO_ACTION: "Action not found",
    ALREADY_PAID: "Already paid",
    NOT_FOUND: "Invoice does not exist",
    NO_TXN: "Transaction does not exist",
    BAD_REQUEST: "Error in request from click",
    CANCELLED: "Transaction cancelled",
}


def _sign_ok(data: dict[str, str], secret: str) -> bool:
    parts = [data.get("click_trans_id", ""), data.get("service_id", ""), secret]
    parts.append(data.get("merchant_trans_id", ""))
    if data.get("action") == "1":
        parts.append(data.get("merchant_prepare_id", ""))
    parts += [data.get("amount", ""), data.get("action", ""), data.get("sign_time", "")]
    expected = hashlib.md5("".join(parts).encode(), usedforsecurity=False).hexdigest()
    return hmac.compare_digest(expected, data.get("sign_string", ""))


def _reply(data: dict[str, str], code: int, **extra: Any) -> dict[str, Any]:
    return {
        "click_trans_id": data.get("click_trans_id"),
        "merchant_trans_id": data.get("merchant_trans_id"),
        "error": code,
        "error_note": NOTES[code],
        **extra,
    }


def _amount(data: dict[str, str]) -> Decimal | None:
    try:
        amount = Decimal(data.get("amount", "")).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None
    return amount if amount > 0 else None


def _prepare(ledger: Ledger, data: dict[str, str]) -> dict[str, Any]:
    account = data.get("merchant_trans_id", "")
    target = ledger.find(account) if account else None
    if target is None:
        return _reply(data, NOT_FOUND)
    amount = _amount(data)
    if amount is None:
        return _reply(data, BAD_AMOUNT)
    payable = ledger.payable(target)
    if payable is None:
        return _reply(data, ALREADY_PAID if ledger.is_settled(target) else NOT_FOUND)
    if amount > payable:
        return _reply(data, BAD_AMOUNT)

    click_id = data.get("click_trans_id", "")
    txn = ledger.txns().filter(provider=Provider.CLICK, provider_txn_id=click_id).first()
    if txn is None:
        try:
            with transaction.atomic():
                txn = ledger.create_txn(
                    target, provider=Provider.CLICK, provider_txn_id=click_id, amount=amount
                )
        except IntegrityError:
            txn = ledger.txns().get(provider=Provider.CLICK, provider_txn_id=click_id)
    if txn.state < 0:
        return _reply(data, CANCELLED)
    return _reply(data, OK, merchant_prepare_id=int(click_id))


def _complete(ledger: Ledger, data: dict[str, str]) -> dict[str, Any]:
    click_id = data.get("click_trans_id", "")
    txn = (
        ledger.txns()
        .select_for_update()
        .filter(provider=Provider.CLICK, provider_txn_id=click_id)
        .first()
    )
    if txn is None or data.get("merchant_prepare_id", "") != click_id:
        return _reply(data, NO_TXN)
    if ledger.account_of(txn) != data.get("merchant_trans_id", ""):
        return _reply(data, NOT_FOUND)

    try:
        click_error = int(data.get("error", "0"))
    except ValueError:
        return _reply(data, BAD_REQUEST)
    if click_error < 0:
        try:
            ledger.cancel(txn, reason=click_error)
        except CannotCancel:
            return _reply(data, ALREADY_PAID)
        return _reply(data, CANCELLED)

    if txn.state < 0:
        return _reply(data, CANCELLED)
    if _amount(data) != txn.amount:
        return _reply(data, BAD_AMOUNT)
    if txn.state == TxnState.CREATED:
        ledger.perform(txn)
    return _reply(data, OK, merchant_confirm_id=int(click_id))


@transaction.atomic
def handle(data: dict[str, str], merchant: Merchant, ledger: Ledger = TUITION) -> dict[str, Any]:
    """One Click call; the ledger decides what is being paid."""
    if data.get("service_id", "") != merchant.service_id or not _sign_ok(data, merchant.secret):
        return _reply(data, SIGN_FAILED)
    action = data.get("action")
    if action == "0":
        return _prepare(ledger, data)
    if action == "1":
        return _complete(ledger, data)
    return _reply(data, NO_ACTION)
