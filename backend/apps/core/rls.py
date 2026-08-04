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

from django.db import connection

__all__ = [
    "AUTH_TABLES",
    "OPERATIONAL_TABLES",
    "METADATA_TABLES",
    "DERIVED_TABLES",
    "apply_tenant_setting",
    "clear_tenant_setting",
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
    "attendance_record",
    "branch",
    "child",
    "child_guardian",
    "child_ledger_entry",
    "discount",
    "employee",
    "enrollment",
    "expense",
    "expense_category",
    "group",
    "guardian",
    "invoice",
    "notification",
    "notification_template",
    "payment",
    "payroll_item",
    "payroll_run",
    "position",
    "product",
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
    """Ulanishdagi tenant qiymatini tozalaydi."""
    if connection.vendor != "postgresql":
        return
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.organization_id', '', false)")


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
