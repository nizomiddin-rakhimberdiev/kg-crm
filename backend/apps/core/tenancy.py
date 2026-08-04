"""
Tenant (tashkilot) konteksti — P10 ning yuragi.

Joriy so'rovning tashkiloti `ContextVar` da saqlanadi va uni `TenantManager`
avtomatik o'qiydi. Shunday qilib har bir so'rov filtri **umumiy base queryset**
darajasida qo'llanadi, ya'ni yangi endpoint yozgan dasturchi uni "unutishi"
mumkin emas (docs/02 §11.3).

`ContextVar` tanlandi, `threading.local` emas: u async view va Celery
vazifalarida ham to'g'ri ishlaydi va kontekst tasodifan oqib ketmaydi.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token

__all__ = [
    "TenantScopeMissing",
    "platform_context",
    "auth_lookup_context",
    "get_current_organization_id",
    "set_current_organization_id",
    "organization_context",
    "clear_current_organization",
]


class TenantScopeMissing(RuntimeError):
    """
    Tenant konteksti o'rnatilmagan holda tenant-scoped so'rov bajarildi.

    Bu ataylab **xato** — jimgina bo'sh natija qaytarish xavfliroq, chunki u
    haqiqiy tenant xatosini yashiradi va keyinchalik "nega ma'lumot yo'q?"
    degan noto'g'ri diagnostikaga olib keladi. Ataylab kontekstsiz o'qish
    kerak bo'lsa — `.unscoped()` ishlatiladi va u grep bilan topiladi.
    """


_current_organization_id: ContextVar[uuid.UUID | None] = ContextVar(
    "current_organization_id", default=None
)


def get_current_organization_id() -> uuid.UUID | None:
    """Joriy tashkilot ID'si yoki `None`."""
    return _current_organization_id.get()


def set_current_organization_id(organization_id: uuid.UUID | None) -> Token:
    """Joriy tashkilotni o'rnatadi. Qaytgan token bilan tiklash mumkin."""
    return _current_organization_id.set(organization_id)


def clear_current_organization() -> None:
    """Kontekstni tozalaydi (middleware so'rov oxirida chaqiradi)."""
    _current_organization_id.set(None)


@contextmanager
def organization_context(organization_id: uuid.UUID | str | None) -> Iterator[None]:
    """
    Vaqtinchalik tenant konteksti.

    Celery vazifalari va testlar uchun asosiy kirish nuqtasi::

        with organization_context(org.id):
            Child.objects.count()

    Bu yerda **ikkita** qatlam bir vaqtda o'rnatiladi:
      1. `ContextVar` — ilova qatlamidagi filtr (`TenantManager`) uchun,
      2. Postgres GUC `app.organization_id` — RLS siyosatlari uchun
         (docs/03 §6.3).

    Ikkalasi bitta joyda, chunki ular bitta savolga javob beradi: "hozir
    qaysi tashkilot?" Ularni ajratish "ORM to'g'ri, baza noto'g'ri
    tenantda" degan holatni mumkin qilardi.

    Chiqishda GUC ALBATTA tozalanadi: ulanish puldan qaytadi va keyingi
    so'rov oldingi tenantning qiymatini meros qilib olmasligi kerak.
    """
    from apps.core.rls import apply_tenant_setting, clear_tenant_setting

    # Celery argumentlari JSON, ya'ni UUID satr sifatida keladi —
    # uni shu yerda normallashtirish chaqiruvchilarni bir xil qiladi.
    if isinstance(organization_id, str):
        organization_id = uuid.UUID(organization_id)

    token = _current_organization_id.set(organization_id)
    if organization_id is not None:
        apply_tenant_setting(organization_id)
    try:
        yield
    finally:
        _current_organization_id.reset(token)
        previous = _current_organization_id.get()
        if previous is not None:
            apply_tenant_setting(previous)
        else:
            clear_tenant_setting()


@contextmanager
def platform_context() -> Iterator[None]:
    """
    Tenantlar bo'ylab yuradigan amallar uchun — vendor tekisligi (ADR-10).

    Faqat **metama'lumot** jadvallarini ochadi: tashkilot, obuna,
    hisob-faktura, o'lchov. Bolalar, to'lovlar, davomat platforma
    rejimida ham ko'rinmaydi va buni baza ta'minlaydi (docs/03 §6.3).

    Bu kontekstni OCHIQ so'rash kerak bo'lgani ataylab: cross-tenant
    amal kodda ko'rinib tursin, tasodifan sodir bo'lmasin. Uni qidirish
    ham oson — `grep platform_context`.

    Ishlatiladigan joylar:
      * ro'yxatdan o'tkazish (tashkilot yaratish — hali tenant yo'q),
      * fon vazifalari (barcha tashkilotlar bo'ylab aylanish),
      * platforma konsoli (docs/04 §19).
    """
    from apps.core.rls import disable_platform_mode, enable_platform_mode

    enable_platform_mode()
    try:
        yield
    finally:
        disable_platform_mode()


@contextmanager
def auth_lookup_context() -> Iterator[None]:
    """
    Login uchun tor eshik — faqat `user` va `refresh_token` (docs/03 §6.3).

    Foydalanuvchini email bo'yicha topish AYNAN tenantni aniqlaydigan
    so'rov, ya'ni u o'zi tenant bilan cheklangan bo'la olmaydi. Eshik
    shuning uchun bor — lekin u iloji boricha TOR: bolalar, to'lovlar,
    davomat bu rejimda ham ko'rinmaydi.

    JWT bilan kelgan so'rovda bu umuman ishlatilmaydi: token
    `organization_id` ni o'zi olib yuradi, shuning uchun kontekst
    foydalanuvchini qidirishdan OLDIN o'rnatiladi.
    """
    from apps.core.rls import disable_auth_lookup, enable_auth_lookup

    enable_auth_lookup()
    try:
        yield
    finally:
        disable_auth_lookup()
