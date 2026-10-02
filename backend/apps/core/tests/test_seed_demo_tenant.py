"""
Namoyish bog'chasi (`/t/demo`, PLAN 5.10).

Eng muhim test — oxirgisi: buyruq **boshqa tenantga tegmaydi**, hatto
`--reset` bilan ham. `seed_demo` bir marta haqiqiy mijozning
tashkilotini to'ldirib qo'ygan — bu buyruq aynan shu xatoning
takrorlanmasligi uchun alohida yozilgan.
"""

from __future__ import annotations

from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from apps.core.tenancy import organization_context, platform_context

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]

PASSWORD = "Demo-Juda-Kuchli-2026"  # noqa: S105 — test ma'lumoti


@pytest.fixture
def demo_env(monkeypatch):
    monkeypatch.setenv("DEMO_OWNER_PASSWORD", PASSWORD)


def _run(*args: str) -> str:
    out = StringIO()
    call_command("seed_demo_tenant", *args, stdout=out)
    return out.getvalue()


def _demo():
    from apps.organizations.models import Organization

    with platform_context():
        return Organization.objects.filter(slug="demo").first()


def _footprint(organization_id) -> dict[str, int]:
    """Tenantning operatsion "izi" — tegilganini sezish uchun."""
    from apps.audit.models import AuditLog
    from apps.children.models import Child, Group
    from apps.finance.models import Invoice, Payment

    with organization_context(organization_id):
        return {
            "children": Child.objects.count(),
            "groups": Group.objects.count(),
            "invoices": Invoice.objects.count(),
            "payments": Payment.objects.count(),
            "audit": AuditLog.objects.count(),
        }


def test_the_demo_has_what_the_brief_asks_for(demo_env):
    from apps.attendance.models import AttendanceRecord
    from apps.children.models import Child, Group
    from apps.expenses.models import ExpenseCategory
    from apps.hr.models import Employee
    from apps.inventory.models import StockMovement
    from apps.reports.selectors import debtor_report
    from apps.settings_app.services import get_setting

    _run()
    demo = _demo()
    assert demo is not None

    with organization_context(demo.id):
        assert Group.objects.count() == 3
        children = list(Child.objects.all())
        assert len(children) == 45

        # Takrorsiz va jinsiga mos: ism+familiya juftligi bir marta,
        # ota ismi `oʻgʻli` / `qizi`, ayol familiyasi `-a` bilan.
        pairs = {(c.last_name, c.first_name) for c in children}
        assert len(pairs) == 45
        for child in children:
            if child.gender == "male":
                assert child.middle_name.endswith("oʻgʻli")
                assert not child.last_name.endswith("a")
            else:
                assert child.middle_name.endswith("qizi")
                assert child.last_name.endswith("a")

        debtors = debtor_report(organization_id=demo.id)["debtor_count"]
        assert 0.10 <= debtors / 45 <= 0.15, f"qarzdorlar: {debtors}/45"

        assert Employee.objects.count() == 8
        assert StockMovement.objects.exists()
        assert {"Oziq-ovqat", "Kommunal", "Ijara", "Xoʻjalik"} <= set(
            ExpenseCategory.objects.values_list("name", flat=True)
        )

        oldest = AttendanceRecord.objects.order_by("attendance_date").first().attendance_date
        assert oldest >= timezone.localdate().replace(day=1) - timedelta(days=95)

        assert get_setting(key="notifications.sms_enabled") is False


def test_dry_run_writes_nothing(demo_env):
    output = _run("--dry-run")
    assert "dry-run" in output
    assert _demo() is None


def test_a_second_run_without_reset_is_refused(demo_env):
    _run()
    with pytest.raises(CommandError, match="--reset"):
        _run()


def test_reset_rebuilds_the_demo(demo_env):
    _run()
    first = _demo().id
    _run("--reset")
    demo = _demo()
    assert demo.id != first
    assert _footprint(demo.id)["children"] == 45


def test_the_password_comes_only_from_the_environment(monkeypatch):
    monkeypatch.delenv("DEMO_OWNER_PASSWORD", raising=False)
    with pytest.raises(CommandError, match="DEMO_OWNER_PASSWORD"):
        _run()


def test_no_other_tenant_is_touched(demo_env, tenant_a):
    """
    `seed_demo` bir marta haqiqiy mijozning tashkilotini to'ldirgan.

    Bu buyruqda nishon argumenti umuman yo'q, lekin buni test ham
    ushlab turishi kerak — `--reset` (to'liq o'chirish) bilan birga.
    """
    from apps.children.models import Child, Group

    with organization_context(tenant_a.organization.id):
        group = Group.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Alfa", capacity=10
        )
        Child.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Haqiqiy",
            last_name="Bola",
            date_of_birth=timezone.localdate() - timedelta(days=1500),
            gender="male",
        )
    assert group.id
    before = _footprint(tenant_a.organization.id)

    _run()
    _run("--reset")

    assert _footprint(tenant_a.organization.id) == before
