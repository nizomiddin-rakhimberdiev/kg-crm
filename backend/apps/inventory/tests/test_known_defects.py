"""
Ombor ↔ chiqim bog'lanishi — 2026-09-30 auditi (PLAN 1.9, Q13).

Auditda: omborga "Xarid" (20 kg × 15 000 = 300 000) kiritildi, lekin u
chiqimlarga ham, kassaga ham tushmadi. Ya'ni bog'cha pulni sarfladi,
tizim esa buni ko'rmadi — foyda-zarar shu summaga xato bo'ladi.

Q13: "Xarid" ixtiyoriy ravishda chiqim sifatida ham yoziladi (katakcha +
kassa tanlash, sukut — yoqilgan).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from apps.cash.selectors import total_balance
from apps.core.tenancy import organization_context
from apps.expenses.models import Expense
from apps.inventory import services
from apps.inventory.models import Product, ProductCategory, Warehouse

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]

QUANTITY = Decimal("20")
UNIT_COST = Decimal("15000.00")
TOTAL = QUANTITY * UNIT_COST  # 300 000


@pytest.fixture
def warehouse(tenant_a) -> Warehouse:
    with organization_context(tenant_a.organization.id):
        return Warehouse.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Oshxona ombori"
        )


@pytest.fixture
def product(tenant_a) -> Product:
    with organization_context(tenant_a.organization.id):
        category = ProductCategory.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Oziq-ovqat"
        )
        return Product.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            name="Guruch",
            category=category,
            unit="kg",
            min_stock=Decimal("10"),
        )


class TestPurchaseIsAlsoSpending:
    def test_purchase_records_an_expense(self, tenant_a, product, warehouse):
        with organization_context(tenant_a.organization.id):
            services.record_movement(
                product=product,
                warehouse=warehouse,
                movement_type="purchase",
                quantity=QUANTITY,
                unit_cost=UNIT_COST,
            )
            expenses = list(Expense.objects.all())

        assert len(expenses) == 1
        assert expenses[0].amount == TOTAL

    def test_purchase_takes_money_out_of_a_cash_account(self, tenant_a, product, warehouse):
        with organization_context(tenant_a.organization.id):
            before = total_balance(organization_id=tenant_a.organization.id)
            services.record_movement(
                product=product,
                warehouse=warehouse,
                movement_type="purchase",
                quantity=QUANTITY,
                unit_cost=UNIT_COST,
            )
            after = total_balance(organization_id=tenant_a.organization.id)

        assert after == before - TOTAL

    def test_purchase_is_not_counted_twice(self, tenant_a, product, warehouse):
        """Xarid chiqimga bog'lansa ham, foyda-zararda BIR marta ko'rinishi kerak."""
        with organization_context(tenant_a.organization.id):
            movement = services.record_movement(
                product=product,
                warehouse=warehouse,
                movement_type="purchase",
                quantity=QUANTITY,
                unit_cost=UNIT_COST,
            )
            # Bog'lanish ikki tomonlama va bitta: harakat → bitta chiqim.
            assert movement.expense is not None
            assert Expense.objects.filter(pk=movement.expense_id).count() == 1
            assert Expense.objects.count() == 1


class TestPurchaseCanBeSeparated:
    def test_the_expense_link_is_optional(self, tenant_a, product, warehouse):
        """
        Q13: katakcha. Homiy sovg'asi yoki allaqachon yozilgan chiqim —
        omborga kiradi, lekin pul chiqmaydi.
        """
        with organization_context(tenant_a.organization.id):
            movement = services.record_movement(
                product=product,
                warehouse=warehouse,
                movement_type="purchase",
                quantity=QUANTITY,
                unit_cost=UNIT_COST,
                create_expense=False,
            )
            assert movement.expense is None
            assert not Expense.objects.exists()

    def test_a_purchase_without_a_price_creates_no_expense(self, tenant_a, product, warehouse):
        with organization_context(tenant_a.organization.id):
            movement = services.record_movement(
                product=product,
                warehouse=warehouse,
                movement_type="purchase",
                quantity=QUANTITY,
            )
            assert movement.expense is None

    def test_consumption_is_not_spending(self, tenant_a, product, warehouse):
        """Iste'mol — pul harakati emas: pul xarid paytida allaqachon chiqqan."""
        with organization_context(tenant_a.organization.id):
            services.record_movement(
                product=product,
                warehouse=warehouse,
                movement_type="purchase",
                quantity=QUANTITY,
                unit_cost=UNIT_COST,
            )
            before = Expense.objects.count()
            services.record_movement(
                product=product,
                warehouse=warehouse,
                movement_type="consumption",
                quantity=Decimal("5"),
            )
            assert Expense.objects.count() == before

    def test_the_cash_account_can_be_chosen(self, tenant_a, product, warehouse):
        """Q13: qaysi qopdan to'langani tanlanadi."""
        from apps.cash.services import account_for_method

        with organization_context(tenant_a.organization.id):
            bank = account_for_method(branch=tenant_a.branch, method="bank_transfer")
            movement = services.record_movement(
                product=product,
                warehouse=warehouse,
                movement_type="purchase",
                quantity=QUANTITY,
                unit_cost=UNIT_COST,
                cash_account=bank,
            )
            assert movement.expense is not None
            assert movement.expense.cash_account_id == bank.id


class TestQuantityText:
    @pytest.mark.parametrize(
        ("value", "unit", "expected"),
        [
            (Decimal("20.000"), "kg", "20 kg"),
            (Decimal("2.500"), "kg", "2,5 kg"),
            (Decimal("3"), "dona", "3 dona"),
            (Decimal("0.750"), "l", "0,75 l"),
            (Decimal("12.000"), "", "12"),
        ],
    )
    def test_trailing_zeros_are_dropped(self, value, unit, expected):
        """Baza `Decimal(10,3)` saqlaydi — ekranda "20.000 kg" hech kim yozmaydigan shakl."""
        assert services.quantity_text(value, unit) == expected
