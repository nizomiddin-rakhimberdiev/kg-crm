"""
Postgres Row-Level Security — ikkinchi izolyatsiya qatlami (docs/03 §6.3).

Ilova qatlamidagi filtr (`TenantManager`) — birlamchi nazorat va u
ishlaydi. Lekin u **kodga** tayanadi: bitta yangi endpoint, bitta xom
SQL, bitta unutilgan `.filter()` — va bolalar ma'lumoti mijozlar orasida
sizib chiqadi. RLS esa **bazada** turadi va uni kod chetlab o'tolmaydi.

Ishlash tartibi:

    ilova ulanadi (kg_app roli, egasi EMAS)
        → har bir so'rovda `SET app.organization_id = '<uuid>'`
        → Postgres har bir SELECT/INSERT/UPDATE/DELETE ga siyosatni
          qo'shadi: `organization_id = app_current_org()`
        → GUC o'rnatilmagan bo'lsa `app_current_org()` NULL qaytaradi,
          taqqoslash NULL bo'ladi va **hech qanday qator ko'rinmaydi**

Ya'ni sukut bo'yicha holat "hammasi ochiq" emas, "hech narsa ko'rinmaydi".
Xuddi `TenantScopeMissing` kabi — fail-closed.

**Nega ilova egasi rolidan foydalanmaydi:** jadval egasi RLS'ni sukut
bo'yicha CHETLAB O'TADI. Ya'ni siyosat yozib qo'yib, ilovani egasi bilan
ulash — himoya bor deb o'ylab, aslida hech narsa qilmaslik. Migratsiyalar
egasi bilan bajariladi (ularga to'liq kirish kerak), ish vaqtidagi
ulanish esa cheklangan rol bilan.

**Platforma tekisligi (ADR-10):** vendor xodimi metama'lumotni ko'radi —
tashkilot, obuna, hisob-faktura, o'lchov. Bolalar, to'lovlar, davomat
esa unga **bazada ham** ko'rinmaydi: operatsion jadvallarda platforma
uchun hech qanday chiqish yo'li yo'q. Buzilgan platforma akkauntining
ta'sir doirasi — "mijozlar ro'yxatini biladi", "har bir bolaning
yozuvini o'qiydi" emas (docs/04 §19).
"""

from __future__ import annotations

from django.db import DatabaseError, connection

__all__ = [
    "build_policy_sql",
    "build_policy_teardown_sql",
    "policy_sql_for",
    "metadata_policy_sql_for",
    "teardown_sql_for",
    "AUTH_TABLES",
    "OPERATIONAL_TABLES",
    "METADATA_TABLES",
    "DERIVED_TABLES",
    "apply_tenant_setting",
    "clear_tenant_setting",
    "clear_request_settings",
    "enable_platform_mode",
    "disable_platform_mode",
    "enable_auth_lookup",
    "disable_auth_lookup",
]

# Autentifikatsiya jadvallari — TOR eshikli.
#
# Bu tovuq-tuxum holati: foydalanuvchini email bo'yicha topish AYNAN
# tenantni aniqlaydigan so'rov, ya'ni u o'zi tenant bilan cheklangan
# bo'la olmaydi. Eshik shu ikki jadval bilan CHEKLANGAN va alohida GUC
# talab qiladi — ya'ni buzilgan login yo'lining ta'sir doirasi
# "foydalanuvchi qatorlarini o'qiydi", "bolalar yozuvini o'qiydi" emas.
#
# JWT bilan kelgan so'rovda bu eshik umuman ochilmaydi: token
# `organization_id` ni o'zi olib yuradi, shuning uchun kontekst
# foydalanuvchini qidirishdan OLDIN o'rnatiladi.
AUTH_TABLES: tuple[str, ...] = ("user", "refresh_token")

