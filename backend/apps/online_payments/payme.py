"""
Payme Merchant API (JSON-RPC 2.0) — PLAN 6.1.

Payme calls our endpoint with one of six methods. Everything is HTTP 200;
errors travel in the JSON-RPC `error` object with Payme's own codes, and
Payme shows `message` to the payer — hence three languages.

Amounts arrive in TIYIN (integer); they become so'm as `Decimal(amount) / 100`
— never a float (brief, rule 4). Times are milliseconds since the epoch.

Authentication: `Authorization: Basic base64("Paycom:" + key)`, compared in
constant time with the kindergarten's own key. A wrong key is answered
before anything else is looked at (`-32504`).
"""

from __future__ import annotations

import base64
import hmac
import uuid
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import IntegrityError, transaction

from apps.finance.models import Invoice
from apps.online_payments import services
from apps.online_payments.models import MerchantCredential, OnlineTransaction, Provider, TxnState

__all__ = ["PaymeError", "authorised", "handle"]

ACCOUNT_FIELD = "invoice"


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


def authorised(header: str, credential: MerchantCredential) -> bool:
    if not header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(header[6:]).decode()
    except (ValueError, UnicodeDecodeError):
        return False
    login, _, key = decoded.partition(":")
    expected = services.secret_for(credential)
    return login == "Paycom" and hmac.compare_digest(key.encode(), expected.encode())


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


def _invoice(params: dict[str, Any]) -> Invoice:
    raw = str((params.get("account") or {}).get(ACCOUNT_FIELD, ""))
    try:
        invoice_id = uuid.UUID(raw)
    except ValueError as exc:
        raise _not_found() from exc
    # Tenant context is already set: another kindergarten's invoice is
    # simply not there (RLS) — "not found", never "forbidden".
    invoice = Invoice.objects.select_related("child").filter(pk=invoice_id).first()
    if invoice is None:
        raise _not_found()
    return invoice


def _check(params: dict[str, Any]) -> tuple[Invoice, Decimal]:
    invoice = _invoice(params)
    amount = _amount(params)
    payable = services.payable_amount(invoice)
    if payable is None:
        raise _not_found()
    if amount > payable:
        raise _wrong_amount()
    return invoice, amount


def _txn(params: dict[str, Any], *, lock: bool = False) -> OnlineTransaction:
    queryset = OnlineTransaction.objects.filter(
        provider=Provider.PAYME, provider_txn_id=str(params.get("id", ""))
    )
    if lock:
        queryset = queryset.select_for_update()
    txn = queryset.first()
    if txn is None:
        raise _no_txn()
    return txn


def _txn_result(txn: OnlineTransaction) -> dict[str, Any]:
    return {
        "create_time": txn.provider_time or _ms(txn.created_at),
        "perform_time": _ms(txn.performed_at),
        "cancel_time": _ms(txn.cancelled_at),
        "transaction": str(txn.id),
        "state": txn.state,
        "reason": txn.reason,
    }


# --- Methods ---


def check_perform(params: dict[str, Any]) -> dict[str, Any]:
    _check(params)
    return {"allow": True}


def create(params: dict[str, Any]) -> dict[str, Any]:
    provider_id = str(params.get("id", ""))
    existing = OnlineTransaction.objects.filter(
        provider=Provider.PAYME, provider_txn_id=provider_id
    ).first()
    if existing is not None:
        if existing.state != TxnState.CREATED:
            raise _cannot_perform()
        if services.is_expired(existing):
            services.cancel(existing, reason=4)
            raise _cannot_perform()
        return {
            "create_time": existing.provider_time,
            "transaction": str(existing.id),
            "state": existing.state,
        }

    invoice, amount = _check(params)
    pending = OnlineTransaction.objects.filter(invoice=invoice, state=TxnState.CREATED)
    for other in pending:
        if services.is_expired(other):
            services.cancel(other, reason=4)
        else:
            raise _busy()

    try:
        with transaction.atomic():
            txn = OnlineTransaction.objects.create(
                organization_id=invoice.organization_id,
                branch_id=invoice.branch_id,
                provider=Provider.PAYME,
                provider_txn_id=provider_id,
                invoice=invoice,
                amount=amount,
                provider_time=int(params.get("time") or 0) or None,
            )
    except IntegrityError:
        # A concurrent retry of the same call won — answer with its row.
        txn = _txn(params)
    return {"create_time": txn.provider_time, "transaction": str(txn.id), "state": txn.state}


def perform(params: dict[str, Any]) -> dict[str, Any]:
    txn = _txn(params, lock=True)
    if txn.state == TxnState.CREATED:
        if services.is_expired(txn):
            services.cancel(txn, reason=4)
            raise _cannot_perform()
        services.perform(txn)
    elif txn.state != TxnState.PERFORMED:
        raise _cannot_perform()
    return {"transaction": str(txn.id), "perform_time": _ms(txn.performed_at), "state": txn.state}


def cancel(params: dict[str, Any]) -> dict[str, Any]:
    txn = _txn(params, lock=True)
    reason = params.get("reason")
    services.cancel(txn, reason=int(reason) if reason is not None else None)
    return {"transaction": str(txn.id), "cancel_time": _ms(txn.cancelled_at), "state": txn.state}


def check(params: dict[str, Any]) -> dict[str, Any]:
    return _txn_result(_txn(params))


def statement(params: dict[str, Any]) -> dict[str, Any]:
    start, end = int(params.get("from") or 0), int(params.get("to") or 0)
    rows = OnlineTransaction.objects.filter(
        provider=Provider.PAYME, provider_time__gte=start, provider_time__lte=end
    ).order_by("provider_time")
    return {
        "transactions": [
            {
                "id": txn.provider_txn_id,
                "time": txn.provider_time,
                "amount": int(txn.amount * 100),
                "account": {ACCOUNT_FIELD: str(txn.invoice_id)},
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
def handle(body: dict[str, Any]) -> dict[str, Any]:
    """One JSON-RPC call inside the tenant context; returns the response body."""
    request_id = body.get("id")
    method = METHODS.get(str(body.get("method", "")))
    try:
        if method is None:
            raise PaymeError(-32601, "Metod topilmadi", "Метод не найден", "Method not found")
        return {"id": request_id, "result": method(body.get("params") or {})}
    except PaymeError as error:
        return {
            "id": request_id,
            "error": {"code": error.code, "message": error.message, "data": error.data},
        }


def auth_error(request_id: Any) -> dict[str, Any]:
    error = _auth_failed()
    return {"id": request_id, "error": {"code": error.code, "message": error.message}}
