"""Kassa serializerlari (docs/04 §9.4)."""

from __future__ import annotations

from rest_framework import serializers

from apps.cash.models import CashAccount, CashCount, CashHandover
from apps.core.fields import TenantPrimaryKeyRelatedField

__all__ = [
    "CashAccountSerializer",
    "CashAdjustSerializer",
    "CashCountSerializer",
    "CashCountWriteSerializer",
    "CashHandoverSerializer",
    "CashHandoverWriteSerializer",
    "CashTransferSerializer",
]


class CashAccountSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = CashAccount
        fields = ["id", "name", "kind", "handles_method", "branch", "branch_name", "is_active"]
        read_only_fields = ["id", "branch_name"]


class CashAdjustSerializer(serializers.Serializer):
    """
    Qoldiqni qoʻlda toʻgʻrilash (ADR-29).

    `amount` — manfiy ham boʻlishi mumkin (sanoqda kam chiqdi).
    `opening=True` — bogʻcha tizimga kelgan kundagi boshlangʻich
    qoldiq; aks holda oddiy tuzatish. Sabab MAJBURIY: qoldiq
    oʻzgarsa-yu, nega oʻzgargani yozilmasa, keyin uni hech kim
    tushuntira olmaydi.
    """

    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    reason = serializers.CharField(max_length=255)
    opening = serializers.BooleanField(required=False, default=False)
    occurred_on = serializers.DateField(required=False)


class CashTransferSerializer(serializers.Serializer):
    """
    Qoplar orasida o'tkazma — inkassa, bankdan naqd yechish (Bosqich 12.5).

    Tushum ham, xarajat ham emas: biridan chiqadi, ikkinchisiga kiradi.
    """

    from_account_id = TenantPrimaryKeyRelatedField(model=CashAccount, source="source")
    to_account_id = TenantPrimaryKeyRelatedField(model=CashAccount, source="target")
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=1)
    reason = serializers.CharField(max_length=255)
    occurred_on = serializers.DateField(required=False)
    allow_negative = serializers.BooleanField(required=False, default=False)


class CashHandoverSerializer(serializers.ModelSerializer):
    from_user_name = serializers.CharField(source="from_user.full_name", read_only=True)
    to_user_name = serializers.CharField(source="to_user.full_name", read_only=True)

    class Meta:
        model = CashHandover
        fields = [
            "id",
            "cash_account",
            "from_user",
            "from_user_name",
            "to_user",
            "to_user_name",
            "amount",
            "note",
            "status",
            "decided_at",
            "decision_note",
            "created_at",
        ]
        read_only_fields = fields


class CashHandoverWriteSerializer(serializers.Serializer):
    to_user_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=1)
    note = serializers.CharField(max_length=255, required=False, allow_blank=True)


class CashCountSerializer(serializers.ModelSerializer):
    cash_account_name = serializers.CharField(source="cash_account.name", read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=None
    )

    class Meta:
        model = CashCount
        fields = [
            "id",
            "cash_account",
            "cash_account_name",
            "counted_on",
            "system_balance",
            "counted",
            "difference",
            "reason",
            "created_by_name",
            "created_at",
        ]
        read_only_fields = fields


class CashCountWriteSerializer(serializers.Serializer):
    cash_account_id = TenantPrimaryKeyRelatedField(model=CashAccount, source="cash_account")
    counted = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0)
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)
