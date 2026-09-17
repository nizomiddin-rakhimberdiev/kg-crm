"""
Deploy rejimi — mahsulot bitta, sotuv modeli ikkita (docs/02 ADR-13).

``saas``
    Ko'p ijarachili xizmat: radix-crm.uz, obuna, 15 kunlik sinov,
    vendor konsoli, mijoz manzili ``/t/<slug>``.

``standalone``
    Bitta bog'cha uchun, mijozning O'Z serverida, bir martalik to'lov
    evaziga: obuna ham, tarif ham, sinov muddati ham yo'q; vendor
    tekisligi yo'q; ilova ildizda yashaydi.

Nega bayroq, fork emas: ikki nusxa kod bir hafta ichida ajralib ketadi
va shundan keyin har bir xato ikki marta tuzatiladi. Bu yerda kod
bitta — mijoz serveriga chiqqan tuzatish SaaS'ga ham tegadi, va
teskarisi.

DIQQAT: bu **sotuv** chegarasi, xavfsizlik chegarasi EMAS. Ijarachi
izolyatsiyasi ikki rejimda ham bir xil ishlaydi — ``organization_id``
va Postgres RLS (CLAUDE.md 2- va 8-invariantlar). Standalone bazada
bitta tashkilot bo'lsa ham RLS o'chirilmaydi: "baribir bitta mijoz"
deb siyosatni bo'shatish, ertaga o'sha bazada ikkinchi tashkilot
paydo bo'lganda (masalan ikkinchi bog'chani sotib olgan egasi)
jimgina ma'lumot aralashuviga olib borardi.
"""

from __future__ import annotations

from typing import Final

from django.conf import settings

__all__ = ["SAAS", "STANDALONE", "DEPLOYMENT_MODES", "is_standalone", "is_saas"]

SAAS: Final[str] = "saas"
STANDALONE: Final[str] = "standalone"

DEPLOYMENT_MODES: Final[tuple[str, ...]] = (SAAS, STANDALONE)


def is_standalone() -> bool:
    """Bitta bog'cha uchun alohida o'rnatilgan nusxami?"""
    return str(getattr(settings, "DEPLOYMENT_MODE", SAAS)) == STANDALONE


def is_saas() -> bool:
    """Ko'p ijarachili xizmat nusxasimi?"""
    return not is_standalone()
