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
def organization_context(organization_id: uuid.UUID | None) -> Iterator[None]:
    """
    Vaqtinchalik tenant konteksti.

    Celery vazifalari va testlar uchun asosiy kirish nuqtasi::

        with organization_context(org.id):
            Child.objects.count()
    """
    token = _current_organization_id.set(organization_id)
    try:
        yield
    finally:
        _current_organization_id.reset(token)
