"""Filiallar bo'yicha o'qish funksiyalari (docs/02 §5 — selectors)."""

from __future__ import annotations

from typing import Any

from django.utils.translation import gettext

from apps.branches.models import Branch
from apps.core.exceptions import BusinessRuleViolation

__all__ = ["resolve_branch"]


def resolve_branch(user: Any, explicit_id: Any = None) -> Branch:
    """
    So'rov uchun filialni aniqlaydi.

    Tartib:
    1. Mijoz aniq ko'rsatgan `branch_id` — lekin faqat O'Z tashkilotidan
       (`Branch.objects` tenant bilan cheklangan, shuning uchun begona ID
       "topilmadi" beradi, `403` emas).
    2. Foydalanuvchining o'z filiali (Org Owner'dan boshqa hammada bor).
    3. Tashkilotda **bitta** filial bo'lsa — o'sha.

    Uchinchi qoida ataylab: aksariyat bog'chada bitta filial bor va Org
    Owner'ni bitta elementli ro'yxatdan tanlashga majburlash onboarding'ga
    keraksiz ishqalanish qo'shardi — aynan biz ishqalanishni yo'qotishimiz
    kerak bo'lgan paytda (docs/01 §3.1, maqsad 13).
    """
    if explicit_id:
        branch = Branch.objects.filter(pk=explicit_id, is_active=True).first()
        if branch is None:
            raise BusinessRuleViolation(gettext("Ko'rsatilgan filial topilmadi."))
        return branch

    if getattr(user, "branch_id", None):
        return user.branch

    candidates = list(Branch.objects.filter(is_active=True)[:2])
    if len(candidates) == 1:
        return candidates[0]

    raise BusinessRuleViolation(
        # Egasi "Barcha filiallar" tanlangan holda yangi yozuv yaratsa shu
        # xato chiqadi. Avval matn `branch_id` deb texnik maydon nomini
        # aytardi — egasi nima qilishni bilmasdi. Endi qadamni aytadi.
        gettext(
            "Bu bog'chada bir nechta filial bor — avval yuqoridagi filial tanlovidan "
            "kerakli filialni tanlang."
        )
    )
