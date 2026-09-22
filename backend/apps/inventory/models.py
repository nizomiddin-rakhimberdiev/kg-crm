"""
Ombor (docs/03 §15).

Moliya bilan bir xil falsafa: **stok darajasi o'zgarmas `stock_movement`
qatorlaridan hisoblanadi** (D3). `product.current_stock` — faqat kesh.

Bu Ovqatlanish rejasi moduli uchun ham poydevor: retsept stokni
iste'mol qiladi (docs/02 §22.2).
"""

from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy

from apps.core.models import BranchScopedModel

__all__ = [
    "Warehouse",
    "ProductCategory",
    "Product",
    "Supplier",
    "StockMovement",
    "MovementType",
    "MovementDirection",
    "Unit",
]


class Warehouse(BranchScopedModel):
    """Saqlash joyi (oshxona ombori, quruq oziq-ovqat ombori)."""

    name = models.CharField(max_length=80)

    class Meta:
        db_table = "warehouse"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "name"],
                condition=models.Q(is_active=True),
                name="uq_warehouse_branch_name",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class ProductCategory(BranchScopedModel):
    name = models.CharField(max_length=80)

    class Meta:
        db_table = "product_category"
        ordering = ["name"]
        verbose_name_plural = "product categories"
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "name"],
                condition=models.Q(is_active=True),
                name="uq_product_category_branch_name",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Unit(models.TextChoices):
    KG = "kg", gettext_lazy("kg")
    G = "g", "g"
    L = "l", "l"
    ML = "ml", gettext_lazy("ml")
    PCS = "pcs", gettext_lazy("dona")
    PACK = "pack", gettext_lazy("upakovka")


class Product(BranchScopedModel):
    name = models.CharField(max_length=120)
    sku = models.CharField(max_length=40, blank=True)
    category = models.ForeignKey(
        "inventory.ProductCategory",
        on_delete=models.SET_NULL,
        related_name="products",
        null=True,
        blank=True,
    )
    unit = models.CharField(max_length=15, choices=Unit.choices)
    min_stock = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0"))

    # Harakatlardan keshlangan (docs/03 §8.2). Haqiqat manbai —
    # `stock_movement`; bu ustun faqat ro'yxat va past-stok ogohlantirishi
    # uchun va istalgan vaqtda qayta hisoblanadi.
    current_stock = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0"))

    class Meta:
        db_table = "product"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "name"],
                condition=models.Q(is_active=True),
                name="uq_product_branch_name",
            ),
            models.UniqueConstraint(
                fields=["branch", "sku"],
                condition=~models.Q(sku=""),
                name="uq_product_sku",
            ),
            models.CheckConstraint(
                condition=models.Q(min_stock__gte=0), name="ck_product_min_stock"
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "branch"], name="ix_product_org_br"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.unit})"

    @property
    def is_low_stock(self) -> bool:
        return self.min_stock > 0 and self.current_stock < self.min_stock


class Supplier(BranchScopedModel):
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20, blank=True)
    contact_person = models.CharField(max_length=120, blank=True)

    class Meta:
        db_table = "supplier"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "name"],
                condition=models.Q(is_active=True),
                name="uq_supplier_branch_name",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class MovementDirection(models.TextChoices):
    IN = "in", gettext_lazy("Kirim")
    OUT = "out", gettext_lazy("Chiqim")


class MovementType(models.TextChoices):
    PURCHASE = "purchase", gettext_lazy("Xarid")
    CONSUMPTION = "consumption", gettext_lazy("Iste'mol")
    ADJUSTMENT = "adjustment", gettext_lazy("Tuzatish")
    WASTE = "waste", gettext_lazy("Yaroqsiz")
    TRANSFER = "transfer", gettext_lazy("Ko'chirish")


class StockMovement(BranchScopedModel):
    """
    Append-only stok harakati — stok uchun YAGONA haqiqat manbai (D3).

    Qatorlar hech qachon tahrirlanmaydi va o'chirilmaydi. Xato `adjustment`
    harakati bilan tuzatiladi. Sabab moliyaviy ledger bilan bir xil:
    yangilanadigan stok ustuni jimgina siljiydi va siljish qachon
    boshlanganini hech kim ayta olmaydi.
    """

    product = models.ForeignKey(
        "inventory.Product", on_delete=models.RESTRICT, related_name="movements"
    )
    warehouse = models.ForeignKey(
        "inventory.Warehouse", on_delete=models.RESTRICT, related_name="movements"
    )
    supplier = models.ForeignKey(
        "inventory.Supplier",
        on_delete=models.SET_NULL,
        related_name="movements",
        null=True,
        blank=True,
    )

    direction = models.CharField(max_length=4, choices=MovementDirection.choices)
    movement_type = models.CharField(max_length=15, choices=MovementType.choices)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    occurred_at = models.DateTimeField(db_index=True)
    reference = models.CharField(max_length=100, blank=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "stock_movement"
        ordering = ["-occurred_at", "-created_at"]
        constraints = [
            # Miqdor har doim MUSBAT; ishora `direction` dan keladi —
            # ledger bilan bir xil qoida.
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0), name="ck_movement_quantity_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(unit_cost__isnull=True) | models.Q(unit_cost__gte=0),
                name="ck_movement_unit_cost",
            ),
        ]
        indexes = [
            models.Index(fields=["product", "occurred_at"], name="ix_movement_product_time"),
            models.Index(
                fields=["organization", "warehouse", "occurred_at"],
                name="ix_movement_org_wh_time",
            ),
        ]

    def __str__(self) -> str:
        sign = "+" if self.direction == MovementDirection.IN else "−"
        return f"{sign}{self.quantity} {self.product_id}"

    @property
    def signed_quantity(self) -> Decimal:
        return self.quantity if self.direction == MovementDirection.IN else -self.quantity
