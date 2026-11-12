"""
Delegatsiya qoidasi (ADR-25) — hech kim o'zida yo'q huquqni bera olmaydi.

Holat productiondan olingan: tashkilot egasi "Menejer" roliga `users.*`
berdi (xodim hisoblarini boshqarishi uchun). Bu qoidasiz o'sha menejer
`users.update` bilan o'zini egaga aylantira olardi — har bir test shu
yo'llardan birini yopadi va egasining odatiy ishini buzmasligini ham
tasdiqlaydi.
"""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.accounts.authentication import issue_token_pair
from apps.accounts.models import Permission, Role, RolePermission, User
from apps.branches.models import Branch
from apps.core.tenancy import organization_context

pytestmark = pytest.mark.django_db

PASSWORD = "Juda-Kuchli-Parol-2026"  # noqa: S105


def _grant(tenant, role_code: str, codes: set[str]) -> None:
    """Rolga qo'shimcha ruxsat beradi (egasi UI'da qilgandek)."""
    with organization_context(tenant.organization.id):
        role = Role.objects.get(code=role_code)
        for permission in Permission.objects.filter(code__in=codes):
            RolePermission.objects.get_or_create(role=role, permission=permission)


def _member(tenant, role_code: str, email: str) -> User:
    with organization_context(tenant.organization.id):
        return User.objects.create_user(
            email=email,
            password=PASSWORD,
            full_name=role_code,
            organization=tenant.organization,
            role=tenant.role(role_code),
            branch=None if role_code == "org_owner" else tenant.branch,
        )


