"""
Sozlanadigan qayta hisob turlari (Bosqich 12.3, owner's brief 2026-10-14 §2).

Ilgari ikkita qotirilgan tur bor edi — maʼlumotnoma va ariza — va ikkalasi
ham to'liq kunlik stavka qaytarardi. Brif:

* maʼlumotnoma: 1–2 ketma-ket ish kuni → faqat ovqat puli (kuniga
  `contracts.daily_meal_fee`, sukut 37 500); 3+ kun → shu kunlarning
  HAMMASI uchun to'liq stavka;
* ariza: to'liq stavka, minimal kunlar sozlanadi (sukut 1);
* boshqa turlar shu tuzilmada qo'shiladi: qaytarish usuli (to'liq stavka /
  kuniga qat'iy summa / qaytarilmaydi), minimal kunlar, hujjat.

Fakturadagi qatorda formula ko'rinadi: "2 × 37 500 (ovqat puli) = 75 000".
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from apps.attendance.models_absence import Holiday
from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.finance.models import TariffPlan

pytestmark = pytest.mark.django_db

URL = "/api/v1/absence-claims"


@pytest.fixture
def sept(tenant_a: Any) -> Any:
    with organization_context(tenant_a.organization.id):
        Holiday.objects.create(
            organization=tenant_a.organization, holiday_date=date(2026, 9, 1), name="Mustaqillik"
        )
    return tenant_a


def _child(tenant: Any) -> Child:
    with organization_context(tenant.organization.id):
        tariff = TariffPlan.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            name=f"Asosiy {Child.objects.count()}",
            amount=Decimal("3050000"),
        )
        return Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Ali",
            last_name="Valiyev",
            date_of_birth=date(2021, 3, 14),
            gender="male",
            tariff=tariff,
            is_existing_client=True,
        )


def _claim(tenant: Any, child: Child, kind: str, start: str, end: str) -> Any:
    """
    Maʼlumotnoma RAQAMI bilan: 2026-10-30 dan beri hujjat talab
    qiladigan tur hujjatsiz tasdiqlanmaydi (audit), bu testlar esa
    qaytariladigan summani sinaydi — yaʼni daʼvo tasdiqlangan
    boʻlishi kerak.
    """
    return tenant.client().post(
        URL,
        {
            "child_id": str(child.id),
            "kind": kind,
            "date_from": start,
            "date_to": end,
            "document_no": "M-4821",
        },
        format="json",
    )


def _credit(response: Any) -> Decimal:
    assert response.status_code == 201, response.json()
    return Decimal(response.json()["data"]["credit_amount"])


# --- 6, 7, 9 ---


def test_6_two_sick_days_return_only_the_meal_money(sept: Any):
    response = _claim(sept, _child(sept), "medical", "2026-09-07", "2026-09-08")
    assert _credit(response) == Decimal("75000")
    assert response.json()["data"]["basis"] == "fixed_per_day"


def test_7_three_sick_days_return_the_full_rate_for_all_three(sept: Any):
    response = _claim(sept, _child(sept), "medical", "2026-09-07", "2026-09-09")
    assert _credit(response) == Decimal("436000")
    assert response.json()["data"]["basis"] == "full_rate"


def test_9_an_eight_day_application_returns_the_full_rate(sept: Any):
    assert _credit(_claim(sept, _child(sept), "parental", "2026-09-21", "2026-09-30")) == Decimal(
        "1162000"
    )


def test_the_meal_money_is_the_contract_setting(sept: Any):
    from apps.settings_app.services import set_setting

    with organization_context(sept.organization.id):
        set_setting(organization=sept.organization, key="contracts.daily_meal_fee", value="40000")
    assert _credit(_claim(sept, _child(sept), "medical", "2026-09-07", "2026-09-08")) == Decimal(
        "80000"
    )


# --- Turlar sozlanadi ---


def test_the_default_kinds_are_listed_for_the_claim_form(sept: Any):
    response = sept.client().get(f"{URL}/kinds")
    assert response.status_code == 200
    codes = {row["code"]: row for row in response.json()["data"]}
    assert codes["medical"]["refund_mode"] == "fixed_per_day"
    assert codes["medical"]["full_rate_from_days"] == 3
    assert codes["parental"]["refund_mode"] == "full_rate"


def test_a_new_kind_can_be_added_and_used(sept: Any):
    created = sept.client().post(
        "/api/v1/absence-kinds",
        {
            "code": "sanatoriy",
            "name": "Sanatoriy yoʻllanmasi",
            "refund_mode": "fixed_per_day",
            "daily_amount": "50000",
            "min_days": 5,
        },
        format="json",
    )
    assert created.status_code == 201, created.json()
    assert _credit(_claim(sept, _child(sept), "sanatoriy", "2026-09-21", "2026-09-25")) == Decimal(
        "250000"
    )


def test_fewer_days_than_the_minimum_are_refused(sept: Any):
    sept.client().post(
        "/api/v1/absence-kinds",
        {"code": "safar", "name": "Safar", "refund_mode": "full_rate", "min_days": 5},
        format="json",
    )
    response = _claim(sept, _child(sept), "safar", "2026-09-21", "2026-09-22")
    assert response.status_code == 422


def test_a_kind_that_returns_nothing_records_the_absence_at_zero(sept: Any):
    sept.client().post(
        "/api/v1/absence-kinds",
        {"code": "sababsiz", "name": "Sababsiz", "refund_mode": "none"},
        format="json",
    )
    assert _credit(_claim(sept, _child(sept), "sababsiz", "2026-09-21", "2026-09-22")) == 0


def test_an_unknown_kind_is_refused(sept: Any):
    assert _claim(sept, _child(sept), "yoq", "2026-09-21", "2026-09-22").status_code == 400


def test_only_settings_holders_change_the_rules(sept: Any):
    from rest_framework.test import APIClient

    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.models import User

    with organization_context(sept.organization.id):
        user = User.objects.create_user(
            email="davomat@alfa.uz",
            password="Juda-Kuchli-Parol-2026",  # noqa: S106
            full_name="Davomat",
            organization=sept.organization,
            role=sept.role("attendance_manager"),
            branch=sept.branch,
        )
        tokens = issue_token_pair(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert client.get(f"{URL}/kinds").status_code == 200  # forma uchun o'qiydi
    assert (
        client.post(
            "/api/v1/absence-kinds",
            {"code": "x", "name": "x", "refund_mode": "full_rate"},
            format="json",
        ).status_code
        == 403
    )


# --- Fakturadagi formula ---


def test_the_invoice_line_shows_the_formula(sept: Any):
    child = _child(sept)
    _claim(sept, child, "medical", "2026-09-07", "2026-09-08")
    with organization_context(sept.organization.id):
        invoice = finance.issue_invoice(child=child, period_year=2026, period_month=9)
        line = invoice.lines.get(kind="credit")
    assert line.formula == "2 × 37 500 = 75 000"
    assert "ovqat" in line.description.lower()
    assert invoice.amount_due == Decimal("2975000")


@pytest.mark.tenancy
def test_another_tenants_kind_is_404(sept: Any, tenant_b: Any):
    created = sept.client().post(
        "/api/v1/absence-kinds",
        {"code": "safar", "name": "Safar", "refund_mode": "full_rate"},
        format="json",
    )
    kind_id = created.json()["data"]["id"]
    assert (
        tenant_b.client()
        .patch(f"/api/v1/absence-kinds/{kind_id}", {"name": "x"}, format="json")
        .status_code
        == 404
    )
