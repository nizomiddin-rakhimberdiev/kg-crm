"""
Delegatsiya qoidasi — hech kim o'zida yo'q huquqni bera olmaydi (ADR-25).

`users.*` ruxsati xodim hisoblari VA rollarni boshqaradi. Bu qoidasiz
`users.update` ega bo'lgan menejer:

  * o'z rolining ruxsatlarini kengaytirib, o'ziga oylik, obuna va
    sozlamalarni ochib olardi;
  * o'zini yoki yangi hisobni "Tashkilot egasi" roliga o'tkazardi;
  * egasi rolining `code` ini o'zgartirib, haqiqiy egani egalikdan
    mahrum qilardi (`is_org_owner` aynan shu kodga qaraydi).

Tashkilotlararo chegara (RLS) bundan buzilmasdi, lekin bog'cha ICHIDA
menejer egaga aylanardi. Qoida bitta: harakat qiluvchi faqat o'zida
BOR ruxsatlar doirasida beradi, tayinlaydi va boshqaradi. Tashkilot
egasi bu cheklovdan tashqarida — u tashkilotning eng yuqori huquqi.

Tekshiruvlar servis qatlamida (invariant 1), view'da emas: rol
tayinlash bir nechta yo'ldan keladi (yaratish, tahrirlash, taklif) va
qoida har birida BIR XIL bo'lishi kerak.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from django.utils.translation import gettext
from rest_framework.exceptions import PermissionDenied

from apps.accounts.constants import OWNER_ROLE_CODE
from apps.accounts.models import Permission

__all__ = [
    "assert_can_assign_branch",
    "assert_can_assign_role",
    "assert_can_edit_role",
    "assert_can_manage_user",
    "can_assign_role",
    "can_edit_role",
]


def _role_codes(role: Any) -> set[str]:
    if role is None:
        return set()
    return set(
        Permission.objects.filter(role_permissions__role_id=role.id).values_list("code", flat=True)
    )


def _deny(message: str) -> PermissionDenied:
    return PermissionDenied(message)


def _widens_payment_scope(actor: Any, role: Any) -> bool:
    """
    "Faqat o'z to'lovlari" bilan cheklangan odam cheklanmagan rolni
    berib yoki tahrirlab, ko'proq ko'rishni uzata olmaydi (ADR-25, ADR-30).

    Ruxsat kodlari bir xil bo'lsa ham, bayroqsiz rol ko'proq ko'radi —
    shuning uchun bu kodlar to'plamidan alohida tekshiriladi.
    """
    mine = getattr(actor, "role", None)
    return bool(
        mine is not None
        and mine.payments_own_only
        and not getattr(role, "payments_own_only", False)
    )


def can_assign_role(
    actor: Any,
    role: Any,
    *,
    actor_codes: set[str] | None = None,
    role_codes: set[str] | None = None,
) -> bool:
    """
    Ro'yxatlar uchun — tayinlash mumkinmi (istisno ko'tarmaydi).

    `actor_codes`/`role_codes` — oldindan hisoblangan to'plamlar: ro'yxatda
    har bir qator uchun bazaga qayta borilmasin.
    """
    if actor.is_org_owner:
        return True
    if role.code == OWNER_ROLE_CODE or _widens_payment_scope(actor, role):
        return False
    mine = actor_codes if actor_codes is not None else actor.permission_codes()
    theirs = role_codes if role_codes is not None else _role_codes(role)
    return theirs <= mine


def can_edit_role(
    actor: Any,
    role: Any,
    *,
    actor_codes: set[str] | None = None,
    role_codes: set[str] | None = None,
) -> bool:
    """`assert_can_edit_role` ning istisnosiz shakli (yangi ruxsatlarsiz)."""
    if actor.is_org_owner:
        return True
    if (
        role.code == OWNER_ROLE_CODE
        or actor.role_id == role.id
        or _widens_payment_scope(actor, role)
    ):
        return False
    mine = actor_codes if actor_codes is not None else actor.permission_codes()
    theirs = role_codes if role_codes is not None else _role_codes(role)
    return theirs <= mine


def assert_can_assign_role(actor: Any, role: Any) -> None:
    """Hisobga rol berish: rol ruxsatlari harakat qiluvchinikidan oshmasin."""
    if actor.is_org_owner:
        return
    if role.code == OWNER_ROLE_CODE:
        raise _deny(gettext("Tashkilot egasi rolini faqat tashkilot egasi bera oladi."))
    if _widens_payment_scope(actor, role):
        raise _deny(
            gettext(
                "Siz faqat oʻzingiz qabul qilgan toʻlovlarni koʻrasiz — "
                "bu cheklovsiz rolni bera olmaysiz."
            )
        )
    extra = _role_codes(role) - actor.permission_codes()
    if extra:
        raise _deny(
            gettext(
                "Bu rolda sizda yoʻq ruxsatlar bor, shuning uchun uni bera olmaysiz: {codes}."
            ).format(codes=", ".join(sorted(extra)))
        )


def assert_can_assign_branch(actor: Any, branch: Any) -> None:
    """
    Filialga bog'langan foydalanuvchi faqat O'Z filialiga xodim qo'sha oladi.

    Aks holda u boshqa filialda hisob ochib, o'sha filialning ma'lumotiga
    o'zi kira olmasa ham, kira oladigan odamni yaratardi.
    """
    if actor.is_org_owner:
        return
    if branch is None or branch.id != actor.branch_id:
        raise _deny(gettext("Faqat oʻz filialingizga xodim qoʻsha olasiz."))


def assert_can_manage_user(actor: Any, target: Any) -> None:
    """Hisobni tahrirlash, o'chirish, parolini tiklash."""
    if actor.is_org_owner:
        return
    if target.id == actor.id:
        # O'z ismi, telefoni va paroli — Profil sahifasida (`/auth/me`).
        # Bu yo'l orqali o'z rolini yoki filialini o'zgartirish mumkin emas.
        raise _deny(gettext("Oʻz hisobingizni Profil sahifasida tahrirlang."))
    if target.is_org_owner:
        raise _deny(gettext("Tashkilot egasining hisobini faqat egasi boshqara oladi."))
    if _role_codes(target.role) - actor.permission_codes():
        raise _deny(gettext("Sizdan kengroq huquqli xodimning hisobini boshqara olmaysiz."))


