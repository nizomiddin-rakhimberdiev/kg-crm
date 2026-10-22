"""
Rol shablonlari (audit, 2026-10-21).

Rollar ekranida 15 modul × 6 amal ≈ 100 belgi bor. Yangi rol yasash
uchun ularni qoʻlda bosish — "hech kim qilmaydigan ish" deb yozildi.
Tizim rollarining shakli allaqachon kodda (`ROLE_MATRIX`), ya'ni
shablon yangi maʼlumot emas: u shu matritsani ochib beradi.

**ADR-25 shu yerda ham.** Shablon hech kimga oʻzidagidan koʻpini
bermaydi: javob chaqiruvchining oʻz ruxsatlari bilan KESIShTIRILADI,
va nimasi tushib qolgani aytiladi — aks holda menejer shablonni
bosib, keyin saqlashda tushunarsiz xato olardi.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.urls import reverse

from apps.core.tenancy import organization_context

pytestmark = pytest.mark.django_db


def _templates(client: Any) -> list[dict[str, Any]]:
    response = client.get(reverse("v1:role-templates"))
    assert response.status_code == 200, response.content
    return response.json()["data"]


def test_the_owner_sees_every_template_in_full(tenant_a: Any):
    rows = _templates(tenant_a.client())

    codes = [row["code"] for row in rows]
    # Egasining roli shablon EMAS: uni tarqatib boʻlmaydi.
    assert "org_owner" not in codes
    assert {"director", "manager", "cashier", "attendance_manager"} <= set(codes)
    cashier = next(row for row in rows if row["code"] == "cashier")
    assert cashier["title"]
    assert "payments.read" in cashier["permissions"]
    assert cashier["dropped"] == []
    # Kassir — "faqat oʻzining toʻlovlari" roli (ADR-30).
    assert cashier["payments_own_only"] is True


def test_a_template_never_hands_out_more_than_the_caller_holds(tenant_a: Any):
    """
    ADR-25: rollarni sozlashga ruxsati bor, lekin oʻzi tor roldagi
    odam shablonni TOʻLIQ ola olmaydi.

    Bunday rol haqiqiy: egasi "Kadrlar" degan rol yasab, unga faqat
    hisoblarni boshqarishni berishi mumkin.
    """
    from rest_framework.test import APIClient

    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.models import Permission, Role, RolePermission, User

    narrow = {"users.read", "users.update", "children.read"}
    with organization_context(tenant_a.organization.id):
        role = Role.objects.create(
            organization=tenant_a.organization, name="Kadrlar", code="hr_only"
        )
        for permission in Permission.objects.filter(code__in=narrow):
            RolePermission.objects.create(role=role, permission=permission)
        member = User.objects.create_user(
            email="kadrlar@alfa.uz",
            password="Juda-Kuchli-Parol-2026",  # noqa: S106
            full_name="Kadrlar",
            organization=tenant_a.organization,
            role=role,
            branch=tenant_a.branch,
        )
        tokens = issue_token_pair(member)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    rows = _templates(client)
    cashier = next(row for row in rows if row["code"] == "cashier")
    assert set(cashier["permissions"]) <= narrow
    # Tushib qolganlari AYTILADI — jim qisqartirish eng yomoni.
    assert "payments.create" in cashier["dropped"]


@pytest.mark.tenancy
def test_templates_need_the_users_permission(tenant_a: Any):
    from rest_framework.test import APIClient

    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.models import User

    with organization_context(tenant_a.organization.id):
        cashier = User.objects.create_user(
            email="kassir2@alfa.uz",
            password="Juda-Kuchli-Parol-2026",  # noqa: S106
            full_name="Kassir",
            organization=tenant_a.organization,
            role=tenant_a.role("cashier"),
            branch=tenant_a.branch,
        )
        tokens = issue_token_pair(cashier)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    assert client.get(reverse("v1:role-templates")).status_code == 403
