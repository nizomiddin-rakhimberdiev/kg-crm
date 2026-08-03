"""
Cross-tenant sweep — router bo'ylab AVTOMATIK izolyatsiya testi.

docs/06 §8: "Run as a parametrized sweep over the router, so a new endpoint
is covered the day it is added rather than when someone remembers."

Qo'lda yozilgan per-endpoint testlar muddat siqiganda o'tkazib yuboriladi —
va aynan o'tkazib yuborilgani sizib chiqadi. Shuning uchun bu fayl endpoint
ro'yxatini **router'dan** oladi: Sprint 2 da `/children` qo'shilsa, u
qo'shilgan kuniyoq shu yerda tekshiriladi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.urls import reverse
from django.utils import timezone

from api.v1.router import router
from apps.core.tenancy import organization_context

pytestmark = [pytest.mark.django_db, pytest.mark.tenancy]


def _detail_routes() -> list[tuple[str, str]]:
    """Router'dagi har bir ViewSet uchun (basename, model nomi)."""
    routes = []
    for prefix, viewset, basename in router.registry:
        model = getattr(viewset, "model", None)
        if model is None:
            # `Permission` kabi tenant-scoped bo'lmagan global kataloglar
            # (docs/03 §6.2) — ularda tenant chegarasi yo'q.
            continue
        routes.append((basename, prefix))
    return routes


ROUTES = _detail_routes()


def _snapshot(instance: Any) -> dict[str, Any]:
    """Qatorning barcha oddiy maydonlari — o'zgarganini aniqlash uchun."""
    return {
        field.name: getattr(instance, field.attname)
        for field in instance._meta.fields
        if field.name != "updated_at"
    }


def _create_row(tenant: Any, basename: str) -> Any:
    """Berilgan tenant ichida shu endpoint uchun bitta qator yaratadi."""
    from apps.accounts.models import User
    from apps.attendance.models import AttendanceRecord
    from apps.branches.models import Branch
    from apps.children.models import Child, Group, Guardian
    from apps.children.services import enroll_child
    from apps.expenses.models import Expense, ExpenseCategory
    from apps.finance.models import Discount, TariffPlan
    from apps.finance.services import issue_invoice, record_payment
    from apps.hr.models import Employee, Position
    from apps.inventory.models import (
        Product,
        ProductCategory,
        Supplier,
        Warehouse,
    )
    from apps.inventory.services import record_movement
    from apps.notifications.models import NotificationTemplate
    from apps.notifications.services import queue_notification
    from apps.payroll.services import create_run

    with organization_context(tenant.organization.id):
        if basename == "user":
            return User.objects.create_user(
                email=f"xodim@{tenant.organization.slug}.uz",
                password="Juda-Kuchli-Parol-2026",  # noqa: S106
                full_name="Xodim",
                organization=tenant.organization,
                role=tenant.role("cashier"),
                branch=tenant.branch,
            )
        if basename == "role":
            return tenant.role("cashier")
        if basename == "branch":
            return Branch.objects.create(
                organization=tenant.organization, name="Ikkinchi", code="B2"
            )
        if basename == "child":
            return Child.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                first_name="Ali",
                last_name="Valiyev",
                date_of_birth=date(2021, 3, 14),
                gender="male",
            )
        if basename == "guardian":
            return Guardian.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                first_name="Ona",
                last_name="Valiyeva",
                phone=f"+99890{abs(hash(tenant.organization.slug)) % 10_000_000:07d}",
            )
        if basename == "group":
            return Group.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                name="Quyoshlar",
                capacity=20,
            )
        if basename == "attendance":
            group = Group.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                name="Davomat guruhi",
                capacity=20,
            )
            child = Child.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                first_name="Davomat",
                last_name="Bolasi",
                date_of_birth=date(2021, 3, 14),
                gender="male",
            )
            enroll_child(child=child, group=group)
            return AttendanceRecord.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                child=child,
                group=group,
                attendance_date=timezone.localdate(),
                status="present",
            )
        if basename == "notification-template":
            return NotificationTemplate.objects.create(
                organization=tenant.organization,
                code="custom",
                channel="sms",
                body="Test",
            )
        if basename == "notification":
            from apps.children.models import Guardian

            guardian = Guardian.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                first_name="Vasiy",
                last_name="Testov",
                phone=f"+99890{abs(hash(tenant.organization.slug)) % 10_000_000:07d}",
            )
            return queue_notification(
                organization=tenant.organization,
                branch=tenant.branch,
                guardian=guardian,
                code="debt_reminder",
            )
        if basename == "warehouse":
            return Warehouse.objects.create(
                organization=tenant.organization, branch=tenant.branch, name="Ombor"
            )
        if basename == "product-category":
            return ProductCategory.objects.create(
                organization=tenant.organization, branch=tenant.branch, name="Sabzavot"
            )
        if basename == "supplier":
            return Supplier.objects.create(
                organization=tenant.organization, branch=tenant.branch, name="Yetkazuvchi"
            )
        if basename in {"product", "stock-movement"}:
            item = Product.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                name="Kartoshka",
                unit="kg",
            )
            if basename == "product":
                return item
            store = Warehouse.objects.create(
                organization=tenant.organization, branch=tenant.branch, name="Harakat ombori"
            )
            return record_movement(
                product=item,
                warehouse=store,
                movement_type="purchase",
                quantity=Decimal("10"),
            )
        if basename in {"expense-category", "expense"}:
            category = ExpenseCategory.objects.create(
                organization=tenant.organization, branch=tenant.branch, name="Kommunal"
            )
            if basename == "expense-category":
                return category
            return Expense.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                category=category,
                amount=Decimal("100000"),
                expense_date=date(2026, 7, 1),
            )
        if basename == "position":
            return Position.objects.create(
                organization=tenant.organization, branch=tenant.branch, title="Tarbiyachi"
            )
        if basename in {"employee", "payroll-run"}:
            employee = Employee.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                first_name="Xodim",
                last_name="Testov",
                hire_date=date(2024, 1, 1),
                base_salary=Decimal("4000000"),
            )
            if basename == "employee":
                return employee
            return create_run(
                organization=tenant.organization,
                branch=tenant.branch,
                period_year=2026,
                period_month=7,
            )
        if basename in {"tariff", "discount", "invoice", "ledger", "payment"}:
            tariff = TariffPlan.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                name="Tarif",
                amount=Decimal("1000000"),
            )
            if basename == "tariff":
                return tariff
            child = Child.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                first_name="Moliya",
                last_name="Bolasi",
                date_of_birth=date(2021, 3, 14),
                gender="male",
                tariff=tariff,
            )
            if basename == "discount":
                return Discount.objects.create(
                    organization=tenant.organization,
                    branch=tenant.branch,
                    child=child,
                    discount_type="percent",
                    value=Decimal("10"),
                    valid_from=date(2026, 1, 1),
                )
            invoice = issue_invoice(child=child, period_year=2026, period_month=7)
            if basename == "invoice":
                return invoice
            if basename == "payment":
                return record_payment(
                    child=child, amount=Decimal("100000"), method="cash", invoice=invoice
                )
            return child.ledger_entries.first()
    raise AssertionError(
        f"'{basename}' uchun test ma'lumoti yaratilmagan. Yangi endpoint "
        f"qo'shgan bo'lsangiz, bu funksiyaga uni ham qo'shing — sweep "
        f"jimgina o'tkazib yubormaydi."
    )


