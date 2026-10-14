"""
Kassir faqat oʻzi qabul qilgan pulni koʻradi (mijoz soʻrovi, 2026-10-14).

Mijozning soʻzi: *"kassir hammasini koʻrib turishi bu xato, unga
faqatgina oʻzi qabul qilgan pullarning hisob-kitobi koʻrinsin — qachon
qancha summa qabul qilgani; chiqimlar, umumiy tushum, oylik maosh va
sof natija koʻrinishi kerak emas"*.

Cheklov rolning ANIQ bayrogʻidan kelib chiqadi (`payments_own_only`),
ruxsat yoʻqligidan emas — 14-invariant. Shuning uchun bayroq qoʻyilmagan
har qanday rol, jumladan oʻzi yasalgan rollar, avvalgidek hammasini
koʻradi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from io import StringIO
from typing import Any

import pytest
from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.authentication import issue_token_pair
from apps.accounts.models import Role, User
from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import services as finance

pytestmark = pytest.mark.django_db


def _child(tenant: Any, name: str = "Ali") -> Child:
    with organization_context(tenant.organization.id):
        return Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name=name,
            last_name="Valiyev",
            date_of_birth=date(2021, 3, 14),
            gender="male",
        )


def _user(tenant: Any, email: str, role: Role) -> User:
    with organization_context(tenant.organization.id):
        return User.objects.create_user(
            email=email,
            password="Juda-Kuchli-Parol-2026",  # noqa: S106
            full_name=email.split("@")[0],
            organization=tenant.organization,
            role=role,
            branch=tenant.branch,
        )


def _client(tenant: Any, user: User) -> APIClient:
    with organization_context(tenant.organization.id):
        tokens = issue_token_pair(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


def _pay(tenant: Any, child: Child, amount: str, by: User) -> Any:
    with organization_context(tenant.organization.id):
        return finance.record_payment(
            child=child, amount=Decimal(amount), method="cash", received_by=by
        )


def _rows(response: Any) -> list[dict[str, Any]]:
    body = response.json()
    data = body.get("data", body)
    return data["results"] if isinstance(data, dict) and "results" in data else data


def _data(response: Any) -> dict[str, Any]:
    body = response.json()
    return body.get("data", body)


@pytest.fixture
def desk(tenant_a: Any) -> dict[str, Any]:
    """Ikki kassir va direktor, har biri bittadan toʻlov olgan."""
    cashier = _user(tenant_a, "kassir1@alfa.uz", tenant_a.role("cashier"))
    other = _user(tenant_a, "kassir2@alfa.uz", tenant_a.role("cashier"))
    director = _user(tenant_a, "direktor@alfa.uz", tenant_a.role("director"))
    child = _child(tenant_a)
    mine = _pay(tenant_a, child, "300000", cashier)
    theirs = _pay(tenant_a, child, "700000", other)
    return {
        "cashier": cashier,
        "other": other,
        "director": director,
        "mine": mine,
        "theirs": theirs,
    }


# --- Rol bayrogʻi ---


def test_the_system_cashier_role_is_born_own_only(tenant_a: Any):
    assert tenant_a.role("cashier").payments_own_only is True
    for code in ("org_owner", "director", "manager", "attendance_manager"):
        assert tenant_a.role(code).payments_own_only is False


def test_the_cashier_role_no_longer_reads_reports_expenses_or_dashboard(tenant_a: Any):
    with organization_context(tenant_a.organization.id):
        codes = {
            p.permission.code for p in tenant_a.role("cashier").role_permissions.select_related()
        }
    assert "payments.read" in codes  # toʻlov doskasi uchun kerak
    assert "payments.create" in codes
    assert not {c for c in codes if c.split(".")[0] in {"reports", "expenses", "dashboard"}}


# --- Jurnal ---


def test_a_cashier_sees_only_their_own_payments(tenant_a: Any, desk: dict[str, Any]):
    response = _client(tenant_a, desk["cashier"]).get(reverse("v1:payment-list"))
    assert response.status_code == 200
    assert [r["id"] for r in _rows(response)] == [str(desk["mine"].id)]


def test_asking_for_another_cashier_does_not_widen_the_view(tenant_a: Any, desk: dict[str, Any]):
    response = _client(tenant_a, desk["cashier"]).get(
        reverse("v1:payment-list"), {"received_by": str(desk["other"].id)}
    )
    assert response.status_code == 200
    assert _rows(response) == []


def test_another_cashiers_payment_is_404_not_403(tenant_a: Any, desk: dict[str, Any]):
    client = _client(tenant_a, desk["cashier"])
    for name in ("v1:payment-detail", "v1:payment-receipt"):
        response = client.get(reverse(name, args=[desk["theirs"].id]))
        assert response.status_code == 404, name


def test_the_journal_total_is_their_own(tenant_a: Any, desk: dict[str, Any]):
    response = _client(tenant_a, desk["cashier"]).get(reverse("v1:payment-journal-summary"))
    assert response.status_code == 200
    assert Decimal(_data(response)["total"]) == Decimal("300000")


def test_the_daily_summary_is_their_own(tenant_a: Any, desk: dict[str, Any]):
    response = _client(tenant_a, desk["cashier"]).get(reverse("v1:payment-daily-summary"))
    assert response.status_code == 200
    assert Decimal(_data(response)["total"]) == Decimal("300000")


def test_the_board_summary_hides_the_months_takings(tenant_a: Any, desk: dict[str, Any]):
    """Doska qoladi — u kassirning ishi; oyning umumiy tushumi esa yoʻq."""
    client = _client(tenant_a, desk["cashier"])
    assert client.get(reverse("v1:payment-board")).status_code == 200
    summary = _data(client.get(reverse("v1:payment-board-summary")))
    assert summary["charged"] is None
    assert summary["paid"] is None
    assert summary["outstanding"] is None


# --- Hisobotlar ---


@pytest.mark.parametrize(
    "name", ["v1:report-revenue", "v1:report-expenses", "v1:report-profit-loss"]
)
def test_a_cashier_cannot_open_financial_reports(tenant_a: Any, desk: dict[str, Any], name: str):
    response = _client(tenant_a, desk["cashier"]).get(reverse(name))
    assert response.status_code == 403


def test_a_cashier_cannot_open_the_dashboard_or_expenses(tenant_a: Any, desk: dict[str, Any]):
    client = _client(tenant_a, desk["cashier"])
    assert client.get(reverse("v1:dashboard-list")).status_code == 403
    assert client.get(reverse("v1:expense-list")).status_code == 403


# --- Boshqalar oʻzgarmaydi (14-invariant) ---


def test_the_director_still_sees_everyone(tenant_a: Any, desk: dict[str, Any]):
    response = _client(tenant_a, desk["director"]).get(reverse("v1:payment-list"))
    assert {r["id"] for r in _rows(response)} == {str(desk["mine"].id), str(desk["theirs"].id)}
    summary = _data(_client(tenant_a, desk["director"]).get(reverse("v1:payment-board-summary")))
    assert summary["paid"] is not None


def test_a_custom_role_without_the_flag_is_not_restricted(tenant_a: Any, desk: dict[str, Any]):
    """Bogʻcha oʻzi yasagan "Kassir-2" — bayroqsiz, demak hammasini koʻradi."""
    from apps.accounts.models import Permission, RolePermission

    with organization_context(tenant_a.organization.id):
        role = Role.objects.create(
            organization=tenant_a.organization, name="Kassir-2", code="kassir_2"
        )
        for code in ("payments.read", "payments.create"):
            RolePermission.objects.create(role=role, permission=Permission.objects.get(code=code))
    user = _user(tenant_a, "custom@alfa.uz", role)

    response = _client(tenant_a, user).get(reverse("v1:payment-list"))
    assert len(_rows(response)) == 2


# --- Delegatsiya (ADR-25) ---


def test_an_own_only_actor_cannot_hand_out_an_unrestricted_role(tenant_a: Any):
    from apps.accounts.delegation import can_assign_role, can_edit_role

    cashier = _user(tenant_a, "k@alfa.uz", tenant_a.role("cashier"))
    with organization_context(tenant_a.organization.id):
        twin = Role.objects.create(organization=tenant_a.organization, name="Egizak", code="egizak")
        everything = cashier.permission_codes()
        assert can_assign_role(cashier, twin, actor_codes=everything, role_codes=set()) is False
        assert can_edit_role(cashier, twin, actor_codes=everything, role_codes=set()) is False


# --- Boshqa tashkilot ---


@pytest.mark.tenancy
def test_another_tenants_payment_is_404(tenant_a: Any, tenant_b: Any, desk: dict[str, Any]):
    other_cashier = _user(tenant_b, "kassir@beta.uz", tenant_b.role("cashier"))
    response = _client(tenant_b, other_cashier).get(
        reverse("v1:payment-detail", args=[desk["mine"].id])
    )
    assert response.status_code == 404


# --- Mavjud tashkilotlar: buyruq ---


def _legacy_cashier(tenant: Any) -> Role:
    """Oʻzgarishdan oldingi kassir roli — productionda shundaylari bor."""
    from apps.accounts.models import Permission, RolePermission

    with organization_context(tenant.organization.id):
        role = Role.objects.get(code="cashier")
        role.payments_own_only = False
        role.save(update_fields=["payments_own_only"])
        for code in ("reports.read", "expenses.read", "dashboard.read"):
            RolePermission.objects.get_or_create(
                role=role, permission=Permission.objects.get(code=code)
            )
        return role


def _cmd(*args: str) -> str:
    out = StringIO()
    call_command("restrict_cashier_role", *args, stdout=out)
    return out.getvalue()


def test_the_command_dry_run_changes_nothing(tenant_a: Any):
    role = _legacy_cashier(tenant_a)
    report = _cmd()
    with organization_context(tenant_a.organization.id):
        role.refresh_from_db()
        codes = {rp.permission.code for rp in role.role_permissions.select_related()}
    assert role.payments_own_only is False
    assert "reports.read" in codes
    assert "dry-run" in report.lower()


def test_the_command_restricts_existing_cashier_roles(tenant_a: Any, tenant_b: Any):
    a = _legacy_cashier(tenant_a)
    b = _legacy_cashier(tenant_b)
    with organization_context(tenant_a.organization.id):
        director_before = tenant_a.role("director").role_permissions.count()

    _cmd("--apply")
    second = _cmd("--apply")

    for tenant, role in ((tenant_a, a), (tenant_b, b)):
        with organization_context(tenant.organization.id):
            role.refresh_from_db()
            codes = {rp.permission.code for rp in role.role_permissions.select_related()}
        assert role.payments_own_only is True
        assert not {c for c in codes if c.split(".")[0] in {"reports", "expenses", "dashboard"}}
        assert {"payments.read", "payments.create"} <= codes
    with organization_context(tenant_a.organization.id):
        assert tenant_a.role("director").role_permissions.count() == director_before
    assert "0 ta" in second
