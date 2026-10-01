"""
Qator darajasidagi doira — tarbiyachi faqat o'z guruhlarini ko'radi (PLAN 2.6).

Loyihadagi RBAC **modul × amal** darajasida ishlaydi: "davomat o'qiy
oladimi?" degan savolga javob beradi, "QAYSI guruhning davomatini?"
degan savolga esa yo'q. Tarbiyachi uchun ikkinchi savol muhim: bog'chada
olti guruh bo'lsa, u beshtasining bolalarini ko'rishi ham, ularning
davomatini belgilashi ham kerak emas.

Bu modul mavjud RBAC'ni O'ZGARTIRMAYDI — ustiga qo'shimcha qatlam
qo'yadi. Modul ruxsati avvalgidek birinchi to'siq; bu esa ikkinchisi.
Shuning uchun eski rollar (egasi, direktor, buxgalter) hech narsa
sezmaydi: ular guruhga bog'lanmagan, demak cheklov ham tegmaydi.

Doira **xodim orqali** aniqlanadi (`user.employee` → `group.teacher`),
chunki tarbiyachi avvalo xodim: uning oyligi va shartnomasi bor, tizim
hisobi esa ixtiyoriy.
"""

from __future__ import annotations

from typing import Any

from apps.children.models import Enrollment, EnrollmentState, Group

__all__ = [
    "is_group_restricted",
    "visible_group_ids",
    "can_touch_group",
    "restrict_children",
    "restrict_groups",
]


def is_group_restricted(user: Any) -> bool:
    """
    Foydalanuvchi faqat o'z guruhlari bilan cheklanganmi?

    Uch shart, va ularning TARTIBI muhim:

    1. Tashkilot egasi — hech qachon cheklanmaydi.
    2. `children.read_all` ruxsati bor — cheklanmaydi. Bu barcha tizim
       rollarida bor, ya'ni mavjud rollar hech narsa sezmaydi.
    3. **Birorta guruhning tarbiyachisi emas — cheklanmaydi.**

    Uchinchi shart ataylab: cheklov "ruxsati yo'q" degan sababdan EMAS,
    "u aynan shu guruhlarning tarbiyachisi" degan sababdan kelib
    chiqadi. Aks holda ruxsatlari tor har qanday maxsus rol (masalan
    tashqaridan kelgan buxgalter) kutilmaganda hech narsa ko'rmay
    qolardi — hech kim bunday qaror qabul qilmagan holda.

    Ya'ni: hech kim kimnidir guruhga tarbiyachi qilib biriktirmaguncha
    bu qatlam umuman ishlamaydi.
    """
    if getattr(user, "is_org_owner", False):
        return False
    codes = user.permission_codes() if hasattr(user, "permission_codes") else set()
    if "children.read_all" in codes:
        return False
    return bool(visible_group_ids(user))


def visible_group_ids(user: Any) -> set[Any]:
    """Foydalanuvchi tarbiyachisi bo'lgan guruhlar."""
    employee_id = getattr(getattr(user, "employee", None), "id", None)
    if employee_id is None:
        return set()
    return set(Group.objects.filter(teacher_id=employee_id).values_list("id", flat=True))


def can_touch_group(user: Any, group: Any) -> bool:
    """Shu guruhga tegishi mumkinmi (o'qish ham, yozish ham)?"""
    if not is_group_restricted(user):
        return True
    return group.id in visible_group_ids(user)


def restrict_children(queryset: Any, user: Any) -> Any:
    """
    Bolalar ro'yxatini tarbiyachining guruhlari bilan cheklaydi.

    Cheklanmagan foydalanuvchiga queryset o'zgarmay qaytadi — ya'ni
    chaqiruvchi shart yozishi shart emas va "shartni unutish" xatosi
    tuzilishi bo'yicha mumkin emas.
    """
    if not is_group_restricted(user):
        return queryset
    groups = visible_group_ids(user)
    if not groups:
        return queryset.none()
    child_ids = Enrollment.objects.filter(
        group_id__in=groups, status=EnrollmentState.ACTIVE, end_date__isnull=True
    ).values_list("child_id", flat=True)
    return queryset.filter(id__in=child_ids)


def restrict_groups(queryset: Any, user: Any) -> Any:
    """Guruhlar ro'yxatini ham cheklaydi."""
    if not is_group_restricted(user):
        return queryset
    return queryset.filter(id__in=visible_group_ids(user))
