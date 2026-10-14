"""
Chiqim qatorlari (PLAN 7.5) — egasining misoli bilan.

"Bozorlik kategoriyasi uchun kartoshka, 50 kg, 3000, izohsiz —
150 000 so'm ko'rinishida davom etishi kerak."

Eng muhim qoida: summa QATORLARDAN hisoblanadi. Mijoz yuborgan summaga
ishonilsa, ekranda ko'rsatilgan yig'indi bilan kassadan chiqqan pul bir
kun ajralib qolardi va buni hech kim sezmasdi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from apps.cash.models import CashMovement, MovementSource
from apps.core.tenancy import organization_context
from apps.expenses.models import ExpenseCategory

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]

URL = "/api/v1/expenses"


def _category(tenant, name: str = "Bozorlik") -> ExpenseCategory:
    # Bogʻchada pul avval tushadi, keyin chiqadi (ADR-29): boʻsh
    # kassadan chiqim ataylab toʻxtaydi, shuning uchun oqim testlari
    # avval qopni toʻldiradi. Qoʻriqchining oʻzi `apps/cash` da.
    tenant.fund()
    with organization_context(tenant.organization.id):
        return ExpenseCategory.objects.create(
            organization=tenant.organization, branch=tenant.branch, name=name
        )


def _till(category) -> str:
    """Filialning naqd kassasi — "Qaysi puldan" endi majburiy (2026-10-14)."""
    from apps.cash.models import CashAccount

    with organization_context(category.organization_id):
        return str(
            CashAccount.objects.get(branch_id=category.branch_id, kind="cash", is_active=True).id
        )


def _post(client, category, items, **extra):
    return client.post(
        URL,
        {
            "category_id": str(category.id),
            "expense_date": str(date(2026, 10, 6)),
            "items": items,
            "cash_account_id": _till(category),
            **extra,
        },
        format="json",
    )


POTATO = {"name": "Kartoshka", "quantity": "50", "unit": "kg", "unit_price": "3000"}


class TestOwnerExample:
    def test_fifty_kilos_at_three_thousand_is_a_hundred_and_fifty_thousand(self, tenant_a):
        response = _post(tenant_a.client(), _category(tenant_a), [POTATO])
        assert response.status_code == 201, response.json()
        body = response.json()["data"]
        assert body["amount"] == "150000.00"
        (line,) = body["items"]
        assert line["name"] == "Kartoshka"
        assert line["unit"] == "kg"
        assert Decimal(line["quantity"]) == Decimal("50")
        assert line["line_total"] == "150000.00"

    def test_several_lines_add_up(self, tenant_a):
        body = _post(
            tenant_a.client(),
            _category(tenant_a),
            [
                POTATO,
                {"name": "Yogʻ", "quantity": "4", "unit": "l", "unit_price": "28500"},
                {"name": "Tuxum", "quantity": "60", "unit": "dona", "unit_price": "1500"},
            ],
        ).json()["data"]
        # 150 000 + 114 000 + 90 000
        assert body["amount"] == "354000.00"
        assert len(body["items"]) == 3

    def test_the_note_is_optional(self, tenant_a):
        body = _post(
            tenant_a.client(),
            _category(tenant_a),
            [{**POTATO, "note": "bozordan"}, POTATO],
        ).json()["data"]
        notes = sorted(line["note"] for line in body["items"])
        assert notes == ["", "bozordan"]

    def test_a_fractional_quantity_works(self, tenant_a):
        body = _post(
            tenant_a.client(),
            _category(tenant_a),
            [{"name": "Goʻsht", "quantity": "2.5", "unit": "kg", "unit_price": "95000"}],
        ).json()["data"]
        assert body["amount"] == "237500.00"


class TestMoney:
    def test_the_till_loses_exactly_the_sum_of_the_lines(self, tenant_a):
        _post(tenant_a.client(), _category(tenant_a), [POTATO, POTATO])
        with organization_context(tenant_a.organization.id):
            movement = CashMovement.objects.get(source_type=MovementSource.EXPENSE)
        assert movement.amount == Decimal("300000.00")

    def test_a_client_supplied_total_is_ignored(self, tenant_a):
        """Qatorlar bor — summa ulardan, mijoznikidan emas."""
        body = _post(tenant_a.client(), _category(tenant_a), [POTATO], amount="999999").json()[
            "data"
        ]
        assert body["amount"] == "150000.00"

    def test_it_is_approved_at_once(self, tenant_a):
        body = _post(tenant_a.client(), _category(tenant_a), [POTATO]).json()["data"]
        assert body["status"] == "approved"


class TestRefusals:
    def test_without_lines_or_a_total_it_is_refused(self, tenant_a):
        response = tenant_a.client().post(
            URL,
            {"category_id": str(_category(tenant_a).id), "expense_date": "2026-10-06"},
            format="json",
        )
        assert response.status_code == 400

    def test_a_zero_quantity_is_refused(self, tenant_a):
        response = _post(tenant_a.client(), _category(tenant_a), [{**POTATO, "quantity": "0"}])
        assert response.status_code == 400

    def test_a_plain_total_still_works_for_the_old_path(self, tenant_a):
        """Qatorsiz chiqim — eski yo'l, u buzilmasligi kerak."""
        category = _category(tenant_a)
        response = tenant_a.client().post(
            URL,
            {
                "category_id": str(category.id),
                "expense_date": "2026-10-06",
                "amount": "600000",
                "description": "sabzavotlar",
                "cash_account_id": _till(category),
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["data"]["items"] == []

    def test_another_kindergartens_category_is_refused(self, tenant_a, tenant_b):
        response = _post(tenant_a.client(), _category(tenant_b), [POTATO])
        assert response.status_code in (400, 404)
