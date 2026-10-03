"""
Kitchen services (PLAN 6.6).

Serving is all-or-nothing and refuses a shortage. The design note proposed
letting stock go negative ("the food is already eaten"); the inventory
module's rule — no stock-out beyond what is on hand, checked under a row
lock — is the documented, working one and wins. The preview names every
missing product, so the fix (record the purchase or an adjustment) is
obvious before anyone presses "served". Owner's decision pending.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext

from apps.core.exceptions import BusinessRuleViolation
from apps.kitchen.models import Dish, DishIngredient, MenuDay, MenuItem, MenuStatus

__all__ = [
    "save_dish",
    "dish_cost",
    "set_menu",
    "Requirement",
    "preview",
    "serve",
    "unserve",
]

_QTY = Decimal("0.001")


def _serving_ref(menu_day_id: Any, served_at: Any) -> str:
    """One reference per serving: serve → undo → serve again must not undo twice."""
    return f"menu:{menu_day_id}:{int(served_at.timestamp() * 1_000_000)}"


@transaction.atomic
def save_dish(
    *,
    organization: Any,
    branch: Any,
    dish: Dish | None,
    name: str,
    ingredients: list[dict[str, Any]],
    portion_grams: int | None = None,
    note: str = "",
) -> Dish:
    """Creates or updates a dish; the ingredient list is replaced as a whole."""
    from apps.inventory.selectors import products_queryset

    product_ids = [row["product_id"] for row in ingredients]
    if len(set(product_ids)) != len(product_ids):
        raise BusinessRuleViolation(
            gettext("Bitta mahsulot taomda ikki marta boʻlishi mumkin emas.")
        )
    products = {
        p.id: p for p in products_queryset().filter(id__in=product_ids, branch_id=branch.id)
    }
    if len(products) != len(product_ids):
        raise BusinessRuleViolation(gettext("Mahsulot topilmadi yoki boshqa filialda."))

    if dish is None:
        dish = Dish.objects.create(
            organization=organization,
            branch=branch,
            name=name,
            portion_grams=portion_grams,
            note=note,
        )
    else:
        dish.name, dish.portion_grams, dish.note = name, portion_grams, note
        dish.save(update_fields=["name", "portion_grams", "note", "updated_at"])
        dish.ingredients.all().delete()

    DishIngredient.objects.bulk_create(
        [
            DishIngredient(
                organization=organization,
                branch=branch,
                dish=dish,
                product=products[row["product_id"]],
                quantity_per_portion=Decimal(row["quantity"]).quantize(_QTY),
            )
            for row in ingredients
        ]
    )
    return dish


def dish_cost(dish: Dish) -> Decimal | None:
    """Cost of one portion at the latest purchase prices; `None` if a price is unknown."""
    from apps.inventory.selectors import last_purchase_costs

    rows = list(dish.ingredients.all())
    costs = last_purchase_costs([row.product_id for row in rows])
    total = Decimal("0")
    for row in rows:
        if row.product_id not in costs:
            return None
        total += row.quantity_per_portion * costs[row.product_id]
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@transaction.atomic
def set_menu(
    *, organization: Any, branch: Any, menu_date: date, warehouse: Any, items: list[dict[str, Any]]
) -> MenuDay:
    """Plans a day: `[{dish_id, meal}]`. A served day is closed for edits."""
    if warehouse.branch_id != branch.id:
        raise BusinessRuleViolation(gettext("Ombor boshqa filialda."))
    menu_day, _ = MenuDay.objects.get_or_create(
        branch=branch,
        menu_date=menu_date,
        defaults={"organization": organization, "warehouse": warehouse},
    )
    if menu_day.status == MenuStatus.SERVED:
        raise BusinessRuleViolation(
            gettext(
                "Bu kun allaqachon berilgan. Oʻzgartirish uchun avval «Berildi»ni bekor qiling."
            )
        )
    dishes = {d.id: d for d in Dish.objects.filter(branch=branch, is_active=True)}
    menu_day.warehouse = warehouse
    menu_day.save(update_fields=["warehouse", "updated_at"])
    menu_day.items.all().delete()
    for row in items:
        dish = dishes.get(row["dish_id"])
        if dish is None:
            raise BusinessRuleViolation(gettext("Taom topilmadi."))
        MenuItem.objects.create(
            organization=organization, branch=branch, menu_day=menu_day, dish=dish, meal=row["meal"]
        )
    return menu_day


@dataclass
class Requirement:
    product: Any
    needed: Decimal
    available: Decimal

    @property
    def short(self) -> Decimal:
        return max(Decimal("0"), self.needed - self.available)


def _requirements(menu_day: MenuDay, portions: int) -> list[Requirement]:
    from apps.inventory.selectors import available_stock

    needed: dict[Any, Decimal] = {}
    products: dict[Any, Any] = {}
    for item in menu_day.items.select_related("dish"):
        for row in item.dish.ingredients.select_related("product"):
            products[row.product_id] = row.product
            needed[row.product_id] = needed.get(row.product_id, Decimal("0")) + (
                row.quantity_per_portion * portions
            )
    return [
        Requirement(
            product=products[pid],
            needed=amount.quantize(_QTY),
            available=available_stock(pid),
        )
        for pid, amount in sorted(needed.items(), key=lambda kv: products[kv[0]].name)
    ]


def preview(menu_day: MenuDay, *, staff_portions: int = 0) -> dict[str, Any]:
    """What serving would take from the store — shown before the button is pressed."""
    from apps.attendance.selectors import present_count

    children = present_count(branch_id=menu_day.branch_id, on_date=menu_day.menu_date)
    total = children + max(0, staff_portions)
    lines = _requirements(menu_day, total)
    return {
        "children_portions": children,
        "staff_portions": max(0, staff_portions),
        "portions": total,
        "lines": [
            {
                "product_id": str(line.product.id),
                "product": line.product.name,
                "unit": line.product.unit,
                "needed": str(line.needed),
                "available": str(line.available),
                "short": str(line.short),
            }
            for line in lines
        ],
        "has_shortage": any(line.short > 0 for line in lines),
    }


@transaction.atomic
def serve(menu_day: MenuDay, *, staff_portions: int = 0, user: Any = None) -> MenuDay:
    """Writes one consumption movement per product — all or nothing."""
    from apps.attendance.selectors import present_count
    from apps.inventory.models import MovementType
    from apps.inventory.services import record_movement

    locked = MenuDay.objects.select_for_update().get(pk=menu_day.pk)
    if locked.status == MenuStatus.SERVED:
        raise BusinessRuleViolation(gettext("Bu kun allaqachon berilgan."))
    if locked.menu_date > timezone.localdate():
        raise BusinessRuleViolation(gettext("Kelajakdagi kunni «berildi» qilib boʻlmaydi."))
    if not locked.items.exists():
        raise BusinessRuleViolation(gettext("Menyuda taom yoʻq."))

    children = present_count(branch_id=locked.branch_id, on_date=locked.menu_date)
    portions = children + max(0, staff_portions)
    if portions == 0:
        raise BusinessRuleViolation(
            gettext("Porsiya soni nol: avval shu kun davomatini belgilang.")
        )
    lines = _requirements(locked, portions)
    missing = [line for line in lines if line.short > 0]
    if missing:
        raise BusinessRuleViolation(
            gettext("Omborda yetmaydi: {items}. Avval kirim yoki tuzatish kiriting.").format(
                items=", ".join(
                    f"{line.product.name} ({line.short} {line.product.unit})" for line in missing
                )
            )
        )
    served_at = timezone.now()
    for line in lines:
        record_movement(
            product=line.product,
            warehouse=locked.warehouse,
            movement_type=MovementType.CONSUMPTION,
            quantity=line.needed,
            occurred_at=served_at,
            reference=_serving_ref(locked.id, served_at),
            note=gettext("Menyu {date}").format(date=locked.menu_date.strftime("%d.%m.%Y")),
            create_expense=False,
            created_by=user,
        )
    locked.status = MenuStatus.SERVED
    locked.children_portions = children
    locked.staff_portions = max(0, staff_portions)
    locked.served_at = served_at
    locked.served_by = user
    locked.save(
        update_fields=[
            "status",
            "children_portions",
            "staff_portions",
            "served_at",
            "served_by",
            "updated_at",
        ]
    )
    return locked


@transaction.atomic
def unserve(menu_day: MenuDay, *, user: Any = None) -> MenuDay:
    """A mistaken "served": counter-movements back into the store, never a delete."""
    from apps.inventory.models import MovementDirection, MovementType, StockMovement
    from apps.inventory.services import record_movement

    locked = MenuDay.objects.select_for_update().get(pk=menu_day.pk)
    if locked.status != MenuStatus.SERVED:
        raise BusinessRuleViolation(gettext("Bu kun hali berilmagan."))
    assert locked.served_at is not None  # ck_menu_day_served_at
    for movement in StockMovement.objects.filter(
        reference=_serving_ref(locked.id, locked.served_at),
        movement_type=MovementType.CONSUMPTION,
    ).select_related("product", "warehouse"):
        record_movement(
            product=movement.product,
            warehouse=movement.warehouse,
            movement_type=MovementType.ADJUSTMENT,
            direction=MovementDirection.IN,
            quantity=movement.quantity,
            reference=f"menu-undo:{locked.id}",
            note=gettext("Menyu bekor qilindi"),
            create_expense=False,
            created_by=user,
        )
    locked.status = MenuStatus.DRAFT
    locked.children_portions = None
    locked.served_at = None
    locked.served_by = None
    locked.save(
        update_fields=["status", "children_portions", "served_at", "served_by", "updated_at"]
    )
    return locked
