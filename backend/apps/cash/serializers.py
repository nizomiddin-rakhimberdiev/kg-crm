"""Kassa serializerlari (docs/04 §9.4)."""

from __future__ import annotations

from rest_framework import serializers

from apps.cash.models import CashAccount

__all__ = ["CashAccountSerializer"]


class CashAccountSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = CashAccount
        fields = ["id", "name", "kind", "handles_method", "branch", "branch_name", "is_active"]
        read_only_fields = ["id", "branch_name"]
