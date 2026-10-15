"""
Provider-independent logic for online payments (PLAN 6.1, ADR-26).

`payme.py` and `click.py` only translate their protocols; every decision
about money is made here, once:

* which invoices can be paid online and for how much (`payable_amount`);
* `perform()` — records the money through `finance.record_payment`, so the
  payment, the cash movement ("Payme / Click" pot, ADR-17), the ledger
  credit and the allocation (ADR-20) happen in ONE transaction, exactly as
  for a cashier;
* `cancel()` — before the money was recorded it is a state change; after,
  it is `finance.reverse_payment` (a counter-entry, invariant 3).

The provider's transaction id doubles as `Payment.idempotency_key`, so a
retried webhook can never record the money twice — the database refuses
the second row (`uq_payment_idempotency`).

**Tenant context.** Webhooks and the public link page arrive without a
tenant. The organization is taken from the URL (webhooks) or from the
link token itself (`build_token`), and all work happens inside
`organization_context` — RLS is not widened (the ADR-23 approach).
"""

from __future__ import annotations

import base64
import binascii
import secrets
import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.finance.models import Invoice, InvoiceStatus, PaymentMethod
from apps.online_payments import crypto
from apps.online_payments.merchant import Merchant, checkout_url
from apps.online_payments.models import (
    MerchantCredential,
    OnlineTransaction,
    PaymentLink,
    TxnState,
)

__all__ = [
    "LINK_TTL",
    "build_token",
    "organization_from_token",
    "create_link",
    "active_credentials",
    "secret_for",
    "save_credential",
    "payable_amount",
    "merchant_for",
    "checkout_urls",
    "public_url",
    "public_return_url",
    "perform",
    "cancel",
]

#: How long a payment link stays usable. A month covers the billing cycle.
LINK_TTL = timedelta(days=30)

_RANDOM_BYTES = 24


# --- Link tokens ---


def build_token(organization_id: Any) -> str:
    """`base64url(org uuid + 24 random bytes)` — the organization travels with the link."""
    raw = uuid.UUID(str(organization_id)).bytes + secrets.token_bytes(_RANDOM_BYTES)
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def organization_from_token(token: str) -> uuid.UUID | None:
    try:
        raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
    except (binascii.Error, ValueError):
        return None
    if len(raw) != 16 + _RANDOM_BYTES:
        return None
    return uuid.UUID(bytes=raw[:16])


@transaction.atomic
def create_link(*, invoice: Invoice, created_by: Any = None) -> PaymentLink:
    """
    A shareable link for one invoice. An unexpired link is reused.

    Reuse matters: the "send to parent" button may be pressed twice, and two
    live links for one invoice would look like two bills to a parent.
    """
    now = timezone.now()
    existing = (
        PaymentLink.objects.filter(invoice=invoice, expires_at__gt=now, is_active=True)
        .order_by("-created_at")
        .first()
    )
    if existing is not None:
        return existing
    return PaymentLink.objects.create(
        organization_id=invoice.organization_id,
        branch_id=invoice.branch_id,
        invoice=invoice,
        token=build_token(invoice.organization_id),
        expires_at=now + LINK_TTL,
        created_by=created_by,
    )


# --- Merchant credentials ---


def active_credentials() -> dict[str, MerchantCredential]:
    """The current tenant's configured providers."""
    return {
        credential.provider: credential
        for credential in MerchantCredential.objects.filter(is_active=True)
    }


def secret_for(credential: MerchantCredential) -> str:
    return crypto.decrypt(credential.secret_encrypted)


@transaction.atomic
def save_credential(
    *,
    organization: Any,
    provider: str,
    merchant_id: str,
    secret: str,
    service_id: str = "",
    sandbox: bool = False,
) -> MerchantCredential:
    """Replaces the provider's key: the old row is deactivated, never edited in place."""
    MerchantCredential.objects.filter(provider=provider, is_active=True).update(is_active=False)
    return MerchantCredential.objects.create(
        organization=organization,
        provider=provider,
        merchant_id=merchant_id.strip(),
        service_id=service_id.strip(),
        secret_encrypted=crypto.encrypt(secret.strip()),
        secret_hint=secret.strip()[-4:],
        sandbox=sandbox,
    )


