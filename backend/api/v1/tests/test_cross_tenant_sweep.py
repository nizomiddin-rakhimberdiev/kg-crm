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
from typing import Any

import pytest
from django.urls import reverse

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


def _create_row(tenant: Any, basename: str) -> Any:
    """Berilgan tenant ichida shu endpoint uchun bitta qator yaratadi."""
    from apps.accounts.models import User
    from apps.branches.models import Branch
    from apps.children.models import Child, Group, Guardian

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

    def test_update_of_other_tenant_row_is_404(self, tenant_a, tenant_b, basename, prefix):
        foreign = _create_row(tenant_b, basename)
        response = tenant_a.client().patch(
            reverse(f"v1:{basename}-detail", args=[foreign.id]),
            {"name": "buzildi"},
            format="json",
        )
        assert response.status_code == 404

    def test_delete_of_other_tenant_row_is_404(self, tenant_a, tenant_b, basename, prefix):
        foreign = _create_row(tenant_b, basename)
        response = tenant_a.client().delete(reverse(f"v1:{basename}-detail", args=[foreign.id]))
        assert response.status_code == 404


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
