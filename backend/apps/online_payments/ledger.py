"""
Tuition ledger — a kindergarten's invoice paid into its own merchant
(PLAN 6.1, ADR-26). Runs inside the kindergarten's organization context:
another kindergarten's invoice is simply not found (RLS).
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from apps.finance.models import Invoice
from apps.online_payments import services
from apps.online_payments.models import OnlineTransaction

__all__ = ["TuitionLedger", "TUITION"]


class TuitionLedger:
    account_field = "invoice"
    target_field = "invoice"

    def txns(self) -> Any:
        return OnlineTransaction.objects.all()

    def find(self, account: str) -> Invoice | None:
        try:
            invoice_id = uuid.UUID(str(account))
        except ValueError:
            return None
        return Invoice.objects.select_related("child").filter(pk=invoice_id).first()

    def payable(self, target: Invoice) -> Decimal | None:
        return services.payable_amount(target)

    def is_settled(self, target: Invoice) -> bool:
        return target.amount_paid >= target.amount_due

    def create_txn(self, target: Invoice, **fields: Any) -> OnlineTransaction:
        return OnlineTransaction.objects.create(
            organization_id=target.organization_id,
            branch_id=target.branch_id,
            invoice=target,
            **fields,
        )

    def account_of(self, txn: OnlineTransaction) -> str:
        return str(txn.invoice_id)

    def perform(self, txn: OnlineTransaction) -> OnlineTransaction:
        return services.perform(txn)

    def cancel(self, txn: OnlineTransaction, *, reason: int | None) -> OnlineTransaction:
        return services.cancel(txn, reason=reason)


TUITION = TuitionLedger()