@pytest.mark.parametrize("basename,prefix", ROUTES, ids=[r[1] for r in ROUTES])
class TestCrossTenantIsolation:
    """Har bir ro'yxatdan o'tgan endpoint uchun bir xil to'rtta tekshiruv."""

    def test_list_excludes_other_tenant_rows(self, tenant_a, tenant_b, basename, prefix):
        foreign = _create_row(tenant_b, basename)
        response = tenant_a.client().get(reverse(f"v1:{basename}-list"))
        assert response.status_code == 200

        body = response.json()
        ids = {row["id"] for row in body["data"]}
        assert str(foreign.id) not in ids, (
            f"/{prefix} ro'yxati boshqa tashkilotning qatorini qaytardi"
        )

    def test_retrieve_of_other_tenant_row_is_404(self, tenant_a, tenant_b, basename, prefix):
        """
        403 EMAS, 404.

        403 qator mavjudligini tasdiqlardi — ya'ni boshqa mijozda o'sha ID
        borligini oshkor qilardi (docs/04 §2).
        """
        foreign = _create_row(tenant_b, basename)
        response = tenant_a.client().get(reverse(f"v1:{basename}-detail", args=[foreign.id]))
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOT_FOUND"

    def test_update_of_other_tenant_row_is_blocked(self, tenant_a, tenant_b, basename, prefix):
        """
        `404` (topilmadi) yoki `405` (metod yo'q) — ikkalasi ham xavfsiz.

        Faqat o'qish uchun mo'ljallangan resurslarda (hisob-faktura va
        ledger — D3) `PATCH` umuman mavjud emas. Muhimi status kodi emas,
        **begona qator o'zgarmagani** — quyida aynan shu tekshiriladi.
        """
        foreign = _create_row(tenant_b, basename)
        before = _snapshot(foreign)

        response = tenant_a.client().patch(
            reverse(f"v1:{basename}-detail", args=[foreign.id]),
            {"name": "buzildi"},
            format="json",
        )
        assert response.status_code in (404, 405)

        foreign.refresh_from_db()
        assert _snapshot(foreign) == before, "Begona tashkilotning qatori o'zgardi"

    def test_delete_of_other_tenant_row_is_blocked(self, tenant_a, tenant_b, basename, prefix):
        foreign = _create_row(tenant_b, basename)
        model = type(foreign)

        response = tenant_a.client().delete(reverse(f"v1:{basename}-detail", args=[foreign.id]))
        assert response.status_code in (404, 405)

        # Qator o'chirilmagani VA yumshoq o'chirilmagani — ikkalasi ham.
        # Filtrsiz manager nomi modelga qarab farq qiladi: `User` da u
        # `auth_objects` (login tenant tanlanishidan oldin ishlaydi).
        unscoped = getattr(model, "all_objects", None) or model.auth_objects
        still_there = unscoped.filter(pk=foreign.pk).first()
        assert still_there is not None, "Begona tashkilotning qatori o'chirildi"
        if hasattr(still_there, "is_active"):
            assert still_there.is_active is True


@pytest.mark.parametrize("basename,prefix", ROUTES, ids=[r[1] for r in ROUTES])
def test_endpoint_requires_authentication(api_client, basename, prefix):
    """P5 — deny-by-default: tokensiz hech bir endpoint ochilmaydi."""
    response = api_client.get(reverse(f"v1:{basename}-list"))
    assert response.status_code == 401


def test_sweep_actually_covers_something():
    """
    Sweep bo'sh qolib ketmasin.

    Agar router bo'shab qolsa yoki `model` atributi yo'qolsa, yuqoridagi
    parametrizatsiya 0 ta testga aylanadi va hech narsa qizarmaydi — jimgina
    qamrov yo'qolishi eng xavfli holat.
    """
    assert len(ROUTES) >= 3, f"Sweep faqat {len(ROUTES)} ta endpointni qamrayapti"
