"""
"Imtiyoz-tarif" larni haqiqiy imtiyozga o'tkazish (Bosqich 12.2).

Mijoz imtiyozlarni TARIF qilib kiritgan: "KAM TA`MINLANGANLAR — 0 so'm",
"XODIMLAR FARZANDLARI — 1 525 000". Bu brifdagi "toifa rang bilan
belgilanadi" muammosining tizimdagi ko'rinishi: sababi yo'q, kim bergani
yo'q, hisobotda yo'q. Buyruq bolani asosiy tarifga o'tkazadi va unga
TURI bor imtiyoz yozadi — sukut bo'yicha dry-run.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from io import StringIO
from typing import Any

import pytest
from django.core.management import CommandError, call_command

from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance.charges import plan_month
from apps.finance.models import Discount, TariffPlan

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup(tenant_a: Any) -> dict[str, Any]:
    with organization_context(tenant_a.organization.id):
        base = TariffPlan.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            name="V.I.P",
            amount=Decimal("3050000"),
        )
        staff = TariffPlan.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            name="XODIMLAR FARZANDLARI",
            amount=Decimal("1525000"),
        )
        child = Child.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Ali",
            last_name="Valiyev",
            date_of_birth=date(2021, 3, 14),
            gender="male",
            tariff=staff,
            is_existing_client=True,
        )
    return {"tenant": tenant_a, "base": base, "staff": staff, "child": child}


def _run(*args: str) -> str:
    out = StringIO()
    call_command(
        "convert_benefit_tariffs",
        "--tariff",
        "XODIMLAR FARZANDLARI",
        "--to-tariff",
        "V.I.P",
        "--kind",
        "staff_child",
        "--reason",
        "Xodim farzandi (eski tarifdan)",
        "--from",
        "2026-10-01",
        *args,
        stdout=out,
    )
    return out.getvalue()


def test_dry_run_changes_nothing(setup: dict[str, Any]):
    report = _run()
    with organization_context(setup["tenant"].organization.id):
        setup["child"].refresh_from_db()
        assert setup["child"].tariff_id == setup["staff"].id
        assert not Discount.objects.exists()
    assert "Ali" in report
    assert "dry-run" in report.lower()


def test_apply_moves_the_child_and_keeps_the_amount(setup: dict[str, Any]):
    _run("--apply")
    tenant = setup["tenant"]
    with organization_context(tenant.organization.id):
        child = Child.objects.get(pk=setup["child"].pk)
        benefit = Discount.objects.get(child=child)
        due = plan_month(child, 2026, 10).amount_due
    assert child.tariff_id == setup["base"].id
    assert benefit.kind == "staff_child"
    assert benefit.reason == "Xodim farzandi (eski tarifdan)"
    assert benefit.valid_from == date(2026, 10, 1)
    assert due == Decimal("1525000")  # summa o'zgarmadi — endi sababi bor


def test_a_second_run_does_nothing(setup: dict[str, Any]):
    _run("--apply")
    report = _run("--apply")
    with organization_context(setup["tenant"].organization.id):
        assert Discount.objects.count() == 1
    assert "0 ta" in report


def test_an_unknown_kind_is_refused(setup: dict[str, Any]):
    with pytest.raises(CommandError):
        call_command(
            "convert_benefit_tariffs",
            "--tariff",
            "XODIMLAR FARZANDLARI",
            "--to-tariff",
            "V.I.P",
            "--kind",
            "sibling",
            "--reason",
            "x",
            stdout=StringIO(),
        )
