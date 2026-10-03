from __future__ import annotations

from decimal import Decimal
from typing import Any

from rest_framework import serializers

from apps.kitchen.models import Dish, Meal, MenuDay


class IngredientInputSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=Decimal("0.001"))


class DishWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    portion_grams = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)
    ingredients = IngredientInputSerializer(many=True)
    branch_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_ingredients(self, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not value:
            raise serializers.ValidationError("—")
        return value


class DishSerializer(serializers.ModelSerializer):
    ingredients = serializers.SerializerMethodField()
    cost_per_portion = serializers.SerializerMethodField()

    class Meta:
        model = Dish
        fields = ["id", "name", "portion_grams", "note", "ingredients", "cost_per_portion"]

    def get_ingredients(self, obj: Dish) -> list[dict[str, Any]]:
        return [
            {
                "product_id": str(row.product_id),
                "product": row.product.name,
                "unit": row.product.unit,
                "quantity": str(row.quantity_per_portion),
            }
            for row in obj.ingredients.select_related("product").order_by("product__name")
        ]

    def get_cost_per_portion(self, obj: Dish) -> str | None:
        from apps.kitchen.services import dish_cost

        cost = dish_cost(obj)
        return str(cost) if cost is not None else None


class MenuItemInputSerializer(serializers.Serializer):
    dish_id = serializers.UUIDField()
    meal = serializers.ChoiceField(choices=Meal.choices)


class MenuPlanSerializer(serializers.Serializer):
    menu_date = serializers.DateField()
    warehouse_id = serializers.UUIDField()
    items = MenuItemInputSerializer(many=True)
    branch_id = serializers.UUIDField(required=False, allow_null=True)


class MenuDaySerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)

    class Meta:
        model = MenuDay
        fields = [
            "id",
            "menu_date",
            "warehouse",
            "warehouse_name",
            "status",
            "children_portions",
            "staff_portions",
            "served_at",
            "items",
        ]

    def get_items(self, obj: MenuDay) -> list[dict[str, Any]]:
        return [
            {"dish_id": str(item.dish_id), "dish": item.dish.name, "meal": item.meal}
            for item in obj.items.select_related("dish").order_by("meal", "dish__name")
        ]


class ServeSerializer(serializers.Serializer):
    staff_portions = serializers.IntegerField(required=False, min_value=0, default=0)
