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


# Sweep qamray OLMAYDIGAN endpointlar — har biri sabab bilan.
#
# Bu ro'yxat ataylab qo'lda: `model` atributi yo'q ViewSet jimgina
# o'tkazib yuborilsa, kimdir yangi endpoint qo'shib, hech qanday
# izolyatsiya testisiz qolib ketardi. Endi u qo'shilgan kuniyoq sweep
# qizaradi va muallif qaror qabul qilishga majbur bo'ladi: yo `model`
# berish, yo bu yerga sabab yozib, QO'LDA test yozish.
UNCOVERED: dict[str, str] = {
    "permission": "Global katalog — tenant chegarasi yo'q (docs/03 §6.2).",
    "debtor": (
        "Hisoblangan ro'yxat, jadval emas (ADR-7). Qo'lda test: "
        "apps/finance/tests/test_debtors_isolation.py."
    ),
    "setting": "Kalit-qiymat ViewSet, qator emas. Qo'lda test: apps/settings_app/tests.",
    "dashboard": "Agregat, qator emas. Qo'lda test: apps/reports/tests/test_reports.py.",
    "staff-attendance": (
        "Kunlik jurnal va tabel — agregat, qator CRUD emas. Qo'lda test: "
        "apps/attendance/tests/test_staff_attendance.py (begona xodim → 404)."
    ),
    "report": "Agregat, qator emas. Qo'lda test: apps/reports/tests/test_reports.py.",
    "audit-log": "Tashkilot filtri QO'LDA yozilgan. Qo'lda test: apps/audit/tests.",
    "platform": (
        "Vendor tekisligi — mijoz tokeni bu yerga umuman kirmaydi (ADR-10). "
        "Qo'lda test: apps/platform/tests/test_platform_console.py."
    ),
    "billing": (
        "Obuna tokendan aniqlanadi — endpointlar ID qabul qilmaydi. "
        "Qo'lda test: apps/subscriptions/tests/test_billing_api.py."
    ),
}


