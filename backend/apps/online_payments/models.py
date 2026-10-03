"""
Online payments by parents — Payme and Click (PLAN 6.1, ADR-26).

The money goes to the KINDERGARTEN's own merchant account: Radix never
holds customer money. These tables only record the conversation with the
provider. The money itself is recorded where all money is — `Payment`,
`cash_movement` and the child ledger — by `finance.record_payment`, inside
the same transaction that moves a transaction to "performed".

Three tables, all tenant-scoped with RLS (invariants 2 and 8):

* `merchant_credential` — the kindergarten's Payme / Click keys, the
  secret ENCRYPTED at rest (`crypto.py`);
* `payment_link` — a shareable "pay this invoice" link for parents;
* `online_transaction` — one provider transaction and its state machine.
  The state is updated, the money is not: money lives in the append-only
  ledgers and a cancellation is a reversal there (invariant 3).
"""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy

from apps.core.models import BranchScopedModel, TenantScopedModel

__all__ = [
    "Provider",
    "TxnState",
    "MerchantCredential",
    "PaymentLink",
    "OnlineTransaction",
]


class Provider(models.TextChoices):
    PAYME = "payme", "Payme"
    CLICK = "click", "Click"


class TxnState(models.IntegerChoices):
    """
    Payme's numeric states, reused for Click so both share one machine.

    Negative = cancelled; -2 means "cancelled after the money was
    recorded", i.e. the payment was reversed.
    """

    CREATED = 1, gettext_lazy("Yaratildi")
    PERFORMED = 2, gettext_lazy("Toʻlandi")
    CANCELLED = -1, gettext_lazy("Bekor qilindi")
    CANCELLED_AFTER_PERFORM = -2, gettext_lazy("Qaytarildi")


class MerchantCredential(TenantScopedModel):
    """The kindergarten's own merchant account at a provider."""

    provider = models.CharField(max_length=10, choices=Provider.choices)
    #: Payme: merchant (cash desk) id. Click: merchant id.
    merchant_id = models.CharField(max_length=64)
    #: Click only: service id. Empty for Payme.
    service_id = models.CharField(max_length=32, blank=True)
    #: Fernet token of the secret key — never the key itself.
    secret_encrypted = models.TextField(editable=False)
    #: Last four characters, so the settings screen can say WHICH key is set.
    secret_hint = models.CharField(max_length=4, blank=True, editable=False)
    #: Payme's test checkout (checkout.test.paycom.uz) for a dry run.
    sandbox = models.BooleanField(default=False)

    class Meta:
        db_table = "merchant_credential"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "provider"],
                condition=models.Q(is_active=True),
                name="uq_merchant_credential_active",
            )
        ]

    def __str__(self) -> str:
        return f"{self.provider}:{self.merchant_id}"


class PaymentLink(BranchScopedModel):
    """A "pay this invoice" link a parent opens (`/pay/<token>`)."""

    invoice = models.ForeignKey(
        "finance.Invoice", on_delete=models.RESTRICT, related_name="payment_links"
    )
    #: base64url(organization uuid + 24 random bytes) — see `services.build_token`.
    token = models.CharField(max_length=64, unique=True, editable=False)
    expires_at = models.DateTimeField()
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        db_table = "payment_link"
        ordering = ["-created_at"]


class OnlineTransaction(BranchScopedModel):
    """One provider transaction. `UNIQUE(provider, provider_txn_id)` makes retries harmless."""

    provider = models.CharField(max_length=10, choices=Provider.choices)
    provider_txn_id = models.CharField(max_length=64)
    invoice = models.ForeignKey(
        "finance.Invoice", on_delete=models.RESTRICT, related_name="online_transactions"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    state = models.SmallIntegerField(choices=TxnState.choices, default=TxnState.CREATED)
    reason = models.SmallIntegerField(null=True, blank=True)
    payment = models.ForeignKey(
        "finance.Payment",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="online_transactions",
    )
    #: Provider's own timestamp (Payme: ms since epoch).
    provider_time = models.BigIntegerField(null=True, blank=True)
    performed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "online_transaction"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_txn_id"], name="uq_online_txn_provider_id"
            ),
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="ck_online_txn_amount"),
        ]

    def __str__(self) -> str:
        return f"{self.provider}:{self.provider_txn_id} ({self.state})"
