"""
Kitchen: dishes, the daily menu and what it takes from the store (PLAN 6.6).

A dish is a recipe per ONE portion (`dish_ingredient.quantity_per_portion`,
in the product's own unit). A day's menu is served once: portions = the
children marked present that day + the staff portions entered at serving,
and every ingredient becomes a `stock_movement(consumption)` — the
append-only stock ledger (invariant 3) is the only place stock changes.
Undoing a serving writes counter-movements (`adjustment`), never an edit.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy

from apps.core.models import BranchScopedModel

__all__ = ["Dish", "DishIngredient", "Meal", "MenuDay", "MenuItem", "MenuStatus"]


class Dish(BranchScopedModel):
    name = models.CharField(max_length=150)
    portion_grams = models.PositiveIntegerField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "dish"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "name"], condition=models.Q(is_active=True), name="uq_dish_name"
            ),
        ]

    def __str__(self) -> str:
        return self.name


class DishIngredient(BranchScopedModel):
    dish = models.ForeignKey(Dish, on_delete=models.RESTRICT, related_name="ingredients")
    product = models.ForeignKey(
        "inventory.Product", on_delete=models.RESTRICT, related_name="dish_ingredients"
    )
    quantity_per_portion = models.DecimalField(max_digits=10, decimal_places=3)

    class Meta:
        db_table = "dish_ingredient"
        constraints = [
            models.UniqueConstraint(fields=["dish", "product"], name="uq_dish_ingredient"),
            models.CheckConstraint(
                condition=models.Q(quantity_per_portion__gt=Decimal("0")),
                name="ck_dish_ingredient_quantity",
            ),
        ]


class MenuStatus(models.TextChoices):
    DRAFT = "draft", gettext_lazy("Reja")
    SERVED = "served", gettext_lazy("Berildi")


class Meal(models.TextChoices):
    BREAKFAST = "breakfast", gettext_lazy("Nonushta")
    LUNCH = "lunch", gettext_lazy("Tushlik")
    SNACK = "snack", gettext_lazy("Poldnik")
    DINNER = "dinner", gettext_lazy("Kechki ovqat")


class MenuDay(BranchScopedModel):
    menu_date = models.DateField()
    warehouse = models.ForeignKey(
        "inventory.Warehouse", on_delete=models.RESTRICT, related_name="menu_days"
    )
    status = models.CharField(max_length=10, choices=MenuStatus.choices, default=MenuStatus.DRAFT)
    children_portions = models.PositiveIntegerField(null=True, blank=True)
    staff_portions = models.PositiveIntegerField(default=0)
    served_at = models.DateTimeField(null=True, blank=True)
    served_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, related_name="+", null=True, blank=True
    )

    class Meta:
        db_table = "menu_day"
        ordering = ["-menu_date"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "menu_date"], name="uq_menu_day_branch_date"),
            models.CheckConstraint(
                condition=models.Q(status__in=["draft", "served"]), name="ck_menu_day_status"
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status="draft", served_at__isnull=True)
                    | models.Q(status="served", served_at__isnull=False)
                ),
                name="ck_menu_day_served_at",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.menu_date} ({self.status})"


class MenuItem(BranchScopedModel):
    menu_day = models.ForeignKey(MenuDay, on_delete=models.RESTRICT, related_name="items")
    dish = models.ForeignKey(Dish, on_delete=models.RESTRICT, related_name="menu_items")
    meal = models.CharField(max_length=10, choices=Meal.choices)

    class Meta:
        db_table = "menu_item"
        constraints = [
            models.UniqueConstraint(fields=["menu_day", "dish", "meal"], name="uq_menu_item"),
            models.CheckConstraint(
                condition=models.Q(meal__in=["breakfast", "lunch", "snack", "dinner"]),
                name="ck_menu_item_meal",
            ),
        ]
