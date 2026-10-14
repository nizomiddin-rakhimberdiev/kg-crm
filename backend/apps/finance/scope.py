"""
"Faqat o'zi qabul qilgan to'lovlar" doirasi (mijoz so'rovi, 2026-10-14; ADR-30).

`children/scope.py` bilan bir xil fikr: modul × amal RBAC'i "to'lovlarni
o'qiy oladimi?" degan savolga javob beradi, bu modul esa "QAYSI
to'lovlarni?" degan ikkinchi savolga. Kassirga to'lov doskasi kerak —
demak `payments.read` qoladi; lekin boshqa kassirlar qabul qilgan pul va
oyning umumiy tushumi unga tegishli emas.

Cheklov rolning ANIQ bayrog'idan keladi (`Role.payments_own_only`),
ruxsat yo'qligidan emas (14-invariant). Bayroq qo'yilmagan har qanday
rol — direktor, buxgalter, bog'cha o'zi yasagan rollar — hech narsa
sezmaydi.
"""

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet

__all__ = ["payments_own_only", "restrict_payments"]


def payments_own_only(user: Any) -> bool:
    """Foydalanuvchi faqat o'z to'lovlari bilan cheklanganmi? Egasi — hech qachon."""
    if getattr(user, "is_org_owner", False):
        return False
    role = getattr(user, "role", None)
    return bool(role is not None and role.payments_own_only)


def restrict_payments(queryset: QuerySet[Any], user: Any) -> QuerySet[Any]:
    """Cheklangan foydalanuvchi uchun — faqat `received_by = o'zi`."""
    if payments_own_only(user):
        return queryset.filter(received_by_id=user.id)
    return queryset
