"""Ombor serializerlari (docs/04 §12)."""

from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from apps.cash.models import CashAccount
from apps.core.fields import TenantPrimaryKeyRelatedField
from apps.expenses.models import ExpenseCategory
from apps.inventory.models import (
    MovementDirection,
    MovementType,
    Product,
    ProductCategory,
    StockMovement,
    Supplier,
    Warehouse,
)

__all__ = [
    "WarehouseSerializer",
    "ProductCategorySerializer",
    "ProductSerializer",
    "SupplierSerializer",
    "StockMovementSerializer",
    "MovementWriteSerializer",
]


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ["id", "name", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ["id", "name", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ["id", "name", "phone", "contact_person", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    is_low_stock = serializers.BooleanField(read_only=True)
    category_id = TenantPrimaryKeyRelatedField(
        model=ProductCategory, source="category", required=False, allow_null=True
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "sku",
            "category_id",
            "category_name",
            "unit",
            "min_stock",
            "current_stock",
            "is_low_stock",
            "is_active",
            "created_at",
        ]
        # `current_stock` — harakatlardan hisoblangan kesh (D3), mijoz
        # uni to'g'ridan-to'g'ri yozolmaydi. Qoldiqni o'zgartirish uchun
        # `adjustment` harakati yoziladi.
        read_only_fields = ["id", "current_stock", "is_low_stock", "created_at"]


class StockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True, default=None)
    expense_amount = serializers.DecimalField(
        source="expense.amount", max_digits=12, decimal_places=2, read_only=True, default=None
    )

    class Meta:
        model = StockMovement
        fields = [
            "id",
            "product",
            "product_name",
            "warehouse",
            "warehouse_name",
            "supplier",
            "supplier_name",
            "direction",
            "movement_type",
            "quantity",
            "unit_cost",
            "occurred_at",
            "reference",
            "note",
            "expense",
            "expense_amount",
            "created_at",
        ]
        read_only_fields = fields


class MovementWriteSerializer(serializers.Serializer):
    """
    Harakat yozish — `ModelSerializer` EMAS.

    Manfiy stok tekshiruvi qulf ostida bajarilishi kerak, ya'ni yozish
    faqat servis funksiyasi orqali bo'ladi (docs/03 §26).
    """

    product_id = TenantPrimaryKeyRelatedField(model=Product, source="product")
    warehouse_id = TenantPrimaryKeyRelatedField(model=Warehouse, source="warehouse")
    supplier_id = TenantPrimaryKeyRelatedField(
        model=Supplier, source="supplier", required=False, allow_null=True
    )
    movement_type = serializers.ChoiceField(choices=MovementType.choices)
    direction = serializers.ChoiceField(choices=MovementDirection.choices, required=False)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.001"))
    unit_cost = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True, min_value=Decimal("0")
    )
    occurred_at = serializers.DateTimeField(required=False)
    reference = serializers.CharField(required=False, allow_blank=True, max_length=100)
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)

    # --- Xarid chiqimi (Q13) ---
    #
    # Sukut YOQILGAN: omborga narxi bilan kelgan mahsulot deyarli har
    # doim sotib olingan, ya'ni pul chiqqan. Katakchani o'chirish —
    # istisno (homiy sovg'asi, chiqimi alohida yozilgan xarid).
    create_expense = serializers.BooleanField(required=False, default=True)
    cash_account_id = TenantPrimaryKeyRelatedField(
        model=CashAccount, source="cash_account", required=False, allow_null=True
    )
    expense_category_id = TenantPrimaryKeyRelatedField(
        model=ExpenseCategory, source="expense_category", required=False, allow_null=True
    )