# Operatsion jadvallar — platforma uchun CHIQISH YO'Q.
# Bu ro'yxatning qisqaligi emas, to'liqligi muhim: unutilgan jadval —
# himoyasiz jadval. `test_rls.py` uni modellar ro'yxati bilan solishtiradi.
OPERATIONAL_TABLES: tuple[str, ...] = (
    "absence_claim",
    "attendance_record",
    "branch",
    "cash_account",
    "cash_movement",
    "child",
    "child_guardian",
    "child_ledger_entry",
    "contract",
    "contract_template",
    "discount",
    "dish",
    "dish_ingredient",
    "employee",
    "enrollment",
    "expense",
    "expense_category",
    "expense_item",
    "group",
    "guardian",
    "holiday",
    "insight",
    "invoice",
    "menu_day",
    "menu_item",
    "merchant_credential",
    "notification",
    "online_transaction",
    "notification_template",
    "payment",
    "payment_allocation",
    "payment_link",
    "employee_advance",
    "payroll_item",
    "payroll_payout",
    "payroll_run",
    "position",
    "product",
    "staff_attendance",
    "product_category",
    "report_export",
    "role",
    "stock_movement",
    "supplier",
    "system_setting",
    "tariff_plan",
    "warehouse",
    "audit_log",
)

# Metama'lumot — vendor konsoli shularni ko'radi (docs/04 §19).
METADATA_TABLES: tuple[str, ...] = (
    "organization",
    "subscription",
    "subscription_invoice",
    "subscription_payment",
    "usage_snapshot",
    # Parent bot routing (ADR-27): HMAC digests only, no phone or chat id.
    "contact_index",
    # Radix's merchant transactions for subscription invoices (PLAN 6.4).
    "subscription_online_transaction",
)

# `organization_id` ustuni YO'Q, lekin ota-jadval orqali bog'langan.
# Ular uchun siyosat ichki so'rov bilan yoziladi.
DERIVED_TABLES: dict[str, str] = {
    "invoice_line": "EXISTS (SELECT 1 FROM invoice i WHERE i.id = invoice_line.invoice_id"
    " AND i.organization_id = app_current_org())",
    "role_permission": "EXISTS (SELECT 1 FROM role r WHERE r.id = role_permission.role_id"
    " AND r.organization_id = app_current_org())",
}

# RLS qo'llanmaydigan jadvallar — vendor katalogi (docs/03 §6.2).
# Ular mijoz ma'lumoti emas va barcha tenantlar uchun bir xil.
CATALOGUE_TABLES: tuple[str, ...] = ("permission", "subscription_plan")


def apply_tenant_setting(organization_id: object) -> None:
    """
    Ulanishga joriy tashkilotni yozadi.

    `SET LOCAL` EMAS, oddiy `SET`: Django sukut bo'yicha autocommit
    rejimida ishlaydi va `SET LOCAL` tranzaksiya tashqarisida darhol
    yo'qoladi. Buning evaziga qiymatni chiqishda ALBATTA tozalash kerak —
    aks holda ulanish pulidan keyingi so'rov oldingi tenantning
    qiymatini meros qilib olardi. `clear_tenant_setting()` shuning uchun
    `finally` blokida chaqiriladi.
    """
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config('app.organization_id', %s, false)", [str(organization_id)]
        )


def clear_tenant_setting() -> None:
    """
    Ulanishdagi tenant qiymatini tozalaydi.

    Bu funksiya **kafolat** beradi: chaqiruvdan keyin ulanishda eskirgan
    tashkilot qolmaydi. Uch holat bor va uchalasi ham yopilgan.

    1. Ulanish umuman ochilmagan — tozalaydigan narsa yo'q. Faqat
       tozalash uchun ulanish ochish har bir `404` ga keraksiz baza
       murojaatini qo'shardi.
    2. Ulanish sog'lom — qiymat bo'shatiladi.
    3. Ulanish yaroqsiz holatda (masalan bekor qilingan tranzaksiya, u
       yerda har qanday SQL xato beradi) — u holda ulanishning O'ZI
       yopiladi. Qiymatni o'chira olmaganimizda ulanishni tashlash
       yagona ishonchli yo'l: keyingi so'rov yangi ulanish oladi va u
       toza bo'ladi.
    """
    if connection.vendor != "postgresql":
        return
    if connection.connection is None:
        return
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('app.organization_id', '', false)")
    except DatabaseError:
        connection.close()


