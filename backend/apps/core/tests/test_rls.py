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
    enable_platform_mode,
)
from apps.core.tenancy import organization_context, platform_context

pytestmark = [pytest.mark.django_db, pytest.mark.tenancy]


def _sql(sql: str, params: list | None = None) -> list:
    """Xom SQL — ORMʼni butunlay chetlab oʻtib."""
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
        assert not missing, f"Bu jadvallarda RLS siyosati yoʻq: {sorted(missing)}"

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
            f"Bu tenant modellar RLS roʻyxatiga qoʻshilmagan: {sorted(unlisted)}. "
            f"`apps/core/rls.py` ga qoʻshing va migratsiya yozing."
        )

    def test_rls_is_enabled_AND_forced(self):
        """
        `FORCE` ham bo'lishi SHART.

        Postgres jadval EGASINI o'z siyosatlaridan ozod qiladi. Ilova
        egasi roli bilan ulansa — eng keng tarqalgan deployment —
        siyosatlar bor bo'lib turadi, lekin hech narsa qilmaydi.
        Tashqaridan hammasi joyida ko'rinadi.

        Bu aynan shu loyihada sodir bo'lgan: migratsiya qo'llanilgandan
        keyin unga `FORCE` qo'shildi, va allaqachon migratsiya qilingan
        baza eski holatda qoldi. `check_rls` buyrug'i shu uchun bor.
        """
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT relname, relforcerowsecurity
                FROM pg_class
                WHERE relrowsecurity = true AND relkind = 'r'
                """
            )
            rows = dict(cursor.fetchall())

        for table in ("child", "payment", "child_ledger_entry", "user", "organization"):
            assert table in rows, f"{table}: RLS yoqilmagan"
            assert rows[table], f"{table}: FORCE yoʻq — egasi siyosatni chetlab oʻtadi"

    def test_the_generated_sql_forces_every_table(self):
        """`check_rls --fix` va migratsiya bir xil SQLʼdan foydalanadi."""
        from apps.core.rls import build_policy_sql

        sql = build_policy_sql()
        for table in (*OPERATIONAL_TABLES, *METADATA_TABLES, *DERIVED_TABLES):
            quoted = f'"{table}"'
            assert f"ALTER TABLE {quoted} FORCE ROW LEVEL SECURITY;" in sql, (
                f"{table} uchun FORCE generatsiya qilinmagan"
            )

    def test_check_command_passes_on_a_correct_database(self):
        """
        `check_rls` toza bazada muvaffaqiyat qaytaradi.

        Bu testning qiymati teskarisida: agar kimdir siyosat ro'yxatiga
        jadval qo'shib, migratsiya yozishni unutsa, buyruq deployda
        yiqiladi — va shu test buyruqning o'zi ishlayotganini
        kafolatlaydi.
        """
        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command("check_rls", stdout=out)
        assert "RLS kuchda" in out.getvalue()


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
        assert names == {"Ozimniki"}, f"Begona qator koʻrindi: {names}"

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
    "platforma rejimini oʻchirishni unutdim" degan xato bolalar
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

        "Mijozlar roʻyxatini biladi" — ha. "Har bir bolaning yozuvini
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
                assert count == 0, f"Platforma rejimi `{table}` jadvalini ochib qoʻydi"
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


class TestRequestBoundary:
    """
    So'rov tugagach ulanishda HECH QANDAY kontekst qolmasligi kerak.

    Bu sinf aniq bir xatoni qulflaydi (P0-001). `apply_tenant_setting()`
    autentifikatsiya paytida chaqirilardi, lekin uni hech kim
    tozalamasdi: middleware faqat `ContextVar` ni tozalardi, GUC'ga
    tegmasdi. `CONN_MAX_AGE = 60` bilan ulanish pulga tashkilot
    o'rnatilgan holda qaytardi.

    Oqibati nozik, lekin og'ir: RLS'ning butun ma'nosi "kontekst yo'q →
    hech narsa ko'rinmaydi" edi. Tozalanmagan GUC bilan u "kontekst yo'q
    → OLDINGI tenantni ko'rsat" ga aylanardi. Ya'ni ikkinchi izolyatsiya
    qatlami fail-closed emas, fail-stale bo'lib qolgandi — va aynan shu
    qatlam birinchisi unutilganda ushlab qolish uchun bor edi.

    Quyidagi testlar funksiya chaqirilganini emas, ULANISH HOLATINI
    tekshiradi. Tozalash olib tashlansa, ular qizaradi.
    """

    def test_the_request_leaves_no_organization_behind(self, tenant_a):
        """Eng toʻgʻridan-toʻgʻri tekshiruv: soʻrovdan keyin GUC boʻsh."""
        response = tenant_a.client().get("/api/v1/children")
        assert response.status_code == 200

        with connection.cursor() as cursor:
            cursor.execute("SELECT app_current_org()")
            leaked = cursor.fetchone()[0]

        assert leaked is None, (
            f"Soʻrovdan keyin ulanishda {leaked} qolib ketdi. Bu ulanish "
            "pulga shu holatda qaytadi va keyingi soʻrov uni meros qilib oladi."
        )

    def test_a_reused_connection_shows_the_next_query_nothing(self, tenant_a, tenant_b):
        """
        Haqiqiy stsenariy: so'rovdan KEYIN o'sha ulanishda kontekstsiz so'rov.

        Testdagi ulanish so'rovlar orasida qayta ishlatiladi — ya'ni bu
        production'dagi ulanish pulining aynan o'zi. Xom SQL ORM'ni
        butunlay chetlab o'tadi, shuning uchun bu yerda javob beradigan
        yagona narsa — RLS.
        """
        _make_child(tenant_a, "Aziza")
        _make_child(tenant_b, "Bekzod")

        response = tenant_a.client().get("/api/v1/children")
        assert response.status_code == 200
        assert b"Aziza" in response.content
        assert b"Bekzod" not in response.content

        # So'rov tugadi. Endi AYNAN SHU ulanishda, kontekstsiz.
        visible = _sql("SELECT count(*) FROM child")[0][0]
        assert visible == 0, (
            f"Kontekstsiz soʻrov {visible} ta bolani koʻrdi. Kutilgan: 0. "
            "Ulanishda oldingi soʻrovning tashkiloti qolib ketgan."
        )

    def test_the_boundary_also_closes_platform_mode(self, tenant_a):
        """
        Tashkilot yetarli emas — platforma rejimi ham tozalanishi shart.

        `app.platform` ning oqib ketishi `app.organization_id` nikidan
        yomonroq: u bitta tenantni emas, BARCHA tashkilotlarning
        metama'lumotini ochadi. Shuning uchun so'rov chegarasi uchala
        GUC'ni ham oladi.
        """
        enable_platform_mode()  # biror yo'l uni ochiq qoldirgan holatni taqlid qilamiz

        assert tenant_a.client().get("/api/v1/children").status_code == 200

        with connection.cursor() as cursor:
            cursor.execute("SELECT app_is_platform()")
            assert cursor.fetchone()[0] is False, (
                "Platforma rejimi soʻrovdan keyin ham ochiq qoldi."
            )

    def test_clearing_the_tenant_must_not_close_platform_mode(self, tenant_a):
        """
        `clear_tenant_setting()` va `clear_request_settings()` ATAYLAB har xil.

        Birinchisi faqat tashkilotni oladi, chunki `organization_context()`
        `platform_context()` ICHIDA ishlatiladi (masalan fon vazifalari
        tashkilotlar bo'ylab aylanganda). Agar u platforma rejimini ham
        o'chirsa, tashqi kontekst ichkarisi chiqishi bilan buzilardi.

        Bu test shu farqni qulflaydi: kimdir ikki funksiyani "soddalashtirib"
        bittaga qo'shsa, shu yerda qizaradi.
        """
        with platform_context():
            with organization_context(tenant_a.organization.id):
                pass

            with connection.cursor() as cursor:
                cursor.execute("SELECT app_is_platform()")
                assert cursor.fetchone()[0] is True, (
                    "Ichki `organization_context` chiqishi tashqi platforma "
                    "rejimini oʻchirib yubordi — nesting buzilgan."
                )
