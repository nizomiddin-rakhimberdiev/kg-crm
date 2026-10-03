"""
Hisobot va boshqaruv paneli — ROL bo'yicha ko'rinish (docs/02 §11.2).

Nega alohida test: `reports.read` bitta ruxsat bo'lib, u BARCHA hisobotni
ochib yuborardi. Jadvalda esa Kassir uchun "R (finance only)", Davomat
menejeri uchun "R (attendance only)" deb yozilgan — ya'ni tarbiyachi
bog'chaning tushumini va foyda-zararini (ichida oylik maosh) o'qiy olardi.
Xuddi shunday, `GET /dashboard` har bir rolga pul ko'rsatkichlarini
qaytarardi. Ikkalasi ham rol ta'rifidagi "No finance" bilan ziddiyatda edi.
"""

from __future__ import annotations

from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.accounts.authentication import issue_token_pair
from apps.accounts.models import User
from apps.core.tenancy import organization_context

pytestmark = pytest.mark.django_db

MONEY_KEYS = {"month_revenue", "outstanding_debt", "debtor_count", "recent_payments"}


def _client_for(tenant: Any, role_code: str, email: str) -> APIClient:
    """Berilgan roldagi foydalanuvchi uchun autentifikatsiya qilingan klient."""
    with organization_context(tenant.organization.id):
        user = User.objects.create_user(
            email=email,
            password="Juda-Kuchli-Parol-2026",  # noqa: S106 — test ma'lumoti
            full_name="Xodim",
            organization=tenant.organization,
            role=tenant.role(role_code),
            branch=tenant.branch,
        )
        tokens = issue_token_pair(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


# --- Hisobotlar ---


@pytest.mark.parametrize(
    ("role_code", "allowed", "denied"),
    [
        (
            "attendance_manager",
            ["attendance"],
            ["revenue", "profit-loss", "payroll", "debtors", "expenses"],
        ),
        (
            "cashier",
            ["revenue", "debtors", "expenses"],
            ["payroll", "profit-loss", "attendance"],
        ),
        ("director", ["revenue", "profit-loss", "payroll", "attendance", "expenses"], []),
    ],
)
def test_report_visibility_matches_matrix(
    tenant_a: Any, role_code: str, allowed: list[str], denied: list[str]
):
    client = _client_for(tenant_a, role_code, f"{role_code}@alfa.uz")
    for report in allowed:
        assert client.get(f"/api/v1/reports/{report}").status_code == 200, report
    for report in denied:
        assert client.get(f"/api/v1/reports/{report}").status_code == 403, report


def test_owner_sees_every_report(tenant_a: Any):
    client = tenant_a.client()
    for report in ("revenue", "expenses", "payroll", "attendance", "debtors", "profit-loss"):
        assert client.get(f"/api/v1/reports/{report}").status_code == 200, report


def test_export_of_a_forbidden_report_is_refused(tenant_a: Any):
    """
    Eksport ruxsat matritsasidan chetlab o'tadigan yo'l BO'LMASIN.

    Tizim rollarida `reports.export` faqat egasi va direktorda bor, ya'ni
    bu qatlam odatda ko'rinmaydi. Ammo egasi uni istalgan rolga bera oladi
    (docs/02 §11.2 — matritsa boshlang'ich holat, qat'iy chegara emas), va
    o'shanda mavzu ruxsati baribir tekshirilishi kerak.
    """
    from apps.accounts.models import Permission, Role, RolePermission

    with organization_context(tenant_a.organization.id):
        role = Role.objects.get(code="attendance_manager")
        RolePermission.objects.create(
            role=role, permission=Permission.objects.get(code="reports.export")
        )

    client = _client_for(tenant_a, "attendance_manager", "att-export@alfa.uz")
    assert client.post("/api/v1/reports/payroll/export", {}, format="json").status_code == 403
    assert client.post("/api/v1/reports/attendance/export", {}, format="json").status_code == 202


def test_finished_export_is_guarded_by_its_own_topic(tenant_a: Any):
    """Egasi yaratgan oylik maosh faylini tarbiyachi yuklab ololmaydi."""
    owner = tenant_a.client()
    created = owner.post("/api/v1/reports/payroll/export", {}, format="json")
    job_id = created.json()["data"]["id"]

    teacher = _client_for(tenant_a, "attendance_manager", "att-download@alfa.uz")
    assert teacher.get(f"/api/v1/reports/exports/{job_id}").status_code == 404
    assert teacher.get(f"/api/v1/reports/exports/{job_id}/download").status_code == 404
    # Ro'yxatda ham ko'rinmaydi.
    listed = teacher.get("/api/v1/reports/exports").json()["data"]
    assert all(row["report_type"] != "payroll" for row in listed)


# --- Boshqaruv paneli ---


def test_dashboard_hides_money_from_attendance_manager(tenant_a: Any):
    client = _client_for(tenant_a, "attendance_manager", "att-dash@alfa.uz")
    data = client.get("/api/v1/dashboard").json()["data"]
    assert data["active_children"] is not None
    assert MONEY_KEYS.isdisjoint(data.keys()), sorted(set(data) & MONEY_KEYS)


@pytest.mark.parametrize("role_code", ["cashier", "director", "manager"])
def test_dashboard_keeps_money_for_finance_roles(tenant_a: Any, role_code: str):
    client = _client_for(tenant_a, role_code, f"{role_code}-dash@alfa.uz")
    data = client.get("/api/v1/dashboard").json()["data"]
    assert MONEY_KEYS.issubset(data.keys()), role_code


def test_dashboard_cache_does_not_leak_between_roles(tenant_a: Any):
    """
    Kesh kaliti moliya bayrog'ini o'z ichiga oladi.

    Usiz: egasi panelni ochadi → to'liq javob keshlanadi → tarbiyachi
    ochadi → o'sha keshdan pul bilan javob oladi.
    """
    assert MONEY_KEYS.issubset(tenant_a.client().get("/api/v1/dashboard").json()["data"].keys())
    teacher = _client_for(tenant_a, "attendance_manager", "att-cache@alfa.uz")
    assert MONEY_KEYS.isdisjoint(teacher.get("/api/v1/dashboard").json()["data"].keys())


def test_every_dashboard_block_has_its_own_permission(tenant_a: Any):
    """
    Boshqaruv paneli — boshqa joyda ko'rsa bo'ladigan ma'lumotning
    qisqartmasi, YANGI kirish yo'li emas.

    Kassirda `attendance` ruxsati yo'q, shuning uchun davomat foizi ham
    javobda bo'lmasligi kerak — ilgari u har kimga ketardi.
    """
    cashier = (
        _client_for(tenant_a, "cashier", "cashier-blocks@alfa.uz")
        .get("/api/v1/dashboard")
        .json()["data"]
    )
    assert "attendance_month_pct" not in cashier
    assert "low_stock_count" not in cashier
    assert "active_children" in cashier  # `children: R` — matritsada bor

    teacher = (
        _client_for(tenant_a, "attendance_manager", "att-blocks@alfa.uz")
        .get("/api/v1/dashboard")
        .json()["data"]
    )
    assert "attendance_month_pct" in teacher


def test_cash_balance_needs_all_three_permissions(tenant_a: Any):
    """
    Kassa qoldig'i tushum, chiqim va oylikni BITTA raqamga yig'adi.

    Ya'ni uchtasidan biriga ruxsati yo'q odam qolganini undan chiqarib
    olardi: masalan kassir tushum va chiqimni biladi, qoldiqdan esa
    bog'chaning butun oylik fondi kelib chiqardi.
    """
    assert "cash" in tenant_a.client().get("/api/v1/dashboard").json()["data"]

    for role_code in ("cashier", "manager", "attendance_manager"):
        data = (
            _client_for(tenant_a, role_code, f"{role_code}-cash@alfa.uz")
            .get("/api/v1/dashboard")
            .json()["data"]
        )
        assert "cash" not in data, role_code


class TestBranchScope:
    """
    Filialga bog'langan xodim hisobotda faqat O'Z filialini ko'radi —
    Dashboard bilan bir xil qoida. Avval `?branch=` bo'lmasa butun
    tashkilot qaytardi (Paddington: MAIN menejeri Gorkiy tushumini ko'rardi).
    """

    def _pay(self, tenant: Any, branch: Any, amount: str) -> None:
        from datetime import date
        from decimal import Decimal

        from apps.children.models import Child
        from apps.finance import services as finance

        with organization_context(tenant.organization.id):
            child = Child.objects.create(
                organization=tenant.organization,
                branch=branch,
                first_name="Bola",
                last_name=branch.name,
                date_of_birth=date(2021, 3, 14),
                gender="male",
            )
            finance.record_payment(child=child, amount=Decimal(amount), method="cash")

    def test_branch_bound_reader_sees_only_her_branch(self, tenant_a: Any) -> None:
        from apps.branches.models import Branch

        with organization_context(tenant_a.organization.id):
            gorkiy = Branch.objects.create(
                organization=tenant_a.organization, name="Gorkiy", code="SECOND"
            )
        self._pay(tenant_a, tenant_a.branch, "100000")
        self._pay(tenant_a, gorkiy, "900000")

        cashier = _client_for(tenant_a, "cashier", "kassir-scope@alfa.uz")
        own = cashier.get("/api/v1/reports/revenue").json()["data"]["total"]
        # Boshqa filialni so'rasa ham — o'zinikini oladi.
        asked = cashier.get("/api/v1/reports/revenue", {"branch": str(gorkiy.id)})
        assert own == "100000.00"
        assert asked.json()["data"]["total"] == "100000.00"

        owner_all = tenant_a.client().get("/api/v1/reports/revenue").json()["data"]["total"]
        owner_gorkiy = (
            tenant_a.client()
            .get("/api/v1/reports/revenue", {"branch": str(gorkiy.id)})
            .json()["data"]["total"]
        )
        assert owner_all == "1000000.00"
        assert owner_gorkiy == "900000.00"
