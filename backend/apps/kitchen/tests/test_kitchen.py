"""
Kitchen: dishes, menu and the stock they consume (PLAN 6.6).

Portions come from the register (present children) plus staff; serving
writes consumption movements — the only way stock changes — all or
nothing; a shortage is refused with the product named; undoing writes
counter-movements, and serve → undo → serve → undo stays exact.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.attendance.models import AttendanceRecord
from apps.children.models import Child, Group
from apps.children.services import enroll_child
from apps.core.tenancy import organization_context
from apps.inventory.models import Product, StockMovement, Warehouse
from apps.inventory.services import product_stock, record_movement

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]

DISHES = "/api/v1/dishes"
MENU = "/api/v1/menu-days"


@pytest.fixture
def kitchen(tenant_a):
    """A store with 10 kg rice at 12 000 so'm/kg and 2 l oil; three children present today."""
    today = timezone.localdate()
    with organization_context(tenant_a.organization.id):
        store = Warehouse.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Oshxona"
        )
        rice = Product.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Guruch", unit="kg"
        )
        oil = Product.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Yogʻ", unit="l"
        )
        for product, quantity, cost in ((rice, "10", "12000"), (oil, "2", "30000")):
            record_movement(
                product=product,
                warehouse=store,
                movement_type="purchase",
                quantity=Decimal(quantity),
                unit_cost=Decimal(cost),
                create_expense=False,
            )
        group = Group.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Quyosh", capacity=9
        )
        for index, status in enumerate(("present", "present", "present", "absent")):
            child = Child.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                first_name=f"Bola{index}",
                last_name="Testov",
                date_of_birth=date(2021, 1, 1),
                gender="male",
            )
            enroll_child(child=child, group=group)
            AttendanceRecord.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                group=group,
                child=child,
                attendance_date=today,
                status=status,
            )
    return {"store": store, "rice": rice, "oil": oil, "today": today}