def _detail_routes() -> list[tuple[str, str]]:
    """Router'dagi har bir ViewSet uchun (basename, prefiks)."""
    routes = []
    for prefix, viewset, basename in router.registry:
        if getattr(viewset, "model", None) is None:
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
    from apps.payroll.services import create_run, record_advance

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
        if basename == "insight":
            from apps.intelligence.models import Insight

            return Insight.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                type="payment_delay",
                severity="warning",
                status="new",
                subject_type="branch",
                subject_id=tenant.branch.id,
                evidence={"children_count": 1},
                recommendation_key="payment_delay.review_debtors",
                deep_link="/debtors?overdue_days=15",
                generated_at=timezone.now(),
            )
        if basename == "cash-account":
            from apps.cash.models import CashAccount, CashAccountKind

            return CashAccount.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                name="Direktor seyfi",
                kind=CashAccountKind.CASH,
            )
        if basename == "bank-statement":
            from apps.cash import services as cash_services
            from apps.cash.models import BankStatement, CashAccount

            cash_services.ensure_branch_accounts(branch=tenant.branch)
            return BankStatement.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                cash_account=CashAccount.objects.get(branch=tenant.branch, kind="bank"),
                file_name="vypiska.xlsx",
            )
        if basename == "money-operation":
            from apps.cash import services as cash_services
            from apps.cash.models import MoneyOperation

            return MoneyOperation.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                kind="loan_in",
                cash_account=cash_services.cash_pot(branch=tenant.branch),
                amount=Decimal("1000"),
                occurred_on=date(2026, 9, 30),
                period_year=2026,
                period_month=9,
                reason="Sinov",
            )
        if basename in {"cash-handover", "cash-count"}:
            from apps.cash import services as cash_services
            from apps.cash.models import CashCount, CashHandover

            pot = cash_services.cash_pot(branch=tenant.branch)
            if basename == "cash-count":
                return CashCount.objects.create(
                    organization=tenant.organization,
                    branch=tenant.branch,
                    cash_account=pot,
                    counted_on=date(2026, 9, 30),
                    system_balance=Decimal("0"),
                    counted=Decimal("0"),
                    difference=Decimal("0"),
                )
            receiver = User.objects.create_user(
                email=f"qabul-{tenant.organization.slug}@test.uz",
                password="Juda-Kuchli-Parol-2026",  # noqa: S106
                full_name="Qabul",
                organization=tenant.organization,
                role=tenant.role("director"),
                branch=tenant.branch,
            )
            return CashHandover.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                cash_account=pot,
                from_user=tenant.owner,
                to_user=receiver,
                amount=Decimal("1000"),
            )
        if basename == "absence-kind":
            from apps.attendance.models_absence import AbsenceKind, RefundMode

            return AbsenceKind.objects.create(
                organization=tenant.organization,
                code="safar",
                name="Safar",
                refund_mode=RefundMode.FULL_RATE,
            )
        if basename in {"absence-claim", "holiday"}:
            from apps.attendance.models_absence import AbsenceClaim, ClaimKind, Holiday

            if basename == "holiday":
                return Holiday.objects.create(
                    organization=tenant.organization,
                    holiday_date=date(2026, 3, 21),
                    name="Navro'z",
                )
            child = Child.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                first_name="Da'vo",
                last_name="Bolasi",
                date_of_birth=date(2021, 3, 14),
                gender="female",
            )
            return AbsenceClaim.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                child=child,
                kind=ClaimKind.MEDICAL,
                date_from=date(2026, 9, 7),
                date_to=date(2026, 9, 11),
            )
        if basename == "position":
            return Position.objects.create(
                organization=tenant.organization, branch=tenant.branch, title="Tarbiyachi"
            )
        if basename in {"employee", "payroll-run", "payroll-advance"}:
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
            if basename == "payroll-advance":
                # Bu test tenant chegarasini sinaydi, pul oqimini emas —
                # shuning uchun boʻsh qopdan chiqim ataylab ruxsat
                # etiladi (ADR-29).
                return record_advance(
                    employee=employee,
                    amount=Decimal("300000"),
                    paid_on=date(2026, 7, 15),
                    allow_negative=True,
                )
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
        # Contracts (PLAN 6.5).
        if basename in {"contract-template", "contract"}:
            from apps.contracts.services import create_contract, save_template

            template = save_template(
                organization=tenant.organization,
                template=None,
                name="Shablon",
                body="{{bola.fio}}",
            )
            if basename == "contract-template":
                return template
            child = Child.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                first_name="Shartnoma",
                last_name="Bolasi",
                date_of_birth=date(2021, 3, 14),
                gender="male",
            )
            return create_contract(child=child, template=template)
        # Kitchen (PLAN 6.6).
        if basename in {"dish", "menu-day"}:
            from apps.kitchen.services import save_dish, set_menu

            warehouse = Warehouse.objects.create(
                organization=tenant.organization, branch=tenant.branch, name="Oshxona"
            )
            product = Product.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                name="Guruch",
                unit="kg",
            )
            dish = save_dish(
                organization=tenant.organization,
                branch=tenant.branch,
                dish=None,
                name="Palov",
                ingredients=[{"product_id": product.id, "quantity": "0.1"}],
            )
            if basename == "dish":
                return dish
            return set_menu(
                organization=tenant.organization,
                branch=tenant.branch,
                menu_date=date(2026, 7, 1),
                warehouse=warehouse,
                items=[{"dish_id": dish.id, "meal": "lunch"}],
            )
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

        # Tekshiruv EGASINING kontekstida: RLS ostida begona qatorni
        # kontekstsiz o'qib bo'lmaydi, va bu to'g'ri — test ham
        # ishlab chiqarish kodi bilan bir xil qoidada yashashi kerak.
        with organization_context(tenant_b.organization.id):
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
        # Lekin filtrsiz manager ham RLS'ni chetlab o'tolmaydi, shuning
        # uchun tekshiruv egasining kontekstida bajariladi.
        with organization_context(tenant_b.organization.id):
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


def test_every_skipped_endpoint_has_a_stated_reason():
    """
    Qamrovdan tashqarida qolgan har bir endpoint ro'yxatda bo'lishi shart.

    Aks holda `model` atributini yozishni unutish "test yo'q" degani
    bo'lardi — va buni hech kim sezmasdi.
    """
    skipped = {
        basename
        for _, viewset, basename in router.registry
        if getattr(viewset, "model", None) is None
    }
    unexplained = skipped - set(UNCOVERED)
    assert not unexplained, (
        f"Bu endpointlar sweep'dan tashqarida, lekin sababi yozilmagan: "
        f"{sorted(unexplained)}. Yo ViewSet'ga `model` bering, yo "
        f"UNCOVERED ga sabab yozib, qo'lda izolyatsiya testi qo'shing."
    )
    stale = set(UNCOVERED) - skipped
    assert not stale, f"UNCOVERED da endi kerak bo'lmagan yozuvlar: {sorted(stale)}"


def test_sweep_actually_covers_something():
    """
    Sweep bo'sh qolib ketmasin.

    Agar router bo'shab qolsa yoki `model` atributi yo'qolsa, yuqoridagi
    parametrizatsiya 0 ta testga aylanadi va hech narsa qizarmaydi — jimgina
    qamrov yo'qolishi eng xavfli holat.
    """
    assert len(ROUTES) >= 3, f"Sweep faqat {len(ROUTES)} ta endpointni qamrayapti"