def assert_can_edit_role(actor: Any, role: Any, new_codes: Iterable[str] | None = None) -> None:
    """
    Rolni tahrirlash, o'chirish yoki ruxsatlarini o'rnatish.

    Uch shart: o'z roli emas (o'z-o'ziga huquq berish), egasi roli emas,
    va rolning HOZIRGI va YANGI ruxsatlari ham harakat qiluvchinikidan
    oshmaydi — yuqoriroq rolni "kamaytirib" ham bo'lmaydi, u ham
    boshqaruv.
    """
    if actor.is_org_owner:
        return
    if role.code == OWNER_ROLE_CODE:
        raise _deny(gettext("Tashkilot egasi rolini faqat tashkilot egasi oʻzgartira oladi."))
    if actor.role_id == role.id:
        raise _deny(gettext("Oʻz rolingizning ruxsatlarini oʻzgartira olmaysiz."))
    if _widens_payment_scope(actor, role):
        raise _deny(gettext("Sizdan kengroq huquqli rolni oʻzgartira olmaysiz."))
    mine = actor.permission_codes()
    if _role_codes(role) - mine:
        raise _deny(gettext("Sizdan kengroq huquqli rolni oʻzgartira olmaysiz."))
    if new_codes is not None:
        extra = set(new_codes) - mine
        if extra:
            raise _deny(
                gettext("Sizda yoʻq ruxsatlarni bera olmaysiz: {codes}.").format(
                    codes=", ".join(sorted(extra))
                )
            )
