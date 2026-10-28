"""
Bolani qidirish — BITTA taʼrif (mijoz soʻrovi, 2026-10-28).

Mijoz "asosiyda ham, bolalarda ham, toʻlovlar va qarzdorliklarda ham"
ism, shartnoma raqami yoki ID boʻyicha qidirishni soʻradi. Sabab
amaliy: kassir qoʻlida qogʻoz shartnoma turadi, ekranda esa faqat ism
boʻyicha qidirish bor edi — bir xil familiyali uchta bola orasidan
toʻgʻrisini topish uchun har birini ochib koʻrish kerak boʻlardi.

Taʼrif shu yerda YAKKA: uch ekran uchta boshqa javob bersa, xodim
qaysi biriga ishonishni bilmaydi. Ism boʻyicha qidiruv `search_key`
orqali ketadi (PLAN 2.7) — "Улугбек" deb yozilgan soʻrov "Ulugʻbek" ni
ham topadi, apostrof va alifbo farqi esa yoʻqoladi.
"""

from __future__ import annotations

import contextlib
import uuid

from django.db.models import Q

from apps.core import translit

__all__ = ["child_search"]


def child_search(term: str) -> Q:
    """Ism, familiya, shartnoma raqami yoki ID boʻyicha filtr."""
    cleaned = (term or "").strip()
    if not cleaned:
        return Q()

    found = Q(search_key__contains=translit.search_key(cleaned))
    # Shartnoma raqami qogʻozdan koʻchiriladi: registr va oraliq boʻshliq
    # odamning ishi emas.
    found |= Q(contract_number__icontains=cleaned)
    # ID emas boʻlishi — xato emas, odatiy hol: odam koʻpincha ism yozadi.
    with contextlib.suppress(ValueError, AttributeError, TypeError):
        found |= Q(id=uuid.UUID(cleaned))
    return found
