"""
Row-Level Security siyosatlari (docs/03 §6.3).

Bu migratsiya **oxirgi** bo'lishi kerak: u barcha jadvallar mavjud
bo'lgandan keyin siyosat qo'yadi. Shuning uchun har bir app'ning oxirgi
migratsiyasiga bog'langan.

RLS "migratsiya emas, siyosat qo'shish" — aynan shuning uchun u shu
paytda, mavjud ma'lumotni ko'chirmasdan qo'shilyapti. Buning sababi
Sprint 0 da qabul qilingan qaror: `organization_id` BIRINCHI
migratsiyadan beri har bir jadvalda. Tenancy'ni kod yozilishidan oldin
hal qilishning haqiqiy foydasi shu yerda ko'rinadi.
"""

from django.db import migrations

from apps.core.rls import AUTH_TABLES, DERIVED_TABLES, METADATA_TABLES, OPERATIONAL_TABLES

# --- Yordamchi funksiyalar ---
#
# `current_setting(..., true)` — ikkinchi argument "xato bermasin"
# degani: sozlama umuman o'rnatilmagan bo'lsa NULL qaytadi. Shu bilan
# siyosat FAIL-CLOSED bo'ladi: NULL bilan taqqoslash hech qachon `true`
# bermaydi, ya'ni kontekstsiz ulanish hech narsa ko'rmaydi.
FUNCTIONS = """
CREATE OR REPLACE FUNCTION app_current_org() RETURNS uuid AS $$
    SELECT NULLIF(current_setting('app.organization_id', true), '')::uuid;
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION app_is_platform() RETURNS boolean AS $$
    SELECT COALESCE(NULLIF(current_setting('app.platform', true), ''), 'off') = 'on';
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION app_is_auth_lookup() RETURNS boolean AS $$
    SELECT COALESCE(NULLIF(current_setting('app.auth_lookup', true), ''), 'off') = 'on';
$$ LANGUAGE sql STABLE;
"""

DROP_FUNCTIONS = """
DROP FUNCTION IF EXISTS app_current_org();
DROP FUNCTION IF EXISTS app_is_platform();
DROP FUNCTION IF EXISTS app_is_auth_lookup();
"""


def _quote(table: str) -> str:
    """`user` — Postgres'da zaxiralangan so'z."""
    return f'"{table}"'


def _policy(table: str, expression: str, write_expression: str | None = None) -> str:
    """
    `FORCE` ham qo'shiladi — bu qaror ataylab.

    Postgres'da jadval EGASI RLS'ni sukut bo'yicha chetlab o'tadi. Ya'ni
    siyosatlarni yozib qo'yib, ilovani egasi roli bilan ulash — himoya
    bor deb o'ylab, aslida hech narsa qilmaslik demakdir. `FORCE` bu
    teshikni yopadi va qo'shimcha foyda beradi: butun test to'plami
    endi RLS ostida ishlaydi, ya'ni siyosat haqiqatan sinaladi, faqat
    e'lon qilinmaydi.

    Buning narxi: tenantlar bo'ylab yuradigan har bir amal (ro'yxatdan
    o'tkazish, fon vazifalari, platforma konsoli) endi `platform_context()`
    ni OCHIQ so'rashi kerak. Bu ham ataylab — cross-tenant amal
    ko'rinmas bo'lib qolmasligi kerak.
    """
    quoted = _quote(table)
    write = write_expression or expression
    return f"""
ALTER TABLE {quoted} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {quoted} FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON {quoted};
CREATE POLICY tenant_isolation ON {quoted}
    USING ({expression})
    WITH CHECK ({write});
"""


def _drop(table: str) -> str:
    quoted = _quote(table)
    return f"""
DROP POLICY IF EXISTS tenant_isolation ON {quoted};
ALTER TABLE {quoted} NO FORCE ROW LEVEL SECURITY;
ALTER TABLE {quoted} DISABLE ROW LEVEL SECURITY;
"""


