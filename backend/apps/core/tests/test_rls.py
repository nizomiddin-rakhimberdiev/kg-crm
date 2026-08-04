"""
RLS siyosatlari HAQIQATAN ishlayotganini isbotlaydigan testlar (docs/03 §6.3).

Siyosat yozib qo'yish yetarli emas. Postgres'da jadval **egasi** RLS'ni
sukut bo'yicha chetlab o'tadi — ya'ni siyosatlarni yozib, ilovani egasi
roli bilan ulash "himoya bor" deb o'ylab, aslida hech narsa qilmaslik
demakdir. Shuning uchun migratsiya `FORCE ROW LEVEL SECURITY` ham
qo'yadi: egasi ham siyosat ostida.

Buning yon foydasi katta — **butun test to'plami RLS ostida ishlaydi.**
Ya'ni siyosat shu yerdagi o'nta test bilan emas, 500 dan ortiq test
bilan sinaladi: agar biror siyosat noto'g'ri bo'lsa, tegishli modulning
testi qizaradi.

Quyidagi testlar esa xom SQL bilan to'g'ridan-to'g'ri tekshiradi: ORM
umuman chetlab o'tilganda ham baza o'z ishini qilyaptimi?
"""

from __future__ import annotations

from datetime import date

import pytest
from django.db import connection

from apps.children.models import Child
from apps.core.rls import (
    CATALOGUE_TABLES,
    DERIVED_TABLES,
    METADATA_TABLES,
    OPERATIONAL_TABLES,
)
from apps.core.tenancy import organization_context

pytestmark = [pytest.mark.django_db, pytest.mark.tenancy]


def _sql(sql: str, params: list | None = None) -> list:
    """Xom SQL — ORM'ni butunlay chetlab o'tib."""
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        return cursor.fetchall()


def _set_org(organization_id: object) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config('app.organization_id', %s, false)", [str(organization_id)]
        )


def _make_child(tenant, name: str) -> Child:
    with organization_context(tenant.organization.id):
        return Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name=name,
            last_name="Testov",
            date_of_birth=date(2021, 3, 14),
            gender="male",
        )


class TestPoliciesAreInstalled:
    def test_every_tenant_table_has_a_policy(self):
        """
        Har bir tenant jadvalida siyosat bo'lishi SHART.

        Unutilgan jadval — himoyasiz jadval, va uni ko'z bilan payqash
        mumkin emas: hamma narsa normal ishlab turadi.
        """
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT tablename FROM pg_policies WHERE policyname = 'tenant_isolation'"
            )
            protected = {row[0] for row in cursor.fetchall()}

        expected = {*OPERATIONAL_TABLES, *METADATA_TABLES, *DERIVED_TABLES}
        missing = expected - protected
        assert not missing, f"Bu jadvallarda RLS siyosati yo'q: {sorted(missing)}"

    def test_the_table_list_matches_the_models(self):
        """
        Ro'yxat modellar bilan sinxron.

        Yangi tenant model qo'shilib, `OPERATIONAL_TABLES` ga
        yozilmasa — u RLS'siz qoladi. Bu test shuni topadi.
        """
        from django.apps import apps

        from apps.core.models import TenantScopedModel

        model_tables = {
            model._meta.db_table
            for model in apps.get_models()
            if issubclass(model, TenantScopedModel)
            # `core.tests.models` dagi model faqat testlar uchun va
            # migratsiyaga tushmaydi (conftest.py uni qo'lda yaratadi).
            and not model._meta.db_table.startswith("test_")
        }
        known = {*OPERATIONAL_TABLES, *METADATA_TABLES, *CATALOGUE_TABLES}
        unlisted = model_tables - known
        assert not unlisted, (
            f"Bu tenant modellar RLS ro'yxatiga qo'shilmagan: {sorted(unlisted)}. "
            f"`apps/core/rls.py` ga qo'shing va migratsiya yozing."
        )

    def test_rls_is_enabled_not_just_defined(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT relname FROM pg_class WHERE relrowsecurity = true AND relkind = 'r'"
            )
            enabled = {row[0] for row in cursor.fetchall()}
        assert "child" in enabled
        assert "payment" in enabled
        assert "child_ledger_entry" in enabled


class TestFailClosed:
    def test_no_tenant_context_means_no_rows(self, tenant_a):
        """
        Kontekstsiz ulanish HECH NARSA ko'rmaydi.

        Sukut bo'yicha holat "hammasi ochiq" emas, "hech narsa
        ko'rinmaydi" — `TenantScopeMissing` bilan bir xil falsafa. Agar
        teskarisi bo'lganda, GUC o'rnatishni unutgan bitta kod yo'li
        butun bazani ochib qo'yardi.
        """
        _make_child(tenant_a, "Ali")
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('app.organization_id', '', false)")

        assert _sql("SELECT count(*) FROM child")[0][0] == 0

    def test_a_garbage_setting_does_not_open_the_door(self, tenant_a):
        _make_child(tenant_a, "Ali")
        _set_org("00000000-0000-0000-0000-000000000000")
        assert _sql("SELECT count(*) FROM child")[0][0] == 0