def _client(tenant, user: User) -> APIClient:
    with organization_context(tenant.organization.id):
        tokens = issue_token_pair(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


# Productiondagi Paddington "Menejer" roli — egasi 2026-10-02 da sozlagan
# aniq to'plam. Test aynan shu holatni takrorlaydi.
PADDINGTON_MANAGER = {
    f"{module}.{action}"
    for module, actions in {
        "attendance": ("create", "read", "update"),
        "children": ("approve", "create", "delete", "export", "read", "update"),
        "dashboard": ("read",),
        "debtors": ("approve", "create", "delete", "export", "read", "update"),
        "expenses": ("approve", "create", "delete", "export", "read", "update"),
        "inventory": ("approve", "create", "delete", "export", "read", "update"),
        "notifications": ("approve", "create", "delete", "export", "read", "update"),
        "payments": ("approve", "create", "delete", "export", "read", "update"),
        "reports": ("approve", "create", "delete", "export", "read", "update"),
        "users": ("approve", "create", "delete", "export", "read", "update"),
        # `accounts/0011` (ADR-51): `payments.read` bor rolga tarif va
        # imtiyozni o'qish beriladi — migratsiyadan keyingi holat.
        "tariffs": ("read",),
        "discounts": ("read",),
    }.items()
    for action in actions
}


@pytest.fixture
def manager(tenant_a) -> User:
    """Paddington'dagi anita: menejer, rolida `users.*` ham bor."""
    with organization_context(tenant_a.organization.id):
        role = Role.objects.get(code="manager")
        RolePermission.objects.filter(role=role).delete()
    # On the big-update line every seeded system role also carries
    # `children.read_all` / `attendance.read_all` (ADR-21) — the role the
    # owner customised keeps them, as a migrated manager role would.
    _grant(tenant_a, "manager", PADDINGTON_MANAGER | READ_ALL)
    assert len(_codes(tenant_a, "manager")) == 56
    return _member(tenant_a, "manager", "anita@alfa.uz")


# ADR-21 scope permissions; seeded on every system role.
READ_ALL = {"children.read_all", "attendance.read_all"}


def _codes(tenant, role_code: str) -> set[str]:
    with organization_context(tenant.organization.id):
        return set(
            Permission.objects.filter(role_permissions__role__code=role_code).values_list(
                "code", flat=True
            )
        )


class TestNoSelfEscalation:
    def test_manager_cannot_widen_her_own_role(self, tenant_a, manager):
        role = tenant_a.role("manager")
        everything = _codes(tenant_a, "org_owner")

        response = _client(tenant_a, manager).put(
            f"/api/v1/roles/{role.id}/permissions",
            {"permissions": sorted(everything)},
            format="json",
        )

        assert response.status_code == 403
        assert "payroll.read" not in _codes(tenant_a, "manager")
        assert "billing.read" not in _codes(tenant_a, "manager")

    def test_manager_cannot_make_herself_owner(self, tenant_a, manager):
        owner_role = tenant_a.role("org_owner")
        response = _client(tenant_a, manager).patch(
            f"/api/v1/users/{manager.id}", {"role_id": str(owner_role.id)}, format="json"
        )
        assert response.status_code == 403
        with organization_context(tenant_a.organization.id):
            manager.refresh_from_db()
            assert not manager.is_org_owner

    def test_manager_cannot_create_an_owner_account(self, tenant_a, manager):
        response = _client(tenant_a, manager).post(
            "/api/v1/users",
            {
                "full_name": "Soxta Ega",
                "email": "fake-owner@alfa.uz",
                "password": PASSWORD,
                "role_id": str(tenant_a.role("org_owner").id),
                "branch_id": str(tenant_a.branch.id),
            },
            format="json",
        )
        assert response.status_code == 403
        with organization_context(tenant_a.organization.id):
            assert not User.objects.filter(email="fake-owner@alfa.uz").exists()

    def test_manager_cannot_assign_a_role_wider_than_hers(self, tenant_a, manager):
        """Direktor rolida oylik (`payroll.*`) bor — menejerda yo'q."""
        response = _client(tenant_a, manager).post(
            "/api/v1/users",
            {
                "full_name": "Direktor",
                "email": "dir@alfa.uz",
                "password": PASSWORD,
                "role_id": str(tenant_a.role("director").id),
                "branch_id": str(tenant_a.branch.id),
            },
            format="json",
        )
        assert response.status_code == 403
        assert "payroll" in response.json()["error"]["message"]

    def test_role_code_cannot_be_renamed(self, tenant_a, manager):
        """
        `is_org_owner` = `role.code == "org_owner"`. Kodni qayta nomlash
        egasini egalikdan mahrum qilardi — hatto egasining o'zi uchun ham
        yopiq (kod — rolning shaxsi).
        """
        owner_role = tenant_a.role("org_owner")
        as_manager = _client(tenant_a, manager).patch(
            f"/api/v1/roles/{owner_role.id}", {"code": "x"}, format="json"
        )
        assert as_manager.status_code == 403

        as_owner = tenant_a.client().patch(
            f"/api/v1/roles/{owner_role.id}", {"code": "x"}, format="json"
        )
        assert as_owner.status_code == 400
        with organization_context(tenant_a.organization.id):
            tenant_a.owner.refresh_from_db()
            assert tenant_a.owner.is_org_owner

    def test_manager_cannot_reset_the_owners_password(self, tenant_a, manager):
        """
        Egasi filialga bog'lanmagan — menejerning ro'yxatida umuman yo'q
        (filial doirasi `404` beradi). Qoida baribir ikkinchi qavat.
        """
        response = _client(tenant_a, manager).post(
            f"/api/v1/users/{tenant_a.owner.id}/reset-password",
            {"password": "Yangi-Parol-2026-xx"},
            format="json",
        )
        assert response.status_code in (403, 404)
        with organization_context(tenant_a.organization.id):
            tenant_a.owner.refresh_from_db()
            assert tenant_a.owner.check_password(tenant_a.password)


class TestReadAllIsDelegatedLikeAnyOtherPermission:
    def test_a_manager_without_read_all_cannot_create_a_cashier_who_has_it(self, tenant_a):
        """
        Found when merging main (ADR-25) into big-update (ADR-21): the seeded
        cashier role carries `children.read_all`. A manager whose role lacks
        it — e.g. a teacher-scoped manager — may not hand out "see the whole
        kindergarten" through a new account. The delegation rule refuses,
        exactly as for any other permission.
        """
        with organization_context(tenant_a.organization.id):
            RolePermission.objects.filter(role__code="manager").delete()
        _grant(tenant_a, "manager", PADDINGTON_MANAGER)
        narrow = _member(tenant_a, "manager", "tor@alfa.uz")

        response = _client(tenant_a, narrow).post(
            "/api/v1/users",
            {
                "full_name": "Yangi Kassir",
                "email": "kassir2@alfa.uz",
                "password": PASSWORD,
                "role_id": str(tenant_a.role("cashier").id),
                "branch_id": str(tenant_a.branch.id),
            },
            format="json",
        )
        assert response.status_code == 403


class TestLegitimateDelegationStillWorks:
    def test_manager_can_open_a_cashier_account_in_her_branch(self, tenant_a, manager):
        """Menejerning haqiqiy ishi: kassir rolidagi hamma ruxsat unda bor."""
        assert _codes(tenant_a, "cashier") <= _codes(tenant_a, "manager")
        response = _client(tenant_a, manager).post(
            "/api/v1/users",
            {
                "full_name": "Yangi Kassir",
                "email": "kassir@alfa.uz",
                "password": PASSWORD,
                "role_id": str(tenant_a.role("cashier").id),
                "branch_id": str(tenant_a.branch.id),
            },
            format="json",
        )
        assert response.status_code == 201, response.json()

    def test_manager_cannot_open_an_account_in_another_branch(self, tenant_a, manager):
        with organization_context(tenant_a.organization.id):
            other = Branch.objects.create(
                organization=tenant_a.organization, name="Ikkinchi", code="SECOND"
            )
        response = _client(tenant_a, manager).post(
            "/api/v1/users",
            {
                "full_name": "Begona",
                "email": "begona@alfa.uz",
                "password": PASSWORD,
                "role_id": str(tenant_a.role("cashier").id),
                "branch_id": str(other.id),
            },
            format="json",
        )
        assert response.status_code == 403

    def test_manager_can_edit_a_narrower_role(self, tenant_a, manager):
        cashier = tenant_a.role("cashier")
        narrower = sorted(_codes(tenant_a, "cashier") - {"payments.delete"})
        response = _client(tenant_a, manager).put(
            f"/api/v1/roles/{cashier.id}/permissions", {"permissions": narrower}, format="json"
        )
        assert response.status_code == 200
        assert "payments.delete" not in _codes(tenant_a, "cashier")

    def test_owner_is_unrestricted(self, tenant_a, manager):
        """Ega uchun hech narsa o'zgarmadi: istalgan rolni beradi va tahrirlaydi."""
        owner = tenant_a.client()
        role = tenant_a.role("manager")
        response = owner.put(
            f"/api/v1/roles/{role.id}/permissions",
            {"permissions": sorted(_codes(tenant_a, "manager") | {"payroll.read"})},
            format="json",
        )
        assert response.status_code == 200
        assert "payroll.read" in _codes(tenant_a, "manager")

    def test_roles_list_tells_the_ui_what_is_assignable(self, tenant_a, manager):
        rows = _client(tenant_a, manager).get("/api/v1/roles").json()["data"]
        by_code = {row["code"]: row for row in rows}

        assert by_code["cashier"]["can_assign"] is True
        assert by_code["org_owner"]["can_assign"] is False
        assert by_code["director"]["can_assign"] is False
        # O'z roli va egasi roli — tahrirlab bo'lmaydi.
        assert by_code["manager"]["can_edit"] is False
        assert by_code["org_owner"]["can_edit"] is False
        assert by_code["cashier"]["can_edit"] is True

        owner_rows = tenant_a.client().get("/api/v1/roles").json()["data"]
        assert all(row["can_assign"] and row["can_edit"] for row in owner_rows)


class TestBranchBoundWrites:
    """Filialga bog'langan xodim faqat o'z filialida yaratadi (ADR-25)."""

    def test_manager_cannot_create_in_another_branch(self, tenant_a, manager):
        with organization_context(tenant_a.organization.id):
            other = Branch.objects.create(
                organization=tenant_a.organization, name="Ikkinchi", code="SECOND"
            )
        response = _client(tenant_a, manager).post(
            "/api/v1/groups", {"name": "Begona guruh", "branch_id": str(other.id)}, format="json"
        )
        assert response.status_code == 403

    def test_manager_creates_in_her_own_branch(self, tenant_a, manager):
        _grant(tenant_a, "manager", {"children.create"})
        response = _client(tenant_a, manager).post(
            "/api/v1/groups",
            {"name": "O'z guruhi", "branch_id": str(tenant_a.branch.id)},
            format="json",
        )
        assert response.status_code == 201, response.json()

    def test_owner_picks_any_branch(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            other = Branch.objects.create(
                organization=tenant_a.organization, name="Ikkinchi", code="SECOND"
            )
        response = tenant_a.client().post(
            "/api/v1/groups", {"name": "Gorkiy guruhi", "branch_id": str(other.id)}, format="json"
        )
        assert response.status_code == 201, response.json()

    def test_owner_with_two_branches_and_no_choice_gets_a_clear_message(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            Branch.objects.create(
                organization=tenant_a.organization, name="Ikkinchi", code="SECOND"
            )
        response = tenant_a.client().post("/api/v1/groups", {"name": "Qaysi?"}, format="json")
        assert response.status_code == 422
        assert "filial tanlovidan" in response.json()["error"]["message"]
