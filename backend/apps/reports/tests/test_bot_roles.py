"""
Bot har rolga OʻZIGA yarasha gapiradi (mijoz soʻrovi, 2026-10-28).

Mijoz: *"Bot hamma rolga oʻziga yarasha ishlashi kerak, direktor uchun
alohida oʻziga kerak boʻlgan narsalarni, kassir uchun alohida, admin
uchun alohida va hokazo"*.

Javoblar allaqachon ruxsat boʻyicha tekshirilardi — kassir foydani
soʻrasa "ruxsat yoʻq" eshitardi. Lekin bot oʻzi SHU savolni taklif
qilardi: yordam roʻyxati hamma uchun bir xil edi, ya'ni bot odamni
javob bermaydigan savolga yoʻllardi.

Endi roʻyxat ruxsatdan quriladi. Oʻzi yasalgan rol ham shu yoʻldan
oʻtadi: hech qayerda rol KODI tekshirilmaydi (14-invariant).
"""

from __future__ import annotations

from typing import Any

import pytest

from apps.accounts.models import Role, User
from apps.core.tenancy import organization_context
from apps.reports import bot

pytestmark = pytest.mark.django_db


def _user(tenant: Any, email: str, role_code: str) -> User:
    with organization_context(tenant.organization.id):
        return User.objects.create_user(
            email=email,
            password="Parol2026!",
            organization=tenant.organization,
            branch=tenant.branch,
            role=tenant.role(role_code),
            full_name=f"{role_code} foydalanuvchi",
        )


def _examples(user: User) -> list[str]:
    return [line[2:] for line in bot.help_text(user=user).splitlines() if line.startswith("• ")]


def test_the_owner_is_offered_everything(tenant_a):
    with organization_context(tenant_a.organization.id):
        examples = _examples(tenant_a.owner)
    assert any("foyda" in e for e in examples)
    assert any("chiqim" in e for e in examples)
    assert any("obuna" in e for e in examples)


def test_the_cashier_is_not_offered_profit_or_expenses(tenant_a):
    cashier = _user(tenant_a, "kassir@bogcha.uz", "cashier")
    with organization_context(tenant_a.organization.id):
        examples = _examples(cashier)
    assert examples, "kassirga ham nimadir taklif qilinishi kerak"
    assert not any("foyda" in e for e in examples)
    assert not any("chiqim" in e for e in examples)
    assert not any("obuna" in e for e in examples)
    # Oʻzi qabul qilgan pul — aynan uning ishi.
    assert any("tushum" in e or "qabul" in e for e in examples)


def test_the_attendance_manager_is_offered_attendance(tenant_a):
    teacher = _user(tenant_a, "tarbiyachi@bogcha.uz", "attendance_manager")
    with organization_context(tenant_a.organization.id):
        examples = _examples(teacher)
    assert any("bola" in e for e in examples)
    assert not any("foyda" in e for e in examples)


def test_every_offered_question_is_understood(tenant_a):
    """Bot oʻzi tanimaydigan savolni maslahat bermasin."""
    cashier = _user(tenant_a, "kassir2@bogcha.uz", "cashier")
    with organization_context(tenant_a.organization.id):
        for user in (tenant_a.owner, cashier):
            for example in _examples(user):
                assert bot.classify(example) is not None, example


def test_a_role_without_expense_rights_is_not_told_to_send_one(tenant_a):
    cashier = _user(tenant_a, "kassir3@bogcha.uz", "cashier")
    with organization_context(tenant_a.organization.id):
        assert "150 000" not in bot.help_text(user=cashier)
        assert "150 000" in bot.help_text(user=tenant_a.owner)


def test_a_custom_role_follows_its_own_permissions(tenant_a):
    """Rol KODI emas, ruxsatlar — 14-invariant."""
    with organization_context(tenant_a.organization.id):
        role = Role.objects.create(
            organization=tenant_a.organization, code="qarovchi", name="Qarovchi"
        )
        from apps.accounts.models import Permission, RolePermission

        for permission in Permission.objects.filter(module="attendance"):
            RolePermission.objects.create(role=role, permission=permission)
        person = User.objects.create_user(
            email="qarovchi@bogcha.uz",
            password="Parol2026!",
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            role=role,
            full_name="Qarovchi",
        )
        examples = _examples(person)
    assert any("keldi" in e or "bola" in e for e in examples)
    assert not any("foyda" in e for e in examples)
