"""Obuna serializerlari (docs/04 §18)."""

from __future__ import annotations

from rest_framework import serializers

from apps.subscriptions.models import (
    PaymentTerm,
    Subscription,
    SubscriptionInvoice,
    UsageSnapshot,
)

__all__ = [
    "SubscriptionSerializer",
    "UsageSnapshotSerializer",
    "SubscriptionInvoiceSerializer",
    "AcceptTrialSerializer",
    "PaymentTermSerializer",
]


class SubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    plan_code = serializers.CharField(source="plan.code", read_only=True)
    base_price = serializers.DecimalField(
        source="plan.base_price", max_digits=12, decimal_places=2, read_only=True
    )
    included_children = serializers.IntegerField(source="plan.included_children", read_only=True)
    overage_step_children = serializers.IntegerField(
        source="plan.overage_step_children", read_only=True
    )
    overage_step_price = serializers.DecimalField(
        source="plan.overage_step_price", max_digits=12, decimal_places=2, read_only=True
    )
    is_read_only = serializers.BooleanField(read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id",
            "status",
            "payment_term",
            "discount_percent",
            "plan_code",
            "plan_name",
            "base_price",
            "included_children",
            "overage_step_children",
            "overage_step_price",
            "trial_started_at",
            "trial_ends_at",
            "current_period_start",
            "current_period_end",
            "committed_children",
            "is_read_only",
            "created_at",
        ]
        read_only_fields = fields


class UsageSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsageSnapshot
        fields = [
            "id",
            "period_year",
            "period_month",
            "peak_children",
            "peak_observed_at",
            "billable_children",
            "measurement_method",
            "note",
            "closed_at",
            "created_at",
        ]
        # Dalil o'zgartirilmaydi (P11). Tuzatish — yangi qator.
        read_only_fields = fields


class SubscriptionInvoiceSerializer(serializers.ModelSerializer):
    amount_paid = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionInvoice
        fields = [
            "id",
            "number",
            "status",
            "issued_at",
            "due_at",
            "period_start",
            "period_end",
            "billable_children",
            "base_amount",
            "overage_amount",
            "discount_amount",
            "total_amount",
            "amount_paid",
            "currency",
            "usage_snapshot",
            "created_at",
        ]
        read_only_fields = fields

    def get_amount_paid(self, obj: SubscriptionInvoice) -> str:
        total = sum((payment.amount for payment in obj.payments.all()), start=0)
        return f"{total:.2f}"


class AcceptTrialSerializer(serializers.Serializer):
    payment_term = serializers.ChoiceField(choices=PaymentTerm.choices, default=PaymentTerm.MONTHLY)
    committed_children = serializers.IntegerField(required=False, min_value=0)


class PaymentTermSerializer(serializers.Serializer):
    payment_term = serializers.ChoiceField(choices=PaymentTerm.choices)
