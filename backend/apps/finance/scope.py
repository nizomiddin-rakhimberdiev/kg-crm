"""
"Faqat o'zi qabul qilgan to'lovlar" doirasi (ADR-30, 2026-10-14;
2026-10-28 da TORAYTIRILDI).

`children/scope.py` bilan bir xil fikr: modul × amal RBAC'i "to'lovlarni
o'qiy oladimi?" degan savolga javob beradi, bu modul esa "QAYSI
to'lovlarni?" degan ikkinchi savolga.

**Nima o'zgardi.** Dastlab bayroq jurnalni ham yopardi: kassir boshqa
kassirning to'lovini umuman ko'rmasdi. Bog'cha buni amalda sinab
ko'rib fikrini o'zgartirdi — smena almashganda "kecha kim qancha
oldi?" degan savol har kuni beriladi, va u har safar egadan o'tishi
kerak edi. Endi **ko'rish hammaga ochiq**, bayroq esa quyidagilarni
ushlab turadi:

  * oyning umumiy tushumi (doska yig'indisi) — ko'rsatilmaydi;
  * kassirning kunlik hisoboti va yo'ldagi puli — faqat o'ziniki;
  * BOSHQA odamning to'lovini qaytarish, tuzatish yoki fiskal
    qilish — mumkin emas (`PaymentViewSet._assert_mine`).

Cheklov rolning ANIQ bayrog'idan keladi (`Role.payments_own_only`),
ruxsat yo'qligidan emas (14-invariant). Bayroq qo'yilmagan har qanday
rol — direktor, buxgalter, bog'cha o'zi yasagan rollar — hech narsa
sezmaydi.
"""

from __future__ import annotations

from typing import Any

__all__ = ["payments_own_only"]


def payments_own_only(user: Any) -> bool:
    """Foydalanuvchi faqat o'z to'lovlari bilan cheklanganmi? Egasi — hech qachon."""
    if getattr(user, "is_org_owner", False):
        return False
    role = getattr(user, "role", None)
    return bool(role is not None and role.payments_own_only)
