"""Umumiy pytest fixture'lari."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from django.db import connection

from apps.accounts.models import Role, User
from apps.accounts.services import register_organization
from apps.branches.models import Branch
from apps.core.tenancy import organization_context
from apps.organizations.models import Organization


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):  # type: ignore[no-untyped-def]
    """
    Test-only jadvallarni yaratadi.

    `TenantScopedModel` abstrakt, shuning uchun uni sinash uchun konkret model
    kerak. U `apps/core/tests/models.py` da yashaydi va migratsiyaga tushmaydi —
    test uchun mo'ljallangan jadval production sxemasiga chiqmasligi kerak.
    """
    from apps.core.tests.models import TenantThing

    with django_db_blocker.unblock(), connection.schema_editor() as schema_editor:
        schema_editor.create_model(TenantThing)
    yield


@pytest.fixture
def organization(db) -> Organization:  # type: ignore[no-untyped-def]
    return Organization.objects.create(
        name="Alfa Bog'cha", slug="alfa", contact_email="owner@alfa.uz"
    )


@pytest.fixture
def other_organization(db) -> Organization:  # type: ignore[no-untyped-def]
    """Ikkinchi tenant — izolyatsiya testlari uchun."""
    return Organization.objects.create(
        name="Beta Bog'cha", slug="beta", contact_email="owner@beta.uz"
    )


@pytest.fixture
def api_client() -> Any:
    from rest_framework.test import APIClient

    return APIClient()


# --- To'liq ro'yxatdan o'tgan tashkilotlar (cross-tenant testlar uchun) ---


@dataclass
class Tenant:
    """Ro'yxatdan o'tgan tashkilot va uning asosiy obyektlari."""

    organization: Organization
    branch: Branch
    owner: User
    password: str

    def role(self, code: str) -> Role:
        with organization_context(self.organization.id):
            return Role.objects.get(code=code)

    def client(self) -> Any:
        """Egasi sifatida autentifikatsiya qilingan API klient."""
        from rest_framework.test import APIClient

        from apps.accounts.authentication import issue_token_pair

        with organization_context(self.organization.id):
            tokens = issue_token_pair(self.owner)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        return client


def _register(name: str, email: str) -> Tenant:
    password = "Juda-Kuchli-Parol-2026"  # noqa: S105 — test ma'lumoti
    result = register_organization(
        organization_name=name,
        contact_email=email,
        full_name="Egasi",
        password=password,
    )
    return Tenant(
        organization=result.organization,
        branch=result.branch,
        owner=result.owner,
        password=password,
    )


@pytest.fixture
def tenant_a(db) -> Tenant:  # type: ignore[no-untyped-def]
    return _register("Alfa Bog'cha", "owner@alfa.uz")


@pytest.fixture
def tenant_b(db) -> Tenant:  # type: ignore[no-untyped-def]
    return _register("Beta Bog'cha", "owner@beta.uz")
