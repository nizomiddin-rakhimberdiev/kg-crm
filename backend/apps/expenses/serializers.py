"""Chiqim serializerlari (docs/04 §13)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.utils.translation import gettext
from rest_framework import serializers

from apps.cash.models import CashAccount
from apps.core.fields import TenantPrimaryKeyRelatedField
from apps.expenses.models import Expense, ExpenseCategory, ExpenseItem
from apps.inventory.models import Supplier

__all__ = ["ExpenseCategorySerializer", "ExpenseSerializer", "ExpenseWriteSerializer"]


class ExpenseCategorySerializer(serializers.ModelSerializer):
    """Ikki darajali toifa va hisob kodi (Bosqich 13.2a)."""

    parent_id = TenantPrimaryKeyRelatedField(
        model=ExpenseCategory, source="parent", required=False, allow_null=True
    )
    parent_name = serializers.CharField(source="parent.name", read_only=True, default=None)
    # Oxirgi ishlatilgan — tezkor kiritishda tepada (Bosqich 13.3a).
    last_used_at = serializers.DateTimeField(read_only=True, default=None)

    class Meta:
        model = ExpenseCategory
        fields = [
            "id",
            "name",
            "parent_id",
            "parent_name",
            "account_code",
            "is_active",
            "last_used_at",
            "created_at",
        ]
        read_only_fields = ["id", "parent_name", "last_used_at", "created_at"]

    def validate_parent_id(self, parent: ExpenseCategory | None) -> ExpenseCategory | None:
        if parent is not None and parent.parent_id is not None:
            raise serializers.ValidationError(
                gettext("Toifa ikki darajali: ichki toifaning ichiga toifa qoʻshilmaydi.")
            )
        if parent is not None and self.instance is not None and parent.pk == self.instance.pk:
            raise serializers.ValidationError(gettext("Toifa oʻziga ota boʻla olmaydi."))
        return parent


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
    period = serializers.SerializerMethodField()
    supplier_name = serializers.CharField(source="supplier.name", read_only=True, default=None)
    has_receipt = serializers.SerializerMethodField()

    class Meta:
        model = Expense
        fields = [
            "id",
            "category",
            "category_name",
            "amount",
            "expense_date",
            "period",
            "is_capex",
            "amortize_months",
            "on_credit",
            "supplier",
            "supplier_name",
            "due_date",
            "paid_on",
            "has_receipt",
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

    def get_has_receipt(self, expense: Expense) -> bool:
        return bool(expense.receipt)

    def get_period(self, expense: Expense) -> str:
        """Tegishli oy — `NULL` bo'lsa to'langan oy (eski yozuvlar)."""
        year = expense.period_year or expense.expense_date.year
        month = expense.period_month or expense.expense_date.month
        return f"{year}-{month:02d}"


class ExpenseWriteSerializer(serializers.ModelSerializer):
    category_id = TenantPrimaryKeyRelatedField(model=ExpenseCategory, source="category")
    # Qaysi puldan to'lanadi — kiritish paytidayoq (ADR-17). Yaratishda
    # MAJBURIY (mijoz so'rovi, 2026-10-14; `validate` da): sukut "naqd
    # kassa" bo'lganda bankdan to'langan chiqim jimgina kassadan
    # yozilardi va adashish hech qayerda ko'rinmasdi.
    cash_account_id = TenantPrimaryKeyRelatedField(
        model=CashAccount, source="cash_account", required=False, allow_null=True
    )
    # Qatorlar (PLAN 7.5). Berilsa — summa ULARDAN hisoblanadi va
    # `amount` mijozdan olinmaydi; berilmasa eski yo'l ishlaydi
    # (bitta summa), chunki eski chiqimlar va importlar shunday.
    items = ExpenseItemInputSerializer(many=True, required=False)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    # Bosqich 13.2a: tegishli oy ("YYYY-MM"), investitsiya, nasiya.
    period = serializers.RegexField(
        r"^\d{4}-(0[1-9]|1[0-2])$", required=False, allow_blank=True, write_only=True
    )
    supplier_id = TenantPrimaryKeyRelatedField(
        model=Supplier, source="supplier", required=False, allow_null=True
    )

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
            "period",
            "is_capex",
            "amortize_months",
            "on_credit",
            "supplier_id",
            "due_date",
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
        period = attrs.pop("period", "")
        if period:
            attrs["period_year"], attrs["period_month"] = (int(part) for part in period.split("-"))
        if attrs.get("amortize_months") and not attrs.get(
            "is_capex", getattr(self.instance, "is_capex", False)
        ):
            raise serializers.ValidationError(
                {"amortize_months": gettext("Oylarga taqsimlash faqat investitsiya uchun.")}
            )
        if self.instance is not None:
            # Tahrirlash (PATCH) — faqat yuborilgan maydonlar o'zgaradi.
            return attrs
        if not attrs.get("items") and attrs.get("amount") is None:
            raise serializers.ValidationError(
                {"amount": gettext("Summa yoki chiqim qatorlari kiritilishi kerak.")}
            )
        if attrs.get("on_credit"):
            # Nasiya: pul hali chiqmaydi — qop to'langanda tanlanadi.
            if attrs.get("supplier") is None:
                raise serializers.ValidationError(
                    {"supplier_id": gettext("Nasiya xarid — kimdan olinganini tanlang.")}
                )
        elif attrs.get("cash_account") is None:
            raise serializers.ValidationError(
                {"cash_account_id": gettext("Chiqim qaysi puldan toʻlanayotganini tanlang.")}
            )
        if "period_year" not in attrs and attrs.get("expense_date"):
            attrs["period_year"] = attrs["expense_date"].year
            attrs["period_month"] = attrs["expense_date"].month
        return attrs
