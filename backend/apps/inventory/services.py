"""
Ombor mantiqi (docs/03 §15.5, §26).

Markaziy qoida: **manfiy stok bo'lmaydi.** Buni DB `CHECK` bilan
ifodalab bo'lmaydi — u yugurib boruvchi yig'indini ko'rmaydi. Shuning
uchun u tranzaksiya ichida, mahsulot qatorini qulflab tekshiriladi.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.db import transaction
from django.db.models import F, Q, Sum
from django.utils import timezone

from apps.core.exceptions import BusinessRuleViolation
from apps.inventory.models import (
    MovementDirection,
    MovementType,
    Product,
    StockMovement,
    Warehouse,
)

__all__ = [
    "product_stock",
    "record_movement",
    "recompute_product_stock",
    "low_stock_products",
    "stock_valuation",
]

# Kirim beradigan harakat turlari — mijozdan `direction` so'ralmaydi,
# u turdan kelib chiqadi. Aks holda "xarid, lekin chiqim" kabi mantiqan
# imkonsiz kombinatsiya yozilishi mumkin edi.
_INBOUND: set[str] = {MovementType.PURCHASE, MovementType.TRANSFER}
_OUTBOUND: set[str] = {MovementType.CONSUMPTION, MovementType.WASTE}


def direction_for(movement_type: str, explicit: str | None = None) -> str:
    """`movement_type` dan yo'nalishni aniqlaydi."""
    if movement_type in _INBOUND:
        return MovementDirection.IN
    if movement_type in _OUTBOUND:
        return MovementDirection.OUT
    # `adjustment` ikki tomonlama — yo'nalish aniq ko'rsatilishi shart.
    if explicit not in (MovementDirection.IN, MovementDirection.OUT):
        raise BusinessRuleViolation(
            "Tuzatish harakati uchun yo'nalish ('in' yoki 'out') ko'rsatilishi shart."
        )
    return explicit


def product_stock(*, product_id: Any, warehouse_id: Any = None) -> Decimal:
    """Mahsulotning HAQIQIY qoldig'i — harakatlardan hisoblanadi."""
    queryset = StockMovement.objects.filter(product_id=product_id)
    if warehouse_id:
        queryset = queryset.filter(warehouse_id=warehouse_id)

    totals = queryset.aggregate(
        inbound=Sum("quantity", filter=Q(direction=MovementDirection.IN)),
        outbound=Sum("quantity", filter=Q(direction=MovementDirection.OUT)),
    )
    return (totals["inbound"] or Decimal("0")) - (totals["outbound"] or Decimal("0"))


def recompute_product_stock(product: Product) -> Decimal:
    """Kesh ustunini harakatlardan qayta hisoblaydi (D3)."""
    stock = product_stock(product_id=product.id)
    Product.objects.filter(pk=product.pk).update(current_stock=stock)
    return stock


@transaction.atomic
def record_movement(
    *,
    product: Product,
    warehouse: Warehouse,
    movement_type: str,
    quantity: Decimal,
    direction: str | None = None,
    supplier: Any = None,
    unit_cost: Decimal | None = None,
    occurred_at: Any = None,
    reference: str = "",
    note: str = "",
) -> StockMovement:
    """
    Stok harakatini yozadi.

    Chiqim uchun mahsulot qatori QULFLANADI va qoldiq harakatlardan qayta
    hisoblanadi. Qulfsiz ikkita parallel chiqim ikkalasi ham "qoldiq
    yetarli" deb ko'rishi va stok manfiy bo'lib qolishi mumkin —
    `CHECK` buni ushlay olmaydi, u boshqa tranzaksiyani ko'rmaydi
    (docs/03 §26).
    """
    if quantity <= 0:
        raise BusinessRuleViolation("Miqdor musbat bo'lishi kerak.")

    if warehouse.branch_id != product.branch_id:
        raise BusinessRuleViolation("Ombor mahsulot bilan boshqa filialda.")

    resolved = direction_for(movement_type, direction)

    if resolved == MovementDirection.OUT:
        locked = Product.objects.select_for_update().get(pk=product.pk)
        available = product_stock(product_id=locked.id)
        if quantity > available:
            raise BusinessRuleViolation(
                f"'{locked.name}' uchun qoldiq yetarli emas: mavjud {available} "
                f"{locked.unit}, so'ralgan {quantity} {locked.unit}."
            )
        product = locked

    movement = StockMovement.objects.create(
        organization=product.organization,
        branch=product.branch,
        product=product,
        warehouse=warehouse,
        supplier=supplier,
        direction=resolved,
        movement_type=movement_type,
        quantity=quantity,
        unit_cost=unit_cost,
        occurred_at=occurred_at or timezone.now(),
        reference=reference[:100],
        note=note[:255],
    )
    recompute_product_stock(product)
    return movement


def low_stock_products(*, organization_id: Any, branch_id: Any = None) -> list[dict[str, Any]]:
    """
    Qoldig'i minimumdan past mahsulotlar.

    Keshdan o'qiydi (`current_stock`) — bu ro'yxat ogohlantirish uchun,
    pul qarori uchun emas. Aniq qiymat kerak bo'lganda `product_stock()`
    chaqiriladi.
    """
    queryset = Product.objects.filter(
        is_active=True, min_stock__gt=0, current_stock__lt=F("min_stock")
    )
    if branch_id:
        queryset = queryset.filter(branch_id=branch_id)

    return [
        {
            "id": str(product.id),
            "name": product.name,
            "unit": product.unit,
            "current_stock": str(product.current_stock),
            "min_stock": str(product.min_stock),
        }
        for product in queryset.order_by("name")
    ]


def stock_valuation(*, organization_id: Any, branch_id: Any = None) -> dict[str, Any]:
    """
    Ombordagi qoldiqning taxminiy qiymati.

    Oxirgi xarid narxi bo'yicha — o'rtacha yoki FIFO emas. Bu ongli
    soddalashtirish: aniq baholash usuli buxgalteriya qarori bo'lib,
    uni mijoz bilan kelishmasdan tanlash noto'g'ri bo'lardi. Hozircha
    raqam faqat ko'rsatkich sifatida beriladi.
    """
    products = Product.objects.filter(is_active=True, current_stock__gt=0)
    if branch_id:
        products = products.filter(branch_id=branch_id)

    total = Decimal("0")
    rows: list[dict[str, Any]] = []
    for product in products:
        last_cost = (
            StockMovement.objects.filter(
                product=product,
                direction=MovementDirection.IN,
                unit_cost__isnull=False,
            )
            .order_by("-occurred_at")
            .values_list("unit_cost", flat=True)
            .first()
        )
        # Pul ikki xonaga yaxlitlanadi: miqdor uch xonali (12,3) bo'lgani
        # uchun ko'paytma besh xonali chiqadi va bu pul emas.
        value = ((last_cost or Decimal("0")) * product.current_stock).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        total += value
        rows.append(
            {
                "product": product.name,
                "quantity": str(product.current_stock),
                "unit": product.unit,
                "last_unit_cost": str(last_cost) if last_cost else None,
                "value": str(value),
            }
        )

    return {
        "total_value": str(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "basis": "last_purchase_price",
        "items": rows,
    }
