"""Chiqim serializerlari (docs/04 §13)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.utils.translation import gettext
from rest_framework import serializers

from apps.cash.models import CashAccount
from apps.core.fields import TenantPrimaryKeyRelatedField
from apps.expenses.models import Expense, ExpenseCategory, ExpenseItem

__all__ = ["ExpenseCategorySerializer", "ExpenseSerializer", "ExpenseWriteSerializer"]


class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ["id", "name", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class ExpenseItemSerializer(serializers.ModelSerializer):
    """Chiqim qatori (PLAN 7.5) — o'qishda."""

    class Meta:
        model = ExpenseItem
        fields = ["id", "name", "quantity", "unit", "unit_price", "line_total", "note"]


class ExpenseItemInputSerializer(serializers.Serializer):
    """Yozishda: `line_total` MIJOZDAN olinmaydi — server hisoblaydi."""

    name = serializers.CharField(max_length=120)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.001"))
    unit = serializers.CharField(max_length=10, required=False, allow_blank=True)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))
    note = serializers.CharField(max_length=255, required=False, allow_blank=True)


class ExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    approved_by_name = serializers.CharField(
        source="approved_by.full_name", read_only=True, default=None
    )
    # Qaysi qopdan to'landi (ADR-17) — `NULL` hali to'lanmagani.
    cash_account_name = serializers.CharField(
        source="cash_account.name", read_only=True, default=None
    )
    items = ExpenseItemSerializer(many=True, read_only=True)

    class Meta:
        model = Expense
        fields = [
            "id",
            "category",
            "category_name",
            "amount",
            "expense_date",
            "description",
            "items",
            "status",
            "approved_by_name",
            "decided_at",
            "decision_note",
            "cash_account",
            "cash_account_name",
            "created_at",
        ]
        read_only_fields = fields


class ExpenseWriteSerializer(serializers.ModelSerializer):
    category_id = TenantPrimaryKeyRelatedField(model=ExpenseCategory, source="category")
    # Qaysi puldan to'lanadi — kiritish paytidayoq (ADR-17). Ixtiyoriy:
    # so'rovni yozgan odam buni bilmasligi mumkin, tasdiqlovchi biladi.
    cash_account_id = TenantPrimaryKeyRelatedField(
        model=CashAccount, source="cash_account", required=False, allow_null=True
    )
    # Qatorlar (PLAN 7.5). Berilsa — summa ULARDAN hisoblanadi va
    # `amount` mijozdan olinmaydi; berilmasa eski yo'l ishlaydi
    # (bitta summa), chunki eski chiqimlar va importlar shunday.
    items = ExpenseItemInputSerializer(many=True, required=False)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)

    class Meta:
        model = Expense
        fields = [
            "id",
            "category_id",
            "amount",
            "expense_date",
            "description",
            "cash_account_id",
            "items",
        ]
        read_only_fields = ["id"]
        # `status` mijozdan qabul qilinmaydi: holat faqat tasdiqlash
        # amallari orqali o'zgaradi, aks holda kim xohlasa o'z chiqimini
        # "tasdiqlangan" deb yozib qo'yardi.

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Summa yoki qatorlar — bittasi bo'lishi SHART.

        Ikkalasi ham kelsa, qatorlar ustun: ekranda ko'rsatilgan
        yig'indi bilan kassadan chiqqan pul ajralib qolmasligi kerak.
        """
        if not attrs.get("items") and attrs.get("amount") is None:
            raise serializers.ValidationError(
                {"amount": gettext("Summa yoki chiqim qatorlari kiritilishi kerak.")}
            )
        return attrs
