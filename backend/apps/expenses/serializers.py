"""Chiqim serializerlari (docs/04 §13)."""

from __future__ import annotations

from rest_framework import serializers

from apps.core.fields import TenantPrimaryKeyRelatedField
from apps.expenses.models import Expense, ExpenseCategory

__all__ = ["ExpenseCategorySerializer", "ExpenseSerializer", "ExpenseWriteSerializer"]


class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ["id", "name", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class ExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    approved_by_name = serializers.CharField(
        source="approved_by.full_name", read_only=True, default=None
    )

    class Meta:
        model = Expense
        fields = [
            "id",
            "category",
            "category_name",
            "amount",
            "expense_date",
            "description",
            "status",
            "approved_by_name",
            "decided_at",
            "decision_note",
            "created_at",
        ]
        read_only_fields = fields


class ExpenseWriteSerializer(serializers.ModelSerializer):
    category_id = TenantPrimaryKeyRelatedField(model=ExpenseCategory, source="category")

    class Meta:
        model = Expense
        fields = ["id", "category_id", "amount", "expense_date", "description"]
        read_only_fields = ["id"]
        # `status` mijozdan qabul qilinmaydi: holat faqat tasdiqlash
        # amallari orqali o'zgaradi, aks holda kim xohlasa o'z chiqimini
        # "tasdiqlangan" deb yozib qo'yardi.
