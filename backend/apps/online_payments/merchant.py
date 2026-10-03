"""
The provider protocols' two seams (PLAN 6.1 / 6.4).

`payme.py` and `click.py` speak the providers' protocols once. What they
settle differs:

* **tuition** — a kindergarten's invoice, paid into the kindergarten's own
  merchant (ADR-26), recorded as a `finance` payment;
* **subscription** — Radix's invoice to a kindergarten, paid into Radix's
  merchant (`.env`), recorded as a `subscriptions` payment (invariant 9:
  the two domains never share tables).

So a protocol call gets a `Merchant` (whose keys) and a `Ledger` (what is
being paid and how money is written). One copy of the protocol, two
ledgers — two copies would drift the way the two balance formulas once
did (ADR-20).
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol
from urllib.parse import urlencode

__all__ = ["Merchant", "Ledger", "CannotCancel", "checkout_url"]


@dataclass(frozen=True)
class Merchant:
    provider: str
    merchant_id: str
    secret: str
    service_id: str = ""
    sandbox: bool = False


class CannotCancel(Exception):
    """The ledger refuses a cancellation after payment (Payme `-31007`)."""


class Ledger(Protocol):
    """What a protocol needs to know about the thing being paid."""

    #: Payme `account` key and the name of the txn's FK to the target.
    account_field: str
    target_field: str

    def txns(self) -> Any:
        """Queryset of the transaction model in this ledger's context."""
        ...

    def find(self, account: str) -> Any | None: ...

    def payable(self, target: Any) -> Decimal | None: ...

    def is_settled(self, target: Any) -> bool: ...

    def create_txn(self, target: Any, **fields: Any) -> Any: ...

    def account_of(self, txn: Any) -> str: ...

    def perform(self, txn: Any) -> Any: ...

    def cancel(self, txn: Any, *, reason: int | None) -> Any: ...


def checkout_url(merchant: Merchant, *, account: str, amount: Decimal, return_url: str) -> str:
    """The provider's checkout page — a redirect; no script of theirs on our page."""
    if merchant.provider == "payme":
        tiyin = int((amount * 100).to_integral_value())
        params = f"m={merchant.merchant_id};ac.invoice={account};a={tiyin};c={return_url}"
        host = (
            "https://checkout.test.paycom.uz" if merchant.sandbox else "https://checkout.paycom.uz"
        )
        return f"{host}/{base64.b64encode(params.encode()).decode()}"
    query = urlencode(
        {
            "service_id": merchant.service_id,
            "merchant_id": merchant.merchant_id,
            "amount": f"{amount:.2f}",
            "transaction_param": account,
            "return_url": return_url,
        }
    )
    return f"https://my.click.uz/services/pay?{query}"
