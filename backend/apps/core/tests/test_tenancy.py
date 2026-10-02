"""
Sprint 0 ning ASOSIY chiqish mezoni (docs/06 §5).

> "a test proves that a queryset built on the base model cannot return
>  another organization's rows."

Bu fayldagi testlar loyihadagi eng muhim testlar. Ular buzilsa, bu uslub
xatosi emas — bu bolalar ma'lumotining boshqa mijozga oqib chiqishi demak.
"""

from __future__ import annotations

import pytest

from apps.core.tenancy import TenantScopeMissing, organization_context
from apps.core.tests.models import TenantThing

pytestmark = [pytest.mark.django_db, pytest.mark.tenancy]


@pytest.fixture
def rows(organization, other_organization):  # type: ignore[no-untyped-def]
    """Har bir tashkilotda bittadan qator."""
    with organization_context(organization.id):
        mine = TenantThing.objects.create(organization=organization, name="meniki")
    with organization_context(other_organization.id):
        theirs = TenantThing.objects.create(organization=other_organization, name="begona")
    return mine, theirs


class TestTenantIsolation:
    def test_queryset_returns_only_current_organization(self, organization, rows):
        mine, theirs = rows
        with organization_context(organization.id):
            ids = set(TenantThing.objects.values_list("id", flat=True))
        assert ids == {mine.id}
        assert theirs.id not in ids

    def test_other_organization_row_is_not_found_by_pk(self, organization, rows):
        """Begona qatorga PK boʻyicha murojaat — DoesNotExist, 403 emas."""
        _, theirs = rows
        with organization_context(organization.id), pytest.raises(TenantThing.DoesNotExist):
            TenantThing.objects.get(pk=theirs.id)

    def test_filter_cannot_widen_the_scope(self, organization, rows):
        """
        Aniq `organization_id` filtri chegarani KENGAYTIRA olmaydi.

        Bu eng ehtimolli hujum shakli: endpoint mijozdan `organization` ni
        qabul qilib qo'ysa. Tenant filtri baza queryset'da bo'lgani uchun
        keyingi har qanday filter faqat toraytiradi.
        """
        _, theirs = rows
        with organization_context(organization.id):
            leaked = TenantThing.objects.filter(organization_id=theirs.organization_id)
        assert list(leaked) == []

    def test_exclude_cannot_bypass_the_scope(self, organization, rows):
        mine, _ = rows
        with organization_context(organization.id):
            remaining = list(TenantThing.objects.exclude(id=mine.id))
        assert remaining == []

    def test_count_and_aggregate_are_scoped(self, organization, rows):
        """Agregatlar ham cheklanadi — hisoblash orqali sizib chiqish boʻlmaydi."""
        with organization_context(organization.id):
            assert TenantThing.objects.count() == 1

    def test_scope_switches_with_context(self, organization, other_organization, rows):
        mine, theirs = rows
        with organization_context(other_organization.id):
            assert list(TenantThing.objects.values_list("id", flat=True)) == [theirs.id]
        with organization_context(organization.id):
            assert list(TenantThing.objects.values_list("id", flat=True)) == [mine.id]


class TestFailClosed:
    def test_missing_context_raises(self, rows):
        """
        Kontekstsiz so'rov — xato, bo'sh natija emas.

        Jimgina bo'sh ro'yxat qaytarish xavfliroq: u haqiqiy tenant xatosini
        yashiradi va "maʼlumot yoʻqoldi" degan noto'g'ri diagnostikaga olib
        keladi.
        """
        with pytest.raises(TenantScopeMissing):
            list(TenantThing.objects.all())

    def test_context_is_reset_after_block(self, organization, rows):
        with organization_context(organization.id):
            pass
        with pytest.raises(TenantScopeMissing):
            list(TenantThing.objects.all())

    def test_nested_context_restores_outer_scope(self, organization, other_organization, rows):
        mine, theirs = rows
        with organization_context(organization.id):
            with organization_context(other_organization.id):
                assert list(TenantThing.objects.values_list("id", flat=True)) == [theirs.id]
            # Ichki blokdan chiqqach tashqi kontekst tiklanishi shart.
            assert list(TenantThing.objects.values_list("id", flat=True)) == [mine.id]


class TestExplicitEscapeHatches:
    def test_unscoped_sees_everything(self, rows):
        """`.unscoped()` — ataylab, grep bilan topiladigan chiqish yoʻli."""
        assert TenantThing.objects.unscoped().count() == 2

    def test_all_objects_manager_is_unscoped(self, rows):
        assert TenantThing.all_objects.count() == 2

    def test_for_organization_is_explicit(self, organization, other_organization, rows):
        mine, theirs = rows
        assert list(
            TenantThing.objects.for_organization(other_organization.id).values_list("id", flat=True)
        ) == [theirs.id]

    def test_unscoped_survives_further_filtering(self, rows):
        """
        Bayroq `.filter()` dan keyin ham saqlanishi shart.

        Aks holda `.unscoped().filter(...)` jimgina yana cheklanib qolardi va
        platforma vazifalari tushunarsiz tarzda bo'sh natija olardi.
        """
        assert TenantThing.objects.unscoped().filter(name__in=["meniki", "begona"]).count() == 2
