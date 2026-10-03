"""
Payme Merchant API (JSON-RPC 2.0) — PLAN 6.1.

Payme calls our endpoint with one of six methods. Everything is HTTP 200;
errors travel in the JSON-RPC `error` object with Payme's own codes, and
Payme shows `message` to the payer — hence three languages.

Amounts arrive in TIYIN (integer); they become so'm as `Decimal(amount) / 100`
— never a float (brief, rule 4). Times are milliseconds since the epoch.

Authentication: `Authorization: Basic base64("Paycom:" + key)`, compared in
constant time with the merchant's key. A wrong key is answered before
anything else is looked at (`-32504`).

What is being paid comes from the `ledger` (`merchant.py`): a kindergarten's
invoice (PLAN 6.1) or Radix's subscription invoice (PLAN 6.4).
"""

from __future__ import annotations

import base64
import hmac
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.online_payments.ledger import TUITION
from apps.online_payments.merchant import CannotCancel, Ledger
from apps.online_payments.models import Provider, TxnState

__all__ = ["PaymeError", "authorised", "handle", "TXN_TIMEOUT"]

ACCOUNT_FIELD = "invoice"

#: Payme cancels an unperformed transaction after 12 hours (reason 4).
TXN_TIMEOUT = timedelta(hours=12)


class PaymeError(Exception):
    def __init__(self, code: int, uz: str, ru: str, en: str, data: str | None = None) -> None:
        super().__init__(en)
        self.code = code
        self.message = {"uz": uz, "ru": ru, "en": en}
        self.data = data


def _auth_failed() -> PaymeError:
    return PaymeError(-32504, "Ruxsat yoʻq", "Недостаточно привилегий", "Insufficient privileges")


def _not_found() -> PaymeError:
    return PaymeError(
        -31050, "Hisob topilmadi", "Счёт не найден", "Invoice not found", data=ACCOUNT_FIELD
    )


def _wrong_amount() -> PaymeError:
    return PaymeError(-31001, "Notoʻgʻri summa", "Неверная сумма", "Incorrect amount")


def _no_txn() -> PaymeError:
    return PaymeError(
        -31003, "Tranzaksiya topilmadi", "Транзакция не найдена", "Transaction not found"
    )


def _cannot_perform() -> PaymeError:
    return PaymeError(
        -31008,
        "Amalni bajarib boʻlmaydi",
        "Невозможно выполнить операцию",
        "Unable to perform the operation",
    )


def _busy() -> PaymeError:
    return PaymeError(
        -31051,
        "Bu hisob boʻyicha boshqa toʻlov kutilmoqda",
        "По этому счёту ожидается другой платёж",
        "Another payment for this invoice is pending",
        data=ACCOUNT_FIELD,
    )


def _cannot_cancel() -> PaymeError:
    return PaymeError(
        -31007,
        "Buyurtma bajarilgan, bekor qilib boʻlmaydi",
        "Заказ выполнен, отменить транзакцию невозможно",
        "The order is completed; the transaction cannot be cancelled",
    )


def authorised(header: str, secret: str) -> bool:
    if not header.startswith("Basic ") or not secret:
        return False
    try:
        decoded = base64.b64decode(header[6:]).decode()
    except (ValueError, UnicodeDecodeError):
        return False
    login, _, key = decoded.partition(":")
    return login == "Paycom" and hmac.compare_digest(key.encode(), secret.encode())


def _expired(txn: Any) -> bool:
    return txn.state == TxnState.CREATED and timezone.now() - txn.created_at > TXN_TIMEOUT


def _ms(moment: datetime | None) -> int:
    if moment is None:
        return 0
    return int(moment.astimezone(UTC).timestamp() * 1000)


def _amount(params: dict[str, Any]) -> Decimal:
    try:
        tiyin = int(params["amount"])
    except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
        raise _wrong_amount() from exc
    if tiyin <= 0:
        raise _wrong_amount()
    return (Decimal(tiyin) / Decimal(100)).quantize(Decimal("0.01"))


def _target(ledger: Ledger, params: dict[str, Any]) -> Any:
    raw = str((params.get("account") or {}).get(ledger.account_field, ""))
    # The tenant context (tuition) or the subscription domain (Radix) is
    # already set: anything outside it is simply not there — "not found".
    target = ledger.find(raw) if raw else None
    if target is None:
        raise _not_found()
    return target


def _check(ledger: Ledger, params: dict[str, Any]) -> tuple[Any, Decimal]:
    target = _target(ledger, params)
    amount = _amount(params)
    payable = ledger.payable(target)
    if payable is None:
        raise _not_found()
    if amount > payable:
        raise _wrong_amount()
    return target, amount


