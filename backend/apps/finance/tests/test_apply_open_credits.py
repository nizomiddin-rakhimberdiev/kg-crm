"""
`apply_open_credits` buyrug'i — PLAN 1.2 (mavjud ma'lumot uchun).

Bu buyruq mijozning moliyaviy raqamlarini o'zgartiradi, shuning uchun
undan talab qilinadigan uchta narsa test bilan qo'riqlanadi:
  * `--dry-run` HECH NARSA yozmaydi;
  * `--tenant` majburiy va faqat o'sha tashkilotga tegadi;
  * qo'llangandan keyin balans o'zgarmaydi — faqat pul qayerga
    tegishli ekani aniqlanadi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import balance, services
from apps.finance.models import Invoice, PaymentAllocation, TariffPlan

pytestmark = pytest.mark.django_db

TARIFF = Decimal("1500000.00")


def _setup(tenant) -> Child:
    """Auditdagi Ibragimov Robiya holati: faktura bor, pul avans bo'lib yotibdi."""
    with organization_context(tenant.organization.id):
        tariff = TariffPlan.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            name="To'liq kun",
            amount=TARIFF,
        )
        child = Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Robiya",
            last_name="Ibragimova",
            date_of_birth=date(2021, 3, 14),
            gender="female",
            tariff=tariff,
        )
        invoice = services.issue_invoice(child=child, period_year=2026, period_month=9)
        # Taqsimotdan OLDIN yozilgan to'lovni taqlid qilamiz: pul bor,
        # lekin u hech qaysi hujjatga biriktirilmagan.
        payment = services.record_payment(child=child, amount=Decimal("830000"), method="cash")
        PaymentAllocation.objects.filter(payment=payment).delete()
        Invoice.objects.filter(pk=invoice.pk).update(amount_paid=Decimal("0"), status="issued")
    return child


def _run(tenant_slug: str, *flags: str) -> str:
    out = StringIO()
    call_command("apply_open_credits", "--tenant", tenant_slug, *flags, stdout=out)
    return out.getvalue()


class TestDryRun:
    def test_dry_run_writes_nothing(self, tenant_a):
        child = _setup(tenant_a)
        output = _run(tenant_a.organization.slug, "--dry-run")

        with organization_context(tenant_a.organization.id):
            invoice = Invoice.objects.get(child=child)
            assert invoice.amount_paid == Decimal("0.00")
            assert balance.child_balance(child).advance == Decimal("830000.00")

        assert "DRY-RUN" in output
        assert "Ibragimova Robiya" in output
        assert "830,000.00" in output


class TestApply:
    def test_the_advance_lands_on_the_invoice(self, tenant_a):
        child = _setup(tenant_a)
        _run(tenant_a.organization.slug)

        with organization_context(tenant_a.organization.id):
            invoice = Invoice.objects.get(child=child)
            detail = balance.child_balance(child)

        assert invoice.amount_paid == Decimal("830000.00")
        assert detail.advance == Decimal("0.00")

    def test_the_balance_does_not_move(self, tenant_a):
        """
        Buyruq pulni YARATMAYDI va yo'q qilmaydi — faqat uning qayerga
        tegishli ekanini aniqlaydi. Balans shuning uchun o'zgarmaydi.
        """
        child = _setup(tenant_a)
        with organization_context(tenant_a.organization.id):
            before = balance.child_balance(child).balance

        _run(tenant_a.organization.slug)

        with organization_context(tenant_a.organization.id):
            assert balance.child_balance(child).balance == before

    def test_running_twice_changes_nothing(self, tenant_a):
        child = _setup(tenant_a)
        _run(tenant_a.organization.slug)
        _run(tenant_a.organization.slug)

        with organization_context(tenant_a.organization.id):
            invoice = Invoice.objects.get(child=child)
            assert invoice.amount_paid == Decimal("830000.00")
            assert (
                PaymentAllocation.objects.filter(invoice=invoice, released_at__isnull=True).count()
                == 1
            )


class TestScope:
    def test_another_tenant_is_untouched(self, tenant_a, tenant_b):
        mine = _setup(tenant_a)
        theirs = _setup(tenant_b)

        _run(tenant_a.organization.slug)

        with organization_context(tenant_b.organization.id):
            assert Invoice.objects.get(child=theirs).amount_paid == Decimal("0.00")
        with organization_context(tenant_a.organization.id):
            assert Invoice.objects.get(child=mine).amount_paid == Decimal("830000.00")

    def test_an_unknown_tenant_is_an_error(self, tenant_a):
        with pytest.raises(CommandError, match="topilmadi"):
            _run("yo-q-bogcha")
