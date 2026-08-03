"""Umumiy pytest fixture'lari."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from django.db import connection

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
def api_client() -> Iterator[object]:
    from rest_framework.test import APIClient

    yield APIClient()