class TestIsolation:
    def test_the_database_itself_hides_the_other_tenant(self, tenant_a, tenant_b):
        """
        Bu testning butun ma'nosi: ORM'ni umuman chetlab o'tamiz.

        Xom SQL yozamiz, `WHERE organization_id` yozmaymiz — va baribir
        faqat o'z tashkilotimizning qatorlarini olamiz. Ya'ni endpointda
        filtrni unutgan dasturchi ham begona ma'lumotni chiqara olmaydi.
        """
        _make_child(tenant_a, "Ozimniki")
        _make_child(tenant_b, "Begona")

        _set_org(tenant_a.organization.id)

        rows = _sql("SELECT first_name FROM child")
        names = {row[0] for row in rows}
        assert names == {"Ozimniki"}, f"Begona qator ko'rindi: {names}"

    def test_money_tables_are_isolated_too(self, tenant_a, tenant_b):
        from decimal import Decimal

        from apps.finance import services as finance

        child_a = _make_child(tenant_a, "A")
        child_b = _make_child(tenant_b, "B")
        with organization_context(tenant_a.organization.id):
            finance.record_payment(child=child_a, amount=Decimal("100000"), method="cash")
        with organization_context(tenant_b.organization.id):
            finance.record_payment(child=child_b, amount=Decimal("900000"), method="cash")

        _set_org(tenant_a.organization.id)

        total = _sql("SELECT COALESCE(SUM(amount), 0) FROM payment")[0][0]
        assert total == Decimal("100000.00")

    def test_insert_into_another_tenant_is_blocked(self, tenant_a, tenant_b):
        """
        `WITH CHECK` — begona tashkilot nomiga YOZIB ham bo'lmaydi.

        Faqat o'qishni himoya qilish yetarli emas: buzilgan kod
        boshqa mijozning ma'lumotiga qator qo'shib, uning hisobotini
        buzishi mumkin edi.
        """
        import psycopg

        _set_org(tenant_a.organization.id)

        with pytest.raises((psycopg.errors.InsufficientPrivilege, Exception)):
            _sql(
                """
                INSERT INTO expense_category
                    (id, created_at, updated_at, is_active, name, organization_id, branch_id)
                VALUES (gen_random_uuid(), now(), now(), true, 'Begona', %s, %s)
                """,
                [str(tenant_b.organization.id), str(tenant_b.branch.id)],
            )


class TestPlatformPlane:
    """
    Vendor metama'lumotni ko'radi, operatsion ma'lumotni KO'RMAYDI.

    Bu ajratish siyosat darajasida, ilova darajasida emas — ya'ni
    "platforma rejimini o'chirishni unutdim" degan xato bolalar
    yozuvlarini ocholmaydi (docs/04 §19).
    """

    def test_platform_mode_sees_organizations(self, tenant_a, tenant_b):
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('app.organization_id', '', false)")
            cursor.execute("SELECT set_config('app.platform', 'on', false)")
        try:
            count = _sql("SELECT count(*) FROM organization")[0][0]
            assert count >= 2
        finally:
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('app.platform', '', false)")

    def test_platform_mode_cannot_read_children(self, tenant_a, tenant_b):
        """
        Buzilgan platforma akkauntining ta'sir doirasi.

        "Mijozlar ro'yxatini biladi" — ha. "Har bir bolaning yozuvini
        o'qiydi" — yo'q, va buni baza ta'minlaydi.
        """
        _make_child(tenant_a, "Ali")
        _make_child(tenant_b, "Vali")

        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('app.organization_id', '', false)")
            cursor.execute("SELECT set_config('app.platform', 'on', false)")
        try:
            for table in (
                "child",
                "payment",
                "child_ledger_entry",
                "attendance_record",
                "guardian",
            ):
                # Jadval nomi shu testdagi qat'iy ro'yxatdan, mijozdan emas.
                count = _sql(f"SELECT count(*) FROM {table}")[0][0]  # noqa: S608
                assert count == 0, f"Platforma rejimi `{table}` jadvalini ochib qo'ydi"
        finally:
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('app.platform', '', false)")

    def test_platform_mode_sees_subscription_metadata(self, tenant_a):
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('app.organization_id', '', false)")
            cursor.execute("SELECT set_config('app.platform', 'on', false)")
        try:
            assert _sql("SELECT count(*) FROM subscription")[0][0] >= 1
        finally:
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('app.platform', '', false)")


class TestContextManagerWiring:
    def test_entering_the_context_sets_the_database_setting(self, tenant_a):
        """
        `organization_context` ikkala qatlamni ham o'rnatadi.

        Ular ajralib qolsa, "ORM to'g'ri tenantda, baza noto'g'ri
        tenantda" degan holat paydo bo'lardi — va u eng chalkash turdagi
        xato bo'lardi.
        """
        with organization_context(tenant_a.organization.id), connection.cursor() as cursor:
            cursor.execute("SELECT app_current_org()")
            assert str(cursor.fetchone()[0]) == str(tenant_a.organization.id)

    def test_leaving_the_context_clears_the_setting(self, tenant_a):
        """
        Chiqishda tozalanadi.

        Ulanish puldan qaytadi; keyingi so'rov oldingi tenantning
        qiymatini meros qilib olsa, bu eng yomon turdagi sizib chiqish
        bo'lardi — tasodifiy va takrorlanmaydigan.
        """
        with organization_context(tenant_a.organization.id):
            pass
        with connection.cursor() as cursor:
            cursor.execute("SELECT app_current_org()")
            assert cursor.fetchone()[0] is None

    def test_nested_contexts_restore_the_outer_one(self, tenant_a, tenant_b):
        with organization_context(tenant_a.organization.id):
            with organization_context(tenant_b.organization.id), connection.cursor() as inner:
                inner.execute("SELECT app_current_org()")
                assert str(inner.fetchone()[0]) == str(tenant_b.organization.id)

            with connection.cursor() as outer:
                outer.execute("SELECT app_current_org()")
                assert str(outer.fetchone()[0]) == str(tenant_a.organization.id)