def clear_request_settings() -> None:
    """
    So'rov CHEGARASI uchun: uchala kontekst GUC'ini ham bo'shatadi.

    `clear_tenant_setting()` dan farqi ataylab. U faqat tashkilotni
    tozalaydi va shunday bo'lishi SHART: `organization_context()` ni
    `platform_context()` ichida ishlatish mumkin, va ichkarisi
    chiqayotganda tashqi platforma rejimini o'chirib yuborsa, nesting
    buzilardi.

    Bu funksiya esa boshqa savolga javob beradi: "so'rov tugadi, ulanish
    pulga qaytmoqda — unda hech qanday kontekst qolmasin". Shu sababli u
    hammasini oladi. `app.platform` ning oqib ketishi `app.organization_id`
    nikidan ham yomonroq bo'lardi: u metama'lumot jadvallarini butun
    boshli ochadi.

    Uchalasi BITTA murojaatda tozalanadi — so'rovga qo'shiladigan narx
    bitta round-trip, uchta emas.
    """
    if connection.vendor != "postgresql":
        return
    if connection.connection is None:
        return
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('app.organization_id', '', false),"
                "       set_config('app.platform', '', false),"
                "       set_config('app.auth_lookup', '', false)"
            )
    except DatabaseError:
        connection.close()


def enable_auth_lookup() -> None:
    """
    Login uchun tor eshikni ochadi — faqat `user` va `refresh_token`.

    Bolalar, to'lovlar, davomat bu rejimda ham ko'rinmaydi.
    """
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.auth_lookup', 'on', false)")


def disable_auth_lookup() -> None:
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.auth_lookup', '', false)")


def enable_platform_mode() -> None:
    """
    Metama'lumot jadvallarini vendor uchun ochadi.

    Bu **operatsion** jadvallarga ta'sir qilmaydi: bolalar va to'lovlar
    platforma rejimida ham ko'rinmaydi. Siyosat darajasidagi bu ajratish
    ataylab — u "platforma rejimini o'chirishni unutdim" degan xatoning
    narxini keskin kamaytiradi.
    """
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.platform', 'on', false)")


def disable_platform_mode() -> None:
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.platform', '', false)")


# --- Siyosat SQL generatori ---
#
# Migratsiya ham, `check_rls` buyrug'i ham SHU YERDAN oladi. Ikki
# nusxa bo'lsa, ular ertami-kechmi ajralib qolardi — va tekshiruv
# haqiqiy holatni emas, o'zining eski nusxasini tasdiqlardi.
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
    # `to_regclass` himoyasi: jadval hali YO'Q bo'lsa — hech narsa
    # qilinmaydi. Sabab: `core/0002` barcha jadvallarga siyosatni bir
    # yo'la qo'yadi, lekin keyinroq qo'shilgan app (masalan `intelligence`)
    # yangi o'rnatishda undan KEYIN migratsiya qilinadi — o'sha paytda
    # `ALTER TABLE insight` yiqilardi. Bunday jadval siyosatni o'z
    # migratsiyasida `policy_sql_for()` bilan qo'yadi; `check_rls` esa
    # baribir hammasini talab qiladi (docs/07 §10).
    return f"""
DO $$ BEGIN
IF to_regclass('public.{quoted}') IS NOT NULL THEN
    ALTER TABLE {quoted} ENABLE ROW LEVEL SECURITY;
    ALTER TABLE {quoted} FORCE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS tenant_isolation ON {quoted};
    CREATE POLICY tenant_isolation ON {quoted}
        USING ({expression})
        WITH CHECK ({write});
END IF;
END $$;
"""


def _drop(table: str) -> str:
    quoted = _quote(table)
    return f"""
DO $$ BEGIN
IF to_regclass('public.{quoted}') IS NOT NULL THEN
    DROP POLICY IF EXISTS tenant_isolation ON {quoted};
    ALTER TABLE {quoted} NO FORCE ROW LEVEL SECURITY;
    ALTER TABLE {quoted} DISABLE ROW LEVEL SECURITY;
END IF;
END $$;
"""


OPERATIONAL_EXPRESSION = "organization_id = app_current_org()"


def policy_sql_for(table: str) -> str:
    """Bitta operatsion jadval uchun siyosat — kech qo'shilgan app migratsiyasi uchun."""
    return _policy(table, OPERATIONAL_EXPRESSION)


def metadata_policy_sql_for(table: str) -> str:
    """Policy for a late-added METADATA table: own organization, or platform mode."""
    return _policy(table, "organization_id = app_current_org() OR app_is_platform()")


def teardown_sql_for(table: str) -> str:
    return _drop(table)


def build_policy_sql() -> str:
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
    statements.append(_policy("organization", "id = app_current_org() OR app_is_platform()"))

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


def build_policy_teardown_sql() -> str:
    tables = [*OPERATIONAL_TABLES, *METADATA_TABLES, *DERIVED_TABLES, *AUTH_TABLES]
    return "\n".join([*(_drop(table) for table in tables), DROP_FUNCTIONS])
