"""
Sukut toifa nomlarini yangilash buyrug'i (audit, 2026-10-21).

Buyruq mavjud tenantning ma'lumotiga tegadi, shuning uchun uning
qoidasi qattiq: faqat ESKI SUKUT nomni hali saqlab turgan va kutilgan
ota-toifa ostidagi qator o'zgaradi. Bog'cha toifani o'zi qayta
nomlagan bo'lsa — uning so'zi qoladi.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.core.management import call_command

from apps.core.tenancy import organization_context
from apps.expenses.models import ExpenseCategory

pytestmark = pytest.mark.django_db


def _category(tenant: Any, name: str, parent: Any = None) -> ExpenseCategory:
    return ExpenseCategory.objects.create(
        organization=tenant.organization, branch=tenant.branch, name=name, parent=parent
    )


def test_dry_run_changes_nothing(tenant_a: Any):
    with organization_context(tenant_a.organization.id):
        parent = _category(tenant_a, "Marketing")
        row = _category(tenant_a, "Target", parent)

    call_command("rename_default_categories", slug=tenant_a.organization.slug)

    with organization_context(tenant_a.organization.id):
        row.refresh_from_db()
        assert row.name == "Target"


def test_apply_renames_only_the_expected_rows(tenant_a: Any):
    with organization_context(tenant_a.organization.id):
        marketing = _category(tenant_a, "Marketing")
        target = _category(tenant_a, "Target", marketing)
        payroll = _category(tenant_a, "Ish haqi")
        cash_part = _category(tenant_a, "Naqd qism", payroll)
        # Ota-toifasi YOʻQ bir darajali toifa — TEGILMAYDI (nom
        # filial ichida unikal, shuning uchun u boshqacha atalgan).
        stray = _category(tenant_a, "Targetlash")
        # Bogʻcha oʻzi qayta nomlagan — TEGILMAYDI.
        renamed = _category(tenant_a, "Instagram reklama", marketing)

    call_command("rename_default_categories", slug=tenant_a.organization.slug, apply=True)

    with organization_context(tenant_a.organization.id):
        target.refresh_from_db()
        cash_part.refresh_from_db()
        stray.refresh_from_db()
        renamed.refresh_from_db()
        assert target.name == "Maqsadli reklama (target)"
        assert cash_part.name == "Naqd berilgan oylik"
        assert stray.name == "Targetlash"
        assert renamed.name == "Instagram reklama"


def test_running_twice_is_safe(tenant_a: Any):
    with organization_context(tenant_a.organization.id):
        marketing = _category(tenant_a, "Marketing")
        target = _category(tenant_a, "Target", marketing)

    call_command("rename_default_categories", slug=tenant_a.organization.slug, apply=True)
    call_command("rename_default_categories", slug=tenant_a.organization.slug, apply=True)

    with organization_context(tenant_a.organization.id):
        target.refresh_from_db()
        assert target.name == "Maqsadli reklama (target)"
        assert ExpenseCategory.objects.filter(name="Maqsadli reklama (target)").count() == 1


@pytest.mark.tenancy
def test_another_organization_is_untouched(tenant_a: Any, tenant_b: Any):
    with organization_context(tenant_b.organization.id):
        marketing = _category(tenant_b, "Marketing")
        target = _category(tenant_b, "Target", marketing)

    call_command("rename_default_categories", slug=tenant_a.organization.slug, apply=True)

    with organization_context(tenant_b.organization.id):
        target.refresh_from_db()
        assert target.name == "Target"
