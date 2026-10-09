"""
Tashkilot maʼlumotini nolga qaytarish (PLAN 11.2).

Ikki savol muhim: **nima ketdi** va **nima qoldi**. Ikkinchisi
birinchisidan muhimroq — mijoz tizimga qayta kira olmay qolsa, bu
tozalash emas, yoʻqotish boʻladi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from io import StringIO
from typing import Any

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.core.tenancy import organization_context

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]


def _seed(tenant: Any) -> None:
    """Mijoz kiritadigan narsalardan bir nechtasi."""
    from apps.cash.models import CashAccount
    from apps.children.models import Child
    from apps.expenses.models import Expense, ExpenseCategory
    from apps.expenses.services import approve_expense
    from apps.hr.models import Employee

    tenant.fund(kind="all")
    with organization_context(tenant.organization.id):
        Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Diyor",
            last_name="Abdullayev",
            date_of_birth=date(2021, 1, 12),
            gender="male",
        )
        Employee.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Nilufar",
            last_name="Karimova",
            hire_date=date(2025, 9, 1),
            base_salary=Decimal("4000000"),
        )
        category = ExpenseCategory.objects.create(
            organization=tenant.organization, branch=tenant.branch, name="Kommunal"
        )
        expense = Expense.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            category=category,
            amount=Decimal("500000"),
            expense_date=date(2026, 10, 1),
            description="Elektr",
        )
        approve_expense(expense=expense, approved_by=tenant.owner)
        assert CashAccount.objects.filter(branch=tenant.branch).exists()


def _absence_claim(tenant: Any) -> None:
    """
    Tasdiqlangan ishdan chiqish daʼvosi — jonli bazadagi holat.

    `absence_claim.applied_invoice` hisob-fakturaga `RESTRICT` bilan
    bogʻlangan, yaʼni daʼvo undan OLDIN oʻchishi kerak. Oʻchirish
    tartibida u hisob-fakturadan KEYIN turardi va buni hech narsa
    koʻrsatmadi — chunki birorta testda tasdiqlangan daʼvo yoʻq edi.
    Jonli bazada esa bitta shunday daʼvo butun tozalashni yiqitdi.
    """
    from apps.attendance.services_absence import approve_claim, create_claim
    from apps.children.models import Child
    from apps.finance import services as finance
    from apps.finance.models import TariffPlan

    with organization_context(tenant.organization.id):
        child = Child.objects.first()
        assert child is not None
        child.tariff = TariffPlan.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            name="Toʻliq kun",
            amount=Decimal("1500000"),
        )
        child.save(update_fields=["tariff"])
        finance.issue_invoice(child=child, period_year=2026, period_month=10)
        claim = create_claim(
            child=child,
            kind="sick",
            date_from=date(2026, 10, 13),
            date_to=date(2026, 10, 16),
            note="Kasallik",
            created_by=tenant.owner,
        )
        # Tasdiqlashning oʻzi daʼvoni shu oyning toʻlanmagan
        # fakturasiga qoʻllaydi (PLAN 7.7). Bizga aynan SHU holat
        # kerak: `applied_invoice` toʻlgandagina `RESTRICT` ishga
        # tushadi va jonli bazadagi nosozlik qaytariladi.
        approve_claim(claim=claim, approved_by=tenant.owner)
        claim.refresh_from_db()
        assert claim.applied_invoice_id is not None


def _run(tenant: Any, *args: str) -> str:
    out = StringIO()
    call_command("reset_organization_data", "--slug", tenant.organization.slug, *args, stdout=out)
    return out.getvalue()


def test_dry_run_is_the_default_and_deletes_nothing(tenant_a: Any):
    from apps.children.models import Child

    _seed(tenant_a)
    output = _run(tenant_a)

    assert "dry-run" in output
    with organization_context(tenant_a.organization.id):
        assert Child.objects.count() == 1


def test_apply_requires_the_slug_to_be_typed_again(tenant_a: Any):
    _seed(tenant_a)
    with pytest.raises(CommandError):
        _run(tenant_a, "--apply")
    with pytest.raises(CommandError):
        _run(tenant_a, "--confirm", "boshqa-slug", "--apply")


def test_apply_clears_the_data_the_customer_entered(tenant_a: Any):
    from apps.attendance.models_absence import AbsenceClaim
    from apps.cash.models import CashMovement
    from apps.children.models import Child
    from apps.expenses.models import Expense
    from apps.finance.models import Invoice
    from apps.hr.models import Employee

    _seed(tenant_a)
    _absence_claim(tenant_a)
    _run(tenant_a, "--confirm", tenant_a.organization.slug, "--apply")

    with organization_context(tenant_a.organization.id):
        assert Child.objects.count() == 0
        assert Employee.objects.count() == 0
        assert Expense.objects.count() == 0
        assert CashMovement.objects.count() == 0
        assert Invoice.objects.count() == 0
        assert AbsenceClaim.objects.count() == 0


def test_the_customer_can_still_log_in_afterwards(tenant_a: Any):
    """
    Eng muhim tekshiruv: tozalash — yoʻqotish emas.

    Kirish, filial, rollar, obuna va roʻyxatdan oʻtishda ochilgan
    kassa qoplari joyida qoladi, aks holda mijoz boʻsh tizimga ham
    kira olmasdi.
    """
    from apps.accounts.models import Role, User
    from apps.branches.models import Branch
    from apps.cash.models import CashAccount
    from apps.notifications.models import NotificationTemplate
    from apps.subscriptions.models import Subscription

    _seed(tenant_a)
    _run(tenant_a, "--confirm", tenant_a.organization.slug, "--apply")

    with organization_context(tenant_a.organization.id):
        assert User.objects.filter(pk=tenant_a.owner.id).exists()
        assert Role.objects.exists()
        assert Branch.objects.filter(pk=tenant_a.branch.id).exists()
        assert CashAccount.objects.filter(branch=tenant_a.branch).count() == 4
        assert NotificationTemplate.objects.exists()
        assert Subscription.objects.filter(organization=tenant_a.organization).exists()

    # Va haqiqatan kira oladi.
    response = tenant_a.client().get("/api/v1/children")
    assert response.status_code == 200
    assert response.json()["data"] == []


def test_the_open_session_keeps_working(tenant_a: Any):
    """
    Tozalash — tizimdan chiqarish emas.

    Mijoz boʻsh tizimni oʻsha oynada koʻrishi kerak; qaytadan parol
    terish "nimadir buzildi" degan taassurot qoldiradi.
    """
    from apps.accounts.models import RefreshToken

    _seed(tenant_a)
    with organization_context(tenant_a.organization.id):
        before = RefreshToken.objects.filter(user=tenant_a.owner).count()
    client = tenant_a.client()  # seans tozalashdan OLDIN ochiladi

    _run(tenant_a, "--confirm", tenant_a.organization.slug, "--apply")

    with organization_context(tenant_a.organization.id):
        assert RefreshToken.objects.filter(user=tenant_a.owner).count() == before
    assert client.get("/api/v1/children").status_code == 200


def test_another_organization_is_not_touched(tenant_a: Any, tenant_b: Any):
    from apps.children.models import Child

    _seed(tenant_a)
    _seed(tenant_b)
    _run(tenant_a, "--confirm", tenant_a.organization.slug, "--apply")

    with organization_context(tenant_b.organization.id):
        assert Child.objects.count() == 1
