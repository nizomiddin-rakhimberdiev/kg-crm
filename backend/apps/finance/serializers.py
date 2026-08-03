"""Moliya serializerlari (docs/04 §9)."""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.children.models import Child
from apps.core.fields import TenantPrimaryKeyRelatedField
from apps.finance.models import Discount, Invoice, InvoiceLine, TariffPlan

__all__ = [
    "TariffPlanSerializer",
    "DiscountSerializer",
    "InvoiceSerializer",
    "InvoiceLineSerializer",
    "GenerateInvoicesSerializer",
    "LedgerEntrySerializer",
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
                {"value": "Foizli chegirma 100 dan oshmasligi kerak."}
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
