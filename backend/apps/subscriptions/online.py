"""
Paying Radix's subscription invoice online (PLAN 6.4, decision P6-3).

The money goes to RADIX here, so the merchant is Radix's own — keys in
`.env` (`RADIX_PAYME_*`, `RADIX_CLICK_*`), never in the database. Empty
keys simply hide the button: bank transfer (D8) stays the way to pay.

The protocol code is the tuition one (`online_payments.payme` / `.click`);
only the ledger differs:

* the account is the invoice NUMBER (global, unique) — Radix's merchant has
  one callback URL for every customer, so the tenant comes from the number,
  looked up in the metadata plane (`subscription_invoice`, ADR-10);
* performing records an ordinary `record_subscription_payment`, which also
  moves `suspended` → `active` (invariant 11 — paying must always work);
* a cancellation after payment is refused (Payme `-31007`): a subscription
  payment is append-only and a refund is a decision for a person, not for a
  callback.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.conf import settings
from django.utils import timezone

from apps.online_payments.merchant import CannotCancel, Merchant, checkout_url
from apps.subscriptions.models import (
    SubscriptionInvoice,
    SubscriptionInvoiceStatus,
    SubscriptionOnlineTransaction,
    SubscriptionPayment,
    SubscriptionPaymentMethod,
)

__all__ = ["SubscriptionLedger", "SUBSCRIPTION", "radix_merchant", "checkout_links"]

CREATED, PERFORMED, CANCELLED = 1, 2, -1


def radix_merchant(provider: str) -> Merchant | None:
    """Radix's own merchant for `provider`, or `None` when not configured."""
    if provider == "payme":
        merchant_id = str(getattr(settings, "RADIX_PAYME_MERCHANT_ID", "") or "")
        secret = str(getattr(settings, "RADIX_PAYME_KEY", "") or "")
        if not (merchant_id and secret):
            return None
        return Merchant(
            provider="payme",
            merchant_id=merchant_id,
            secret=secret,
            sandbox=bool(getattr(settings, "RADIX_PAYME_SANDBOX", False)),
        )
    if provider == "click":
        merchant_id = str(getattr(settings, "RADIX_CLICK_MERCHANT_ID", "") or "")
        service_id = str(getattr(settings, "RADIX_CLICK_SERVICE_ID", "") or "")
        secret = str(getattr(settings, "RADIX_CLICK_SECRET", "") or "")
        if not (merchant_id and service_id and secret):
            return None
        return Merchant(
            provider="click", merchant_id=merchant_id, secret=secret, service_id=service_id
        )
    return None


def outstanding(invoice: SubscriptionInvoice) -> Decimal | None:
    if invoice.status not in (SubscriptionInvoiceStatus.ISSUED, SubscriptionInvoiceStatus.OVERDUE):
        return None
    # `all_objects`: this runs in the platform plane, where the tenant
    # manager would refuse (there is no single organization).
    paid = sum(
        (p.amount for p in SubscriptionPayment.all_objects.filter(subscription_invoice=invoice)),
        Decimal("0"),
    )
    left = invoice.total_amount - paid
    return left if left > 0 else None


def checkout_links(invoice: SubscriptionInvoice, *, return_url: str) -> dict[str, str]:
    """Provider pages for one open invoice; `{}` when nothing is payable or nothing set up."""
    amount = outstanding(invoice)
    if amount is None:
        return {}
    links: dict[str, str] = {}
    for provider in ("payme", "click"):
        merchant = radix_merchant(provider)
        if merchant is not None:
            links[provider] = checkout_url(
                merchant, account=invoice.number, amount=amount, return_url=return_url
            )
    return links


class SubscriptionLedger:
    """Runs inside `platform_context()` — subscription tables are metadata."""

    account_field = "invoice"
    target_field = "subscription_invoice"

    def txns(self) -> Any:
        return SubscriptionOnlineTransaction.all_objects.all()

    def find(self, account: str) -> SubscriptionInvoice | None:
        return (
            SubscriptionInvoice.all_objects.select_related("subscription")
            .filter(number=str(account))
            .first()
        )

    def payable(self, target: SubscriptionInvoice) -> Decimal | None:
        return outstanding(target)

    def is_settled(self, target: SubscriptionInvoice) -> bool:
        return target.status == SubscriptionInvoiceStatus.PAID

    def create_txn(self, target: SubscriptionInvoice, **fields: Any) -> Any:
        return SubscriptionOnlineTransaction.all_objects.create(
            organization_id=target.organization_id, subscription_invoice=target, **fields
        )

    def account_of(self, txn: SubscriptionOnlineTransaction) -> str:
        return str(txn.subscription_invoice.number)

    def perform(self, txn: SubscriptionOnlineTransaction) -> SubscriptionOnlineTransaction:
        from apps.core.tenancy import organization_context
        from apps.subscriptions.services import record_subscription_payment

        if txn.state == PERFORMED:
            return txn
        # Written in the customer's own context — exactly as the platform
        # console records a bank transfer.
        with organization_context(txn.organization_id):
            payment = record_subscription_payment(
                invoice=txn.subscription_invoice,
                amount=txn.amount,
                method=SubscriptionPaymentMethod.ONLINE,
                reference=f"{txn.provider}:{txn.provider_txn_id}"[:80],
            )
        txn.payment = payment
        txn.state = PERFORMED
        txn.performed_at = timezone.now()
        txn.save(update_fields=["payment", "state", "performed_at", "updated_at"])
        return txn

    def cancel(
        self, txn: SubscriptionOnlineTransaction, *, reason: int | None
    ) -> SubscriptionOnlineTransaction:
        if txn.state == PERFORMED:
            raise CannotCancel
        if txn.state < 0:
            return txn
        txn.state = CANCELLED
        txn.reason = reason
        txn.cancelled_at = timezone.now()
        txn.save(update_fields=["state", "reason", "cancelled_at", "updated_at"])
        return txn


SUBSCRIPTION = SubscriptionLedger()
