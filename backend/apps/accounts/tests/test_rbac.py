"""
RBAC testlari — docs/02 §11.2 matritsasi kod bilan mos ekanini qotiradi.

Bu testlar hujjat va kod bir-biridan ajralib ketmasligi uchun: matritsa
o'zgarsa, ular qizaradi va hujjat bilan birga yangilanadi (CLAUDE.md
"docs va kod birga o'zgaradi").
"""

from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.authentication import issue_token_pair
from apps.accounts.constants import ROLE_MATRIX, SYSTEM_ROLES
from apps.accounts.models import Permission, User
from apps.core.tenancy import organization_context

pytestmark = pytest.mark.django_db

PASSWORD = "Juda-Kuchli-Parol-2026"  # noqa: S105


def _member(tenant, role_code: str, email: str | None = None) -> User:
    """Berilgan rol bilan xodim yaratadi."""
    with organization_context(tenant.organization.id):
        return User.objects.create_user(
            email=email or f"{role_code}@{tenant.organization.slug}.uz",
            password=PASSWORD,
            full_name=role_code,
            organization=tenant.organization,
            role=tenant.role(role_code),
            branch=None if role_code == "org_owner" else tenant.branch,
        )


def _client_for(tenant, user: User) -> APIClient:
    with organization_context(tenant.organization.id):
        tokens = issue_token_pair(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


class TestSeededRoles:
    def test_all_system_roles_created_on_signup(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            from apps.accounts.models import Role

            codes = set(Role.objects.values_list("code", flat=True))
        assert codes == set(SYSTEM_ROLES)

    @pytest.mark.parametrize("role_code", sorted(SYSTEM_ROLES))
    def test_role_permissions_match_the_documented_matrix(self, tenant_a, role_code):
        with organization_context(tenant_a.organization.id):
            role = tenant_a.role(role_code)
            actual = set(
                Permission.objects.filter(role_permissions__role=role).values_list(
                    "code", flat=True
                )
            )
        expected = {
            f"{module}.{action}"
            for module, actions in ROLE_MATRIX[role_code].items()
            for action in actions
        }
        assert actual == expected, f"'{role_code}' roli docs/02 §11.2 dan farq qilyapti"

    def test_system_roles_cannot_be_deleted(self, tenant_a):
        role = tenant_a.role("cashier")
        response = tenant_a.client().delete(reverse("v1:role-detail", args=[role.id]))
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"


class TestPermissionEnforcement:
    def test_cashier_cannot_list_users(self, tenant_a):
        """Kassirda `users.read` yo'q (docs/02 §11.2)."""
        client = _client_for(tenant_a, _member(tenant_a, "cashier"))
        assert client.get(reverse("v1:user-list")).status_code == 403

    def test_cashier_cannot_create_branch(self, tenant_a):
        client = _client_for(tenant_a, _member(tenant_a, "cashier"))
        response = client.post(
            reverse("v1:branch-list"), {"name": "Yangi", "code": "NEW"}, format="json"
        )
        assert response.status_code == 403

    def test_director_can_read_but_not_create_users(self, tenant_a):
        """Direktorda `users` faqat o'qish (docs/02 §11.2)."""
        client = _client_for(tenant_a, _member(tenant_a, "director"))
        assert client.get(reverse("v1:user-list")).status_code == 200

        response = client.post(
            reverse("v1:user-list"),
            {
                "full_name": "Yangi",
                "email": "yangi@alfa.uz",
                "password": PASSWORD,
                "role_id": str(tenant_a.role("cashier").id),
                "branch_id": str(tenant_a.branch.id),
            },
            format="json",
        )
        assert response.status_code == 403

    def test_org_owner_has_full_access(self, tenant_a):
        client = tenant_a.client()
        assert client.get(reverse("v1:user-list")).status_code == 200
        assert client.get(reverse("v1:branch-list")).status_code == 200
        assert client.get(reverse("v1:role-list")).status_code == 200

    def test_permission_denied_returns_403_not_404(self, tenant_a):
        """
        Ruxsat yo'qligi `403`, mavjud emasligi `404`.

        Bu ikkisi ataylab farqlanadi: `403` "sizda huquq yo'q" (bir tashkilot
        ichida), `404` esa "bunday narsa yo'q" (tashkilotlar orasida).
        """
        client = _client_for(tenant_a, _member(tenant_a, "cashier"))
        response = client.get(reverse("v1:user-list"))
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "PERMISSION_DENIED"


class TestBranchScoping:
    def test_non_owner_sees_only_own_branch_users(self, tenant_a):
        """Filial doirasi tashkilot filtridan KEYIN qo'llanadi (docs/02 §11.3)."""
        from apps.branches.models import Branch

        with organization_context(tenant_a.organization.id):
            second = Branch.objects.create(
                organization=tenant_a.organization, name="Ikkinchi", code="B2"
            )
            other_branch_user = User.objects.create_user(
                email="boshqa-filial@alfa.uz",
                password=PASSWORD,
                full_name="Boshqa filial",
                organization=tenant_a.organization,
                role=tenant_a.role("cashier"),
                branch=second,
            )

        director = _member(tenant_a, "director")
        response = _client_for(tenant_a, director).get(reverse("v1:user-list"))
        assert response.status_code == 200
        ids = {row["id"] for row in response.json()["data"]}
        assert str(other_branch_user.id) not in ids

    def test_org_owner_sees_all_branches(self, tenant_a):
        from apps.branches.models import Branch

        with organization_context(tenant_a.organization.id):
            second = Branch.objects.create(
                organization=tenant_a.organization, name="Ikkinchi", code="B2"
            )
            far_user = User.objects.create_user(
                email="uzoq@alfa.uz",
                password=PASSWORD,
                full_name="Uzoq",
                organization=tenant_a.organization,
                role=tenant_a.role("cashier"),
                branch=second,
            )

        response = tenant_a.client().get(reverse("v1:user-list"))
        ids = {row["id"] for row in response.json()["data"]}
        assert str(far_user.id) in ids

    @pytest.mark.tenancy
    def test_branch_filter_cannot_reach_another_tenant(self, tenant_a, tenant_b):
        """
        Org Owner `?branch=` bilan filtrlashi mumkin, lekin bu chegarani
        kengaytira olmaydi: queryset allaqachon tashkilot bilan cheklangan,
        shuning uchun begona filial ID'si bo'sh natija beradi.
        """
        response = tenant_a.client().get(
            reverse("v1:user-list"), {"branch": str(tenant_b.branch.id)}
        )
        assert response.status_code == 200
        assert response.json()["data"] == []


class TestUserCreation:
    def test_owner_can_create_user_in_own_organization(self, tenant_a):
        response = tenant_a.client().post(
            reverse("v1:user-list"),
            {
                "full_name": "Yangi Kassir",
                "email": "kassir2@alfa.uz",
                "password": PASSWORD,
                "role_id": str(tenant_a.role("cashier").id),
                "branch_id": str(tenant_a.branch.id),
            },
            format="json",
        )
        assert response.status_code == 201

    @pytest.mark.tenancy
    def test_cannot_assign_role_from_another_organization(self, tenant_a, tenant_b):
        """
        Begona tashkilotning roli — validatsiya xatosi, `403` emas.

        `403` o'sha rol boshqa joyda mavjudligini tasdiqlardi.
        """
        response = tenant_a.client().post(
            reverse("v1:user-list"),
            {
                "full_name": "Buzg'unchi",
                "email": "buzgunchi@alfa.uz",
                "password": PASSWORD,
                "role_id": str(tenant_b.role("cashier").id),
                "branch_id": str(tenant_a.branch.id),
            },
            format="json",
        )
        assert response.status_code == 400
        assert "role_id" in response.json()["error"]["details"]

    @pytest.mark.tenancy
    def test_cannot_assign_branch_from_another_organization(self, tenant_a, tenant_b):
        response = tenant_a.client().post(
            reverse("v1:user-list"),
            {
                "full_name": "Buzg'unchi",
                "email": "buzgunchi2@alfa.uz",
                "password": PASSWORD,
                "role_id": str(tenant_a.role("cashier").id),
                "branch_id": str(tenant_b.branch.id),
            },
            format="json",
        )
        assert response.status_code == 400
        assert "branch_id" in response.json()["error"]["details"]

    def test_non_owner_role_requires_branch(self, tenant_a):
        response = tenant_a.client().post(
            reverse("v1:user-list"),
            {
                "full_name": "Filiaisiz",
                "email": "filialsiz@alfa.uz",
                "password": PASSWORD,
                "role_id": str(tenant_a.role("cashier").id),
            },
            format="json",
        )
        assert response.status_code == 400
        assert "branch_id" in response.json()["error"]["details"]

    def test_duplicate_email_within_organization_rejected(self, tenant_a):
        response = tenant_a.client().post(
            reverse("v1:user-list"),
            {
                "full_name": "Takror",
                "email": tenant_a.owner.email,
                "password": PASSWORD,
                "role_id": str(tenant_a.role("cashier").id),
                "branch_id": str(tenant_a.branch.id),
            },
            format="json",
        )
        assert response.status_code == 400
        assert "email" in response.json()["error"]["details"]


class TestRoleCustomisation:
    """
    Matritsa — boshlang'ich holat, qulf emas (docs/02 §11.2).

    Bog'chalarning ish taqsimoti har xil: birida kassir davomat ham qo'yadi,
    boshqasida yo'q. Shuning uchun tashkilot egasi rollarni moslashtira oladi.
    """

    def test_owner_can_change_a_system_role_permissions(self, tenant_a):
        role = tenant_a.role("cashier")

        response = tenant_a.client().put(
            reverse("v1:role-permissions", args=[role.id]),
            {"permissions": ["children.read", "attendance.read", "attendance.create"]},
            format="json",
        )

        assert response.status_code == 200
        assert response.json()["data"]["permissions"] == [
            "attendance.create",
            "attendance.read",
            "children.read",
        ]

    def test_owner_role_cannot_lose_the_keys_to_the_house(self, tenant_a):
        """
        Rollarni faqat `users.update` ega odam sozlaydi.

        Uni egasidan olib tashlash — tashkilotni o'zini o'zi qulflab qo'yishi:
        keyin hech kim hech qanday rolni tuzata olmaydi.
        """
        role = tenant_a.role("org_owner")

        response = tenant_a.client().put(
            reverse("v1:role-permissions", args=[role.id]),
            {"permissions": ["children.read"]},
            format="json",
        )

        assert response.status_code == 422
        assert "users.update" in response.json()["error"]["message"]

    def test_owner_can_create_a_custom_role(self, tenant_a):
        response = tenant_a.client().post(
            reverse("v1:role-list"),
            {"name": "Kassir yordamchisi", "code": "Kassir Yordamchisi"},
            format="json",
        )

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["code"] == "kassir_yordamchisi"  # normallashtiriladi
        assert data["is_system"] is False

    def test_duplicate_role_code_is_rejected_with_400(self, tenant_a):
        """Bazadagi unikallik cheklovi 500 emas, tushunarli 400 berishi kerak."""
        response = tenant_a.client().post(
            reverse("v1:role-list"),
            {"name": "Yangi kassir", "code": "cashier"},
            format="json",
        )

        assert response.status_code == 400
        assert "code" in response.json()["error"]["details"]

    def test_system_role_code_is_immutable(self, tenant_a):
        role = tenant_a.role("director")

        response = tenant_a.client().patch(
            reverse("v1:role-detail", args=[role.id]),
            {"code": "boshqaruvchi"},
            format="json",
        )

        assert response.status_code == 400
        assert "code" in response.json()["error"]["details"]

    def test_system_role_can_be_renamed(self, tenant_a):
        """Nomi — bog'chaning atamasi, uni o'zgartirish mumkin."""
        role = tenant_a.role("director")

        response = tenant_a.client().patch(
            reverse("v1:role-detail", args=[role.id]),
            {"name": "Bog'cha mudiri"},
            format="json",
        )

        assert response.status_code == 200
        assert response.json()["data"]["name"] == "Bog'cha mudiri"


class TestSelfServiceProfile:
    """
    `PATCH /auth/me` — foydalanuvchi o'zining profilini tahrirlaydi.

    Bu `/users/{id}` dan alohida yo'l: u `users.update` talab qiladi, ya'ni
    kassir o'z telefon raqamini ham o'zgartira olmasdi.
    """

    def test_user_can_edit_own_name_and_phone(self, tenant_a):
        cashier = _member(tenant_a, "cashier")
        client = _client_for(tenant_a, cashier)

        response = client.patch(
            reverse("v1:auth-me"),
            {"full_name": "Dilnoza Karimova", "phone": "+998901112233"},
            format="json",
        )

        assert response.status_code == 200
        user = response.json()["data"]["user"]
        assert user["full_name"] == "Dilnoza Karimova"
        assert user["phone"] == "+998901112233"

    def test_privileged_fields_are_ignored(self, tenant_a):
        """
        Eng muhim test: o'z-o'zini tahrirlash yo'li imtiyoz oshirish
        yo'liga aylanmasligi kerak. Rol, filial, email va faollik
        holati bu endpointda umuman qabul qilinmaydi.
        """
        cashier = _member(tenant_a, "cashier")
        owner_role_id = str(tenant_a.role("org_owner").id)
        client = _client_for(tenant_a, cashier)

        response = client.patch(
            reverse("v1:auth-me"),
            {
                "full_name": "Yangi ism",
                "role_id": owner_role_id,
                "email": "egasi@example.uz",
                "is_active": False,
                "organization": "boshqa",
            },
            format="json",
        )

        assert response.status_code == 200
        cashier.refresh_from_db()
        assert cashier.role.code == "cashier"  # rol o'zgarmadi
        assert cashier.email != "egasi@example.uz"  # email o'zgarmadi
        assert cashier.is_active is True  # o'zini o'chirmadi
        assert cashier.full_name == "Yangi ism"  # xavfsiz maydon esa o'zgardi


class TestProfilePhoto:
    """
    Profil rasmi (docs/04 §5).

    Yuklangan fayl keyin brauzerga qaytariladi, shuning uchun "bu haqiqatan
    rasmmi?" degan savol xavfsizlik savoli — kengaytmaga ishonish yetarli emas.
    """

    @staticmethod
    def _png(size: tuple[int, int] = (32, 32)) -> bytes:
        import io

        from PIL import Image

        buffer = io.BytesIO()
        Image.new("RGB", size, (37, 99, 235)).save(buffer, format="PNG")
        return buffer.getvalue()

    def test_upload_returns_photo_url(self, tenant_a):
        from django.core.files.uploadedfile import SimpleUploadedFile

        response = tenant_a.client().post(
            reverse("v1:auth-me-photo"),
            {"photo": SimpleUploadedFile("avatar.png", self._png(), content_type="image/png")},
            format="multipart",
        )

        assert response.status_code == 200
        photo_url = response.json()["data"]["user"]["photo_url"]
        assert photo_url and photo_url.endswith(".png")
        # Fayl tashkilot papkasiga tushadi (docs/02 §16.2).
        assert str(tenant_a.organization.id) in photo_url

    def test_a_renamed_non_image_is_rejected(self, tenant_a):
        """Kengaytmasi `.png` bo'lgan ixtiyoriy bayt to'plami rad etiladi."""
        from django.core.files.uploadedfile import SimpleUploadedFile

        response = tenant_a.client().post(
            reverse("v1:auth-me-photo"),
            {
                "photo": SimpleUploadedFile(
                    "zararli.png", b"MZ\x90\x00 bu rasm emas", content_type="image/png"
                )
            },
            format="multipart",
        )

        assert response.status_code == 400
        assert "photo" in response.json()["error"]["details"]

    def test_disallowed_extension_is_rejected(self, tenant_a):
        from django.core.files.uploadedfile import SimpleUploadedFile

        response = tenant_a.client().post(
            reverse("v1:auth-me-photo"),
            {"photo": SimpleUploadedFile("hujjat.pdf", self._png(), content_type="image/png")},
            format="multipart",
        )

        assert response.status_code == 400

    def test_photo_can_be_removed(self, tenant_a):
        from django.core.files.uploadedfile import SimpleUploadedFile

        client = tenant_a.client()
        client.post(
            reverse("v1:auth-me-photo"),
            {"photo": SimpleUploadedFile("avatar.png", self._png(), content_type="image/png")},
            format="multipart",
        )

        response = client.delete(reverse("v1:auth-me-photo"))

        assert response.status_code == 200
        assert response.json()["data"]["user"]["photo_url"] is None