def _dish(client, kitchen, rice="0.08", oil="0.01") -> dict:
    response = client.post(
        DISHES,
        {
            "name": "Palov",
            "portion_grams": 250,
            "ingredients": [
                {"product_id": str(kitchen["rice"].id), "quantity": rice},
                {"product_id": str(kitchen["oil"].id), "quantity": oil},
            ],
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    return response.json()["data"]


def _menu(client, kitchen, dish, on=None) -> dict:
    response = client.post(
        f"{MENU}/plan",
        {
            "menu_date": str(on or kitchen["today"]),
            "warehouse_id": str(kitchen["store"].id),
            "items": [{"dish_id": dish["id"], "meal": "lunch"}],
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    return response.json()["data"]


def _stock(tenant, product) -> Decimal:
    with organization_context(tenant.organization.id):
        return product_stock(product_id=product.id)


class TestDishes:
    def test_cost_per_portion_from_latest_purchase_prices(self, tenant_a, kitchen):
        dish = _dish(tenant_a.client(), kitchen)
        # 0.08 kg × 12 000 + 0.01 l × 30 000 = 960 + 300
        assert dish["cost_per_portion"] == "1260.00"
        assert [row["product"] for row in dish["ingredients"]] == ["Guruch", "Yogʻ"]

    def test_another_kindergartens_product_cannot_be_an_ingredient(
        self, tenant_a, tenant_b, kitchen
    ):
        with organization_context(tenant_b.organization.id):
            foreign = Product.objects.create(
                organization=tenant_b.organization, branch=tenant_b.branch, name="X", unit="kg"
            )
        response = tenant_a.client().post(
            DISHES,
            {"name": "X", "ingredients": [{"product_id": str(foreign.id), "quantity": "1"}]},
            format="json",
        )
        assert response.status_code == 422

    def test_a_role_without_inventory_is_forbidden(self, tenant_a, kitchen):
        from apps.online_payments.tests.test_endpoints import _member_client

        client = _member_client(tenant_a, "attendance_manager")
        assert client.get(DISHES).status_code == 403


class TestServing:
    def test_preview_counts_present_children_and_staff(self, tenant_a, kitchen):
        client = tenant_a.client()
        menu = _menu(client, kitchen, _dish(client, kitchen))
        data = client.get(f"{MENU}/{menu['id']}/preview", {"staff_portions": 2}).json()["data"]
        assert data["children_portions"] == 3 and data["portions"] == 5
        rice = next(line for line in data["lines"] if line["product"] == "Guruch")
        assert rice["needed"] == "0.400" and data["has_shortage"] is False

    def test_serving_consumes_the_store(self, tenant_a, kitchen):
        client = tenant_a.client()
        menu = _menu(client, kitchen, _dish(client, kitchen))
        served = client.post(f"{MENU}/{menu['id']}/serve", {"staff_portions": 2}, format="json")
        assert served.status_code == 200, served.json()
        assert served.json()["data"]["status"] == "served"
        assert _stock(tenant_a, kitchen["rice"]) == Decimal("9.600")
        assert _stock(tenant_a, kitchen["oil"]) == Decimal("1.950")
        with organization_context(tenant_a.organization.id):
            assert StockMovement.objects.filter(movement_type="consumption").count() == 2

    def test_serving_twice_is_refused(self, tenant_a, kitchen):
        client = tenant_a.client()
        menu = _menu(client, kitchen, _dish(client, kitchen))
        client.post(f"{MENU}/{menu['id']}/serve", {}, format="json")
        assert client.post(f"{MENU}/{menu['id']}/serve", {}, format="json").status_code == 422
        assert _stock(tenant_a, kitchen["rice"]) == Decimal("9.760")

    def test_a_shortage_is_refused_and_named(self, tenant_a, kitchen):
        client = tenant_a.client()
        menu = _menu(client, kitchen, _dish(client, kitchen, rice="5"))
        preview = client.get(f"{MENU}/{menu['id']}/preview").json()["data"]
        assert preview["has_shortage"] is True
        response = client.post(f"{MENU}/{menu['id']}/serve", {}, format="json")
        assert response.status_code == 422
        assert "Guruch" in response.json()["error"]["message"]
        # All or nothing: the oil was not taken either.
        assert _stock(tenant_a, kitchen["oil"]) == Decimal("2.000")

    def test_undo_and_serve_again_stay_exact(self, tenant_a, kitchen):
        client = tenant_a.client()
        menu = _menu(client, kitchen, _dish(client, kitchen))
        for _round in range(2):
            assert client.post(f"{MENU}/{menu['id']}/serve", {}, format="json").status_code == 200
            assert _stock(tenant_a, kitchen["rice"]) == Decimal("9.760")
            undone = client.post(f"{MENU}/{menu['id']}/unserve", {}, format="json")
            assert undone.json()["data"]["status"] == "draft"
            assert _stock(tenant_a, kitchen["rice"]) == Decimal("10.000")
        with organization_context(tenant_a.organization.id):
            # Append-only: nothing deleted, counter-entries written.
            assert StockMovement.objects.filter(movement_type="consumption").count() == 4
            assert StockMovement.objects.filter(movement_type="adjustment").count() == 4

    def test_a_future_day_cannot_be_served(self, tenant_a, kitchen):
        client = tenant_a.client()
        tomorrow = kitchen["today"] + timedelta(days=1)
        menu = _menu(client, kitchen, _dish(client, kitchen), on=tomorrow)
        assert client.post(f"{MENU}/{menu['id']}/serve", {}, format="json").status_code == 422

    def test_without_a_register_there_are_no_portions(self, tenant_a, kitchen):
        client = tenant_a.client()
        yesterday = kitchen["today"] - timedelta(days=1)
        menu = _menu(client, kitchen, _dish(client, kitchen), on=yesterday)
        response = client.post(f"{MENU}/{menu['id']}/serve", {}, format="json")
        assert response.status_code == 422
        assert "davomat" in response.json()["error"]["message"]

    def test_a_served_day_is_closed_for_planning(self, tenant_a, kitchen):
        client = tenant_a.client()
        dish = _dish(client, kitchen)
        menu = _menu(client, kitchen, dish)
        client.post(f"{MENU}/{menu['id']}/serve", {}, format="json")
        response = client.post(
            f"{MENU}/plan",
            {
                "menu_date": str(kitchen["today"]),
                "warehouse_id": str(kitchen["store"].id),
                "items": [],
            },
            format="json",
        )
        assert response.status_code == 422

    def test_another_kindergartens_warehouse_is_404(self, tenant_a, tenant_b, kitchen):
        with organization_context(tenant_b.organization.id):
            foreign = Warehouse.objects.create(
                organization=tenant_b.organization, branch=tenant_b.branch, name="B"
            )
        client = tenant_a.client()
        dish = _dish(client, kitchen)
        response = client.post(
            f"{MENU}/plan",
            {
                "menu_date": str(kitchen["today"]),
                "warehouse_id": str(foreign.id),
                "items": [{"dish_id": dish["id"], "meal": "lunch"}],
            },
            format="json",
        )
        assert response.status_code == 404
