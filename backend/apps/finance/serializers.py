"""Moliya serializerlari (docs/04 §9)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.utils.translation import gettext
from rest_framework import serializers

from apps.children.models import Child
from apps.core.fields import TenantPrimaryKeyRelatedField
from apps.finance.models import (
    Discount,
    Invoice,
    InvoiceLine,
    Payment,
    PaymentMethod,
    TariffPlan,
)

__all__ = [
    "TariffPlanSerializer",
    "DiscountSerializer",
    "InvoiceSerializer",
    "InvoiceLineSerializer",
    "GenerateInvoicesSerializer",
    "LedgerEntrySerializer",
    "PaymentSerializer",
    "PaymentWriteSerializer",
]


class TariffPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = TariffPlan
        fields = ["id", "name", "amount", "billing_period", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class DiscountSerializer(serializers.ModelSerializer):
    child_id = TenantPrimaryKeyRelatedField(model=Child, source="child")
    child_name = serializers.CharField(source="child.full_name", read_only=True)

    class Meta:
        model = Discount
        fields = [
            "id",
            "child_id",
            "child_name",
            "discount_type",
            "value",
            "reason",
            "valid_from",
            "valid_to",
            "is_active",
        ]
        read_only_fields = ["id", "child_name"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs.get("discount_type") == "percent" and attrs.get("value", 0) > 100:
            raise serializers.ValidationError(
                {"value": gettext("Foizli chegirma 100 dan oshmasligi kerak.")}
            )
        return attrs


class InvoiceLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        fields = ["id", "description", "quantity", "unit_amount", "line_total"]
        read_only_fields = fields


class InvoiceSerializer(serializers.ModelSerializer):
    child_name = serializers.CharField(source="child.full_name", read_only=True)
    lines = InvoiceLineSerializer(many=True, read_only=True)
    amount_outstanding = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "number",
            "child",
            "child_name",
            "period_year",
            "period_month",
            "amount_due",
            "amount_paid",
            "amount_outstanding",
            "status",
            "issued_date",
            "due_date",
            "lines",
            "created_at",
        ]
        # Hisob-faktura API orqali TAHRIRLANMAYDI: u ledger yozuvini
        # yaratgan hujjat. O'zgartirish kerak bo'lsa — bekor qilib,
        # yangisini chiqarish (D3).
        read_only_fields = fields


class GenerateInvoicesSerializer(serializers.Serializer):
    period_year = serializers.IntegerField(min_value=2020, max_value=2100)
    period_month = serializers.IntegerField(min_value=1, max_value=12)
    branch_id = serializers.UUIDField(required=False, allow_null=True)


class LedgerEntrySerializer(serializers.Serializer):
    """Ledger faqat o'qish uchun — yozish `post_ledger_entry()` orqali."""

    id = serializers.UUIDField(read_only=True)
    entry_type = serializers.CharField(read_only=True)
    direction = serializers.CharField(read_only=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    source_type = serializers.CharField(read_only=True)
    source_id = serializers.UUIDField(read_only=True, allow_null=True)
    occurred_at = serializers.DateTimeField(read_only=True)
    description = serializers.CharField(read_only=True)


class PaymentSerializer(serializers.ModelSerializer):
    child_name = serializers.CharField(source="child.full_name", read_only=True)
    invoice_number = serializers.CharField(source="invoice.number", read_only=True, default=None)
    is_reversed = serializers.BooleanField(read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "child",
            "child_name",
            "invoice",
            "invoice_number",
            "amount",
            "method",
            "reference",
            "paid_at",
            "batch_id",
            "is_reversed",
            "reversed_at",
            "reversal_reason",
            "created_at",
        ]
        read_only_fields = fields


class PaymentLineSerializer(serializers.Serializer):
    """Bitta to'lov usuli va undan kelgan summa (docs/03 §13.5a)."""

    method = serializers.ChoiceField(choices=PaymentMethod.choices)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    reference = serializers.CharField(required=False, allow_blank=True, max_length=100)


class PaymentBatchSerializer(serializers.Serializer):
    """
    Bitta kassir harakati — bir nechta usul.

    Qatorlar tartibi MUHIM: taqsimlash shu tartibda boradi, ya'ni oxirgi
    qator avansga tushadi (`record_payment_batch`).
    """

    child_id = TenantPrimaryKeyRelatedField(model=Child, source="child")
    invoice_id = TenantPrimaryKeyRelatedField(
        model=Invoice, source="invoice", required=False, allow_null=True
    )
    lines = PaymentLineSerializer(many=True, allow_empty=False)
    paid_at = serializers.DateTimeField(required=False)


class PaymentWriteSerializer(serializers.Serializer):
    """
    To'lov yozish uchun — `ModelSerializer` EMAS.

    `.save()` modelni to'g'ridan-to'g'ri yozib qo'ymasligi kerak: to'lov
    ledger, hisob-faktura va kesh bilan birga, bitta tranzaksiyada
    yoziladi (docs/03 §13.5). Buning yagona yo'li — servis funksiyasi.
    """

    child_id = TenantPrimaryKeyRelatedField(model=Child, source="child")
    invoice_id = TenantPrimaryKeyRelatedField(
        model=Invoice, source="invoice", required=False, allow_null=True
    )
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    method = serializers.ChoiceField(choices=PaymentMethod.choices)
    reference = serializers.CharField(required=False, allow_blank=True, max_length=100)
    paid_at = serializers.DateTimeField(required=False)