def _txn(ledger: Ledger, params: dict[str, Any], *, lock: bool = False) -> Any:
    queryset = ledger.txns().filter(
        provider=Provider.PAYME, provider_txn_id=str(params.get("id", ""))
    )
    if lock:
        queryset = queryset.select_for_update()
    txn = queryset.first()
    if txn is None:
        raise _no_txn()
    return txn


def _txn_result(txn: Any) -> dict[str, Any]:
    return {
        "create_time": txn.provider_time or _ms(txn.created_at),
        "perform_time": _ms(txn.performed_at),
        "cancel_time": _ms(txn.cancelled_at),
        "transaction": str(txn.id),
        "state": txn.state,
        "reason": txn.reason,
    }


def _expire(ledger: Ledger, txn: Any) -> None:
    ledger.cancel(txn, reason=4)


# --- Methods ---


def check_perform(ledger: Ledger, params: dict[str, Any]) -> dict[str, Any]:
    _check(ledger, params)
    return {"allow": True}


def create(ledger: Ledger, params: dict[str, Any]) -> dict[str, Any]:
    provider_id = str(params.get("id", ""))
    existing = ledger.txns().filter(provider=Provider.PAYME, provider_txn_id=provider_id).first()
    if existing is not None:
        if existing.state != TxnState.CREATED:
            raise _cannot_perform()
        if _expired(existing):
            _expire(ledger, existing)
            raise _cannot_perform()
        return {
            "create_time": existing.provider_time,
            "transaction": str(existing.id),
            "state": existing.state,
        }

    target, amount = _check(ledger, params)
    pending = ledger.txns().filter(**{ledger.target_field: target}, state=TxnState.CREATED)
    for other in pending:
        if _expired(other):
            _expire(ledger, other)
        else:
            raise _busy()

    try:
        with transaction.atomic():
            txn = ledger.create_txn(
                target,
                provider=Provider.PAYME,
                provider_txn_id=provider_id,
                amount=amount,
                provider_time=int(params.get("time") or 0) or None,
            )
    except IntegrityError:
        # A concurrent retry of the same call won — answer with its row.
        txn = _txn(ledger, params)
    return {"create_time": txn.provider_time, "transaction": str(txn.id), "state": txn.state}


def perform(ledger: Ledger, params: dict[str, Any]) -> dict[str, Any]:
    txn = _txn(ledger, params, lock=True)
    if txn.state == TxnState.CREATED:
        if _expired(txn):
            _expire(ledger, txn)
            raise _cannot_perform()
        ledger.perform(txn)
    elif txn.state != TxnState.PERFORMED:
        raise _cannot_perform()
    return {"transaction": str(txn.id), "perform_time": _ms(txn.performed_at), "state": txn.state}


def cancel(ledger: Ledger, params: dict[str, Any]) -> dict[str, Any]:
    txn = _txn(ledger, params, lock=True)
    reason = params.get("reason")
    try:
        ledger.cancel(txn, reason=int(reason) if reason is not None else None)
    except CannotCancel as exc:
        raise _cannot_cancel() from exc
    return {"transaction": str(txn.id), "cancel_time": _ms(txn.cancelled_at), "state": txn.state}


def check(ledger: Ledger, params: dict[str, Any]) -> dict[str, Any]:
    return _txn_result(_txn(ledger, params))


def statement(ledger: Ledger, params: dict[str, Any]) -> dict[str, Any]:
    start, end = int(params.get("from") or 0), int(params.get("to") or 0)
    rows = (
        ledger.txns()
        .filter(provider=Provider.PAYME, provider_time__gte=start, provider_time__lte=end)
        .order_by("provider_time")
    )
    return {
        "transactions": [
            {
                "id": txn.provider_txn_id,
                "time": txn.provider_time,
                "amount": int(txn.amount * 100),
                "account": {ledger.account_field: ledger.account_of(txn)},
                **_txn_result(txn),
            }
            for txn in rows
        ]
    }


METHODS = {
    "CheckPerformTransaction": check_perform,
    "CreateTransaction": create,
    "PerformTransaction": perform,
    "CancelTransaction": cancel,
    "CheckTransaction": check,
    "GetStatement": statement,
}


@transaction.atomic
def handle(body: dict[str, Any], ledger: Ledger = TUITION) -> dict[str, Any]:
    """One JSON-RPC call (already authorised); returns the response body."""
    request_id = body.get("id")
    method = METHODS.get(str(body.get("method", "")))
    try:
        if method is None:
            raise PaymeError(-32601, "Metod topilmadi", "Метод не найден", "Method not found")
        return {"id": request_id, "result": method(ledger, body.get("params") or {})}
    except PaymeError as error:
        return {
            "id": request_id,
            "error": {"code": error.code, "message": error.message, "data": error.data},
        }


def auth_error(request_id: Any) -> dict[str, Any]:
    error = _auth_failed()
    return {"id": request_id, "error": {"code": error.code, "message": error.message}}