def build_forward() -> str:
    statements = [FUNCTIONS]

    # Operatsion jadvallar — platforma uchun chiqish yo'q.
    for table in OPERATIONAL_TABLES:
        if table == "audit_log":
            continue
        statements.append(_policy(table, "organization_id = app_current_org()"))

    # Audit jurnali — O'QISH qat'iy, YOZISH kengroq.
    #
    # Muvaffaqiyatsiz login yozuvida tashkilot YO'Q (kim urinayotganini
    # hali bilmaymiz), platforma harakatlarida ham shunday. Bunday
    # qatorni yozolmaslik aynan eng kerakli dalilni — "kimdir kirishga
    # urindi" — yo'qotardi. Shuning uchun `WITH CHECK` `NULL` ga ruxsat
    # beradi, `USING` esa bermaydi: mijoz o'zining bo'lmagan qatorni
    # hech qachon ko'rmaydi (ADR-10).
    #
    # Platforma esa `organization_id IS NULL` qatorlarni O'QIY oladi —
    # bu xavfsizlik jurnali: "kimdir kirishga urindi" yozuvini hech kim
    # ko'ra olmasa, uni yozishning ma'nosi qolmasdi. Mijozning
    # qatorlari platformaga baribir ko'rinmaydi.
    statements.append(
        _policy(
            "audit_log",
            "organization_id = app_current_org()"
            " OR (app_is_platform() AND organization_id IS NULL)",
            write_expression="organization_id = app_current_org() OR organization_id IS NULL",
        )
    )

    # Tashkilotning o'zi: kalit `id`, `organization_id` emas.
    statements.append(
        _policy("organization", "id = app_current_org() OR app_is_platform()")
    )

    # Qolgan metama'lumot — vendor konsoli ko'radi (docs/04 §19).
    for table in METADATA_TABLES:
        if table == "organization":
            continue
        statements.append(
            _policy(table, "organization_id = app_current_org() OR app_is_platform()")
        )

    # Autentifikatsiya jadvallari — TOR eshik.
    #
    # `user` ni email bo'yicha qidirish tenantni ANIQLAYDIGAN so'rov,
    # ya'ni u o'zi tenant bilan cheklangan bo'la olmaydi. Eshik shu ikki
    # jadval bilan cheklangan va alohida GUC talab qiladi.
    statements.append(
        _policy("user", "organization_id = app_current_org() OR app_is_auth_lookup()")
    )
    statements.append(
        _policy(
            "refresh_token",
            'EXISTS (SELECT 1 FROM "user" u WHERE u.id = refresh_token.user_id'
            " AND u.organization_id = app_current_org()) OR app_is_auth_lookup()",
        )
    )

    # Ota-jadval orqali bog'langanlar.
    for table, expression in DERIVED_TABLES.items():
        statements.append(_policy(table, expression))

    return "\n".join(statements)


def build_backward() -> str:
    tables = [*OPERATIONAL_TABLES, *METADATA_TABLES, *DERIVED_TABLES, *AUTH_TABLES]
    return "\n".join([*(_drop(table) for table in tables), DROP_FUNCTIONS])


class Migration(migrations.Migration):
    # Barcha jadvallar mavjud bo'lgandan KEYIN ishlashi kerak.
    dependencies = [
        ("core", "0001_tenancy_guards"),
        ("accounts", "0005_role_tenancy_guard"),
        ("attendance", "0003_remove_attendancerecord_ck_attendance_not_future_and_more"),
        ("branches", "0002_branch_tenancy_guard"),
        ("children", "0003_child_tariff"),
        ("expenses", "0002_tenancy_guards"),
        ("finance", "0004_payment_tenancy_guard"),
        ("hr", "0002_tenancy_guards"),
        ("inventory", "0002_tenancy_guards"),
        ("notifications", "0002_tenancy_guards"),
        ("organizations", "0001_initial"),
        ("payroll", "0002_tenancy_guards"),
        ("reports", "0001_initial"),
        ("settings_app", "0002_tenancy_guards"),
        ("subscriptions", "0002_seed_launch_plan"),
        ("audit", "0001_initial"),
    ]

    operations = [migrations.RunSQL(sql=build_forward(), reverse_sql=build_backward())]
