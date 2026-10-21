"""
Audit jurnalidagi UUID'larni NOMGA aylantiradi (PLAN 4.4).

Auditda jurnal shunday ko'rinardi::

    Yangilandi  child  child: "4f3c9e21-…", group: "9a1b7c04-…"

Bu yozuv formal jihatdan to'g'ri va amalda foydasiz: "kim nima
qildi?" degan savolga javob berish uchun har bir UUID'ni qo'lda
qidirish kerak. Jurnal esa aynan shu savol uchun bor.

**Nega bu yerda `apps.get_model`.** Audit — kesib o'tuvchi
(cross-cutting) modul: u HAMMA modulning hodisasini yozadi, ya'ni
ularning har biriga bog'lanib bo'lmaydi (CLAUDE.md, invariant 1).
Shuning uchun bu yerda faqat **ko'rsatiladigan nom** o'qiladi va
o'qish kechiktirilgan (`apps.get_model`) — biznes mantiq emas,
import ham emas. Ro'yxat ataylab yopiq: faqat shu yerda sanalgan
turlar hal qilinadi, qolgani UUID bo'lib qoladi (va bu xato emas —
jurnalda yozuv baribir turadi).

Nomlar BIR SO'ROVDA olinadi: 50 qatorli jurnalda qator-qator so'rash
50 ta so'rovga aylanardi.
"""

from __future__ import annotations

import uuid
from typing import Any

from django.apps import apps as django_apps

__all__ = ["ENTITY_MODELS", "KEY_ENTITY", "entity_for_key", "resolve_labels", "label_map_for"]

#: `entity_type` / `changes` kaliti → (app, model). Nom `str(obj)` dan
#: olinadi: har bir modelning `__str__` i allaqachon "odam o'qiydigan
#: nom" sifatida yozilgan va ikkinchi marta ta'riflash ularni
#: ajralib ketishga qoldirardi.
ENTITY_MODELS: dict[str, tuple[str, str]] = {
    "child": ("children", "Child"),
    "group": ("children", "Group"),
    "guardian": ("children", "Guardian"),
    "enrollment": ("children", "Enrollment"),
    "tariff": ("finance", "Tariff"),
    "invoice": ("finance", "Invoice"),
    "payment": ("finance", "Payment"),
    "discount": ("finance", "Discount"),
    "cash_account": ("cash", "CashAccount"),
    "expense": ("expenses", "Expense"),
    "product": ("inventory", "Product"),
    "employee": ("hr", "Employee"),
    "user": ("accounts", "User"),
    "role": ("accounts", "Role"),
    "branch": ("branches", "Branch"),
    "organization": ("organizations", "Organization"),
}


#: (`entity_type`, `changes` kaliti) → nom olinadigan tur.
#:
#: Ba'zi kalitlar turni O'ZI aytmaydi: qopdan qopga o'tkazma `from` va
#: `to` deb yoziladi, va jurnalda "c28a8dc0-… → 617524bc-…" turardi
#: (audit, 2026-10-21). Kalit aytmaganini YOZUV TURI aytadi:
#: `cash_transfer` ning `from`/`to` si doimo kassa hisobi.
KEY_ENTITY: dict[tuple[str, str], str] = {
    ("cash_transfer", "from"): "cash_account",
    ("cash_transfer", "to"): "cash_account",
    ("cash_handover", "to"): "user",
    ("cash_count", "cash_account"): "cash_account",
}


def entity_for_key(entity_type: str, key: str) -> str | None:
    """
    `changes` kaliti qaysi turning nomini talab qiladi.

    Uch qoida, shu tartibda: kalitning o'zi tur nomi (`child`),
    yozuv turi bilan birga ma'no beradigan kalit (`KEY_ENTITY`), yoki
    `_id` qo'shimchasi (`employee_id` → `employee`). Qolgani UUID
    bo'lib qoladi — bu xato emas, yozuv baribir o'z joyida.
    """
    if key in ENTITY_MODELS:
        return key
    hinted = KEY_ENTITY.get((entity_type, key))
    if hinted is not None:
        return hinted
    if key.endswith("_id") and key[:-3] in ENTITY_MODELS:
        return key[:-3]
    return None


def _is_uuid(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        uuid.UUID(value)
    except (ValueError, AttributeError):
        return False
    return True


def label_map_for(entity: str, ids: set[str]) -> dict[str, str]:
    """Bitta tur uchun `{uuid: nom}` — bitta so'rovda."""
    target = ENTITY_MODELS.get(entity)
    if not target or not ids:
        return {}
    model = django_apps.get_model(*target)
    # `objects` tenant bilan cheklangan: begona tashkilotning nomi bu
    # yerda ham ko'rinmaydi, ya'ni jurnal tenant chegarasini buzmaydi.
    rows = model.objects.filter(pk__in=ids)
    return {str(row.pk): str(row) for row in rows}


def resolve_labels(entries: list[Any]) -> dict[str, dict[str, str]]:
    """
    Jurnal qatorlari uchun hamma nomni yig'adi.

    Javob: `{entity_type: {uuid: nom}}`. Har bir tur uchun BITTA
    so'rov — qator-qator so'rash 50 qatorli sahifada 50 ta so'rov
    bo'lardi.
    """
    wanted: dict[str, set[str]] = {}

    for entry in entries:
        entity = getattr(entry, "entity_type", "") or ""
        entity_id = getattr(entry, "entity_id", None)
        if entity in ENTITY_MODELS and entity_id:
            wanted.setdefault(entity, set()).add(str(entity_id))

        for key, value in (getattr(entry, "changes", None) or {}).items():
            if not _is_uuid(value):
                continue
            target = entity_for_key(entity, key)
            if target is not None:
                wanted.setdefault(target, set()).add(str(value))

    return {entity: label_map_for(entity, ids) for entity, ids in wanted.items()}
