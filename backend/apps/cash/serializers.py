"""Kassa serializerlari (docs/04 §9.4)."""

from __future__ import annotations

from rest_framework import serializers

from apps.cash.models import CashAccount

__all__ = ["CashAccountSerializer", "CashAdjustSerializer"]


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
