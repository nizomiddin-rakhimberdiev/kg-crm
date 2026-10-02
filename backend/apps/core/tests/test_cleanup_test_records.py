"""
2026-09-30 sinov yozuvlarini tozalash (PLAN 5.11).

Uchta xususiyat:

* **dry-run sukut bo'yicha** va u hech narsani o'zgartirmaydi;
* `--apply` hech narsani jimgina o'chirmaydi: pul va ombor
  ledgerlari qarshi yozuv bilan nolga keladi, har bir qadam auditda;
* **faqat** aniq sana + aniq nomlar: boshqa tenantdagi aynan shunday
  yozuvlar ham, boshqa kundagi xuddi shu nomli bola ham tegilmaydi.
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from django.db.models import Sum
from django.utils import timezone

from apps.core.tenancy import organization_context

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]

TEST_MOMENT = timezone.make_aware(datetime.combine(date(2026, 9, 30), time(12, 0)))


def _incident(tenant, *, when=TEST_MOMENT) -> dict:
    """Audit paytida qoldirilgan yozuvlarni aynan qayta yaratadi."""
    from apps.attendance.services import mark_bulk
    from apps.children.models import Child, Group, Guardian
    from apps.children.services import attach_guardian, enroll_child
    from apps.expenses.models import Expense, ExpenseCategory
    from apps.expenses.services import approve_expense
    from apps.finance.models import TariffPlan
    from apps.finance.services import issue_invoice, record_payment
    from apps.inventory.models import Product, ProductCategory, Warehouse
    from apps.inventory.services import record_movement

    org, branch = tenant.organization, tenant.branch
    with organization_context(org.id):
        tariff = TariffPlan.objects.create(
            organization=org, branch=branch, name="Test tarif", amount=Decimal("1500000")
        )
        group = Group.objects.create(organization=org, branch=branch, name="nimadir", capacity=10)
        child = Child.objects.create(
            organization=org,
            branch=branch,
            first_name="Sinov Claude",
            last_name="TEST",
            date_of_birth=date(2022, 1, 1),
            gender="male",
            tariff=tariff,
            enrolled_on=date(2026, 9, 1),
        )
        guardian = Guardian.objects.create(
            organization=org,
            branch=branch,
            first_name="Sinov",
            last_name="TEST-Vasiy",
            phone="+998901112233",
        )
        attach_guardian(child=child, guardian=guardian, relation="mother", is_primary=True)
        enroll_child(child=child, group=group)

        payment = record_payment(child=child, amount=Decimal("200000"), method="cash")
        invoice = issue_invoice(child=child, period_year=2026, period_month=9)
        mark_bulk(
            organization=org,
            branch=branch,
            group=group,
            attendance_date=timezone.localdate(),
            records=[{"child_id": child.id, "status": "present"}],
        )

        warehouse = Warehouse.objects.create(organization=org, branch=branch, name="Ombor")
        pcat = ProductCategory.objects.create(organization=org, branch=branch, name="Oziq")
        product = Product.objects.create(
            organization=org, branch=branch, name="TEST Guruch", category=pcat, unit="kg"
        )
        record_movement(
            product=product,
            warehouse=warehouse,
            movement_type="purchase",
            quantity=Decimal("5"),
            unit_cost=Decimal("14000"),
            create_expense=False,
        )

        category = ExpenseCategory.objects.create(
            organization=org, branch=branch, name="TEST Oziq-ovqat"
        )
        expense = Expense.objects.create(
            organization=org,
            branch=branch,
            category=category,
            amount=Decimal("300000"),
            expense_date=date(2026, 9, 30),
            description="sinov",
        )
        approve_expense(expense=expense, approved_by=tenant.owner)

        for model, pk in (
            (Child, child.id),
            (Guardian, guardian.id),
            (Product, product.id),
            (ExpenseCategory, category.id),
        ):
            model.all_objects.filter(pk=pk).update(created_at=when)

    return {
        "child": child,
        "guardian": guardian,
        "payment": payment,
        "invoice": invoice,
        "product": product,
        "expense": expense,
        "category": category,
    }


def _run(tenant, *args: str) -> str:
    out = StringIO()
    call_command("cleanup_test_records", "--slug", tenant.organization.slug, *args, stdout=out)
    return out.getvalue()


def _state(tenant, rows: dict) -> dict:
    from apps.attendance.models import AttendanceRecord
    from apps.cash.models import CashMovement
    from apps.children.models import Child, Guardian
    from apps.finance.balance import child_balance
    from apps.finance.models import Invoice, Payment
    from apps.inventory.models import StockMovement

    def net(qs):
        totals = {
            d: qs.filter(direction=d).aggregate(s=Sum("amount"))["s"] or 0 for d in ("in", "out")
        }
        return totals["in"] - totals["out"]

    with organization_context(tenant.organization.id):
        child = Child.all_objects.get(pk=rows["child"].id)
        stock = sum(
            (m.signed_quantity for m in StockMovement.objects.filter(product=rows["product"])),
            Decimal("0"),
        )
        return {
            "payment_reversed": Payment.objects.get(pk=rows["payment"].id).reversed_at is not None,
            "invoice_status": Invoice.objects.get(pk=rows["invoice"].id).status,
            "balance": child_balance(child).balance,
            "archived": child.archived_at is not None,
            "guardian_active": Guardian.all_objects.get(pk=rows["guardian"].id).is_active,
            "attendance": AttendanceRecord.objects.filter(child=child).count(),
            "stock": stock,
            "cash_net": net(CashMovement.objects.all()),
        }


def test_dry_run_is_the_default_and_changes_nothing(tenant_a):
    rows = _incident(tenant_a)
    before = _state(tenant_a, rows)
    output = _run(tenant_a)
    assert "[dry-run]" in output
    assert "TEST" in output
    assert _state(tenant_a, rows) == before


def test_apply_corrects_everything_through_counter_entries(tenant_a):
    from apps.audit.models import AuditLog
    from apps.cash.models import CashMovement
    from apps.finance.models import Payment

    rows = _incident(tenant_a)
    with organization_context(tenant_a.organization.id):
        movements_before = CashMovement.objects.count()

    _run(tenant_a, "--apply")
    state = _state(tenant_a, rows)

    assert state["payment_reversed"] is True
    assert state["invoice_status"] == "cancelled"
    assert state["balance"] == Decimal("0")
    assert state["archived"] is True
    assert state["guardian_active"] is False
    assert state["attendance"] == 0
    assert state["stock"] == Decimal("0")
    # Kassa: to'lov kirdi va qaytdi, chiqim chiqdi va qaytdi — sof nol.
    assert state["cash_net"] == 0

    with organization_context(tenant_a.organization.id):
        # Append-only: asl qatorlar JOYIDA, ustiga qarshi yozuv qo'shildi.
        assert Payment.objects.filter(pk=rows["payment"].id).exists()
        assert CashMovement.objects.count() > movements_before
        audit = AuditLog.objects.filter(actor_email="system:cleanup_test_records")
        assert audit.count() >= 7
        assert all("PLAN 5.11" in row.changes.get("reason", "") for row in audit)


def test_only_the_exact_records_are_touched(tenant_a, tenant_b):
    """
    Boshqa tenantda AYNAN shunday yozuvlar va shu tenantda BOSHQA kundagi
    xuddi shu nomli bola — ikkalasi ham tegilmasligi kerak.
    """
    target = _incident(tenant_a)
    elsewhere = _incident(tenant_b)
    other_before = _state(tenant_b, elsewhere)

    _run(tenant_a, "--apply")

    assert _state(tenant_a, target)["archived"] is True
    assert _state(tenant_b, elsewhere) == other_before


def test_another_day_is_not_matched(tenant_a):
    rows = _incident(tenant_a, when=TEST_MOMENT.replace(day=29))
    before = _state(tenant_a, rows)
    output = _run(tenant_a, "--apply")
    assert "topilmadi" in output
    assert _state(tenant_a, rows) == before