# --- What can be paid ---


def payable_amount(invoice: Invoice) -> Decimal | None:
    """
    How much of this invoice can be paid online; `None` — not payable.

    Not payable: a cancelled invoice, an archived child, or nothing left to
    pay. The last one is deliberate: a parent re-opening an old link must
    not pay a settled bill twice — an advance is the cashier's decision.
    """
    if invoice.status == InvoiceStatus.CANCELLED:
        return None
    if invoice.child.archived_at is not None:
        return None
    outstanding = invoice.amount_due - invoice.amount_paid
    return outstanding if outstanding > 0 else None


def merchant_for(credential: MerchantCredential) -> Merchant:
    """A stored credential as the protocol layer's `Merchant` (secret decrypted)."""
    return Merchant(
        provider=credential.provider,
        merchant_id=credential.merchant_id,
        secret=secret_for(credential),
        service_id=credential.service_id,
        sandbox=credential.sandbox,
    )


def checkout_urls(*, invoice: Invoice, amount: Decimal, return_url: str) -> dict[str, str]:
    """
    Provider checkout pages for this invoice — a REDIRECT, no script of
    theirs on our page, so the CSP stays as it is.
    """
    return {
        provider: checkout_url(
            Merchant(
                provider=provider,
                merchant_id=credential.merchant_id,
                secret="",  # not needed to build a URL — never decrypted here
                service_id=credential.service_id,
                sandbox=credential.sandbox,
            ),
            account=str(invoice.id),
            amount=amount,
            return_url=return_url,
        )
        for provider, credential in active_credentials().items()
    }


def public_url(link: PaymentLink) -> str:
    """The parent's page for this link (`/pay/<token>`)."""
    base = str(getattr(settings, "FRONTEND_URL", "")).rstrip("/")
    return f"{base}/pay/{link.token}"


def public_return_url(link: PaymentLink) -> str:
    base = str(getattr(settings, "FRONTEND_URL", "")).rstrip("/")
    return f"{base}/pay/{link.token}?done=1"


# --- State machine ---


def perform(txn: OnlineTransaction) -> OnlineTransaction:
    """
    Records the money — once. Call with `txn` locked (`select_for_update`).

    `record_payment` does everything a cashier's payment does, in the same
    transaction: payment row, cash movement into the "Payme / Click" pot,
    ledger credit, allocation starting with THIS invoice, receipt message.
    """
    from apps.finance.services import record_payment

    if txn.state == TxnState.PERFORMED:
        return txn
    payment = record_payment(
        child=txn.invoice.child,
        amount=txn.amount,
        # Click va Payme alohida usul (Bosqich 12.4): hisobot va
        # komissiya ularni ajratadi.
        method=PaymentMethod.PAYME if txn.provider == "payme" else PaymentMethod.CLICK,
        invoice=txn.invoice,
        # Ota-ona havolada AYNAN shu hujjatni to'ladi — bu tanlovning
        # sababi, kassir tanlovi emas.
        allocation_reason="Ota-ona havola orqali shu hisob-fakturani toʻladi",
        reference=f"{txn.provider}:{txn.provider_txn_id}"[:100],
        idempotency_key=f"{txn.provider}:{txn.provider_txn_id}"[:64],
    )
    txn.payment = payment
    txn.state = TxnState.PERFORMED
    txn.performed_at = timezone.now()
    txn.save(update_fields=["payment", "state", "performed_at", "updated_at"])
    return txn


def cancel(txn: OnlineTransaction, *, reason: int | None) -> OnlineTransaction:
    """
    Cancels. After the money was recorded this is a REVERSAL — a
    counter-entry in the ledger and the cash journal, never a delete.
    """
    from apps.finance.services import reverse_payment

    if txn.state < 0:
        return txn
    if txn.state == TxnState.PERFORMED and txn.payment is not None:
        reverse_payment(payment=txn.payment, reason=f"{txn.provider}: bekor qilindi ({reason})")
        txn.state = TxnState.CANCELLED_AFTER_PERFORM
    else:
        txn.state = TxnState.CANCELLED
    txn.reason = reason
    txn.cancelled_at = timezone.now()
    txn.save(update_fields=["state", "reason", "cancelled_at", "updated_at"])
    return txn
