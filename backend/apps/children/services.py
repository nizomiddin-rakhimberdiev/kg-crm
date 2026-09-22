"""
Bolalar domenining biznes mantiqi — mutatsiyalar faqat shu yerda (P3).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.translation import gettext

from apps.children.models import (
    Child,
    ChildGuardian,
    Enrollment,
    EnrollmentState,
    Group,
    Guardian,
)
from apps.core.exceptions import BusinessRuleViolation

__all__ = [
    "attach_guardian",
    "enroll_child",
    "end_enrollment",
    "recount_group",
    "upsert_guardian",
]


@transaction.atomic
def upsert_guardian(
    *,
    organization: Any,
    branch: Any,
    phone: str,
    first_name: str,
    last_name: str,
    email: str = "",
) -> Guardian:
    """
    Telefon bo'yicha vasiyni topadi yoki yaratadi.

    Import va ikkinchi farzandni qo'shishda takroriy vasiy yaratilmasligi
    uchun: bitta oilaning ikki bolasi bir xil onaga bog'lanishi kerak,
    ikkita alohida yozuvga emas (docs/03 §11.2).
    """
    existing = Guardian.objects.filter(branch=branch, phone=phone, is_active=True).first()
    if existing:
        return existing
    return Guardian.objects.create(
        organization=organization,
        branch=branch,
        phone=phone,
        first_name=first_name,
        last_name=last_name,
        email=email,
    )


@transaction.atomic
def attach_guardian(
    *,
    child: Child,
    guardian: Guardian,
    relation: str,
    is_primary: bool = False,
    can_pickup: bool = True,
) -> ChildGuardian:
    """Vasiyni bolaga bog'laydi."""
    if guardian.organization_id != child.organization_id:
        raise BusinessRuleViolation(gettext("Vasiy boshqa tashkilotga tegishli."))
    if guardian.branch_id != child.branch_id:
        raise BusinessRuleViolation(gettext("Vasiy boshqa filialga tegishli."))

    if is_primary:
        # Asosiy vasiy bitta bo'ladi. Qisman unikal indeks buni bazada
        # kafolatlaydi, lekin oldingisini AVVAL bo'shatmasak, indeks
        # foydalanuvchiga tushunarsiz xato bilan urib qaytarardi.
        ChildGuardian.objects.filter(child=child, is_primary=True).update(is_primary=False)

    link, _ = ChildGuardian.objects.update_or_create(
        child=child,
        guardian=guardian,
        defaults={
            "organization": child.organization,
            "branch": child.branch,
            "relation": relation,
            "is_primary": is_primary,
            "can_pickup": can_pickup,
        },
    )
    return link


@transaction.atomic
def enroll_child(*, child: Child, group: Group, start_date: date | None = None) -> Enrollment:
    """
    Bolani guruhga yozadi; avvalgi ochiq a'zolikni yopadi.

    Guruh sig'imi qulf ostida tekshiriladi: ikkita parallel yozuv sig'imni
    oshirib yuborishi mumkin va buni `CHECK` ushlay olmaydi — u boshqa
    qatorlarni ko'rmaydi (docs/03 §26).
    """
    if group.organization_id != child.organization_id:
        raise BusinessRuleViolation(gettext("Guruh boshqa tashkilotga tegishli."))
    if group.branch_id != child.branch_id:
        raise BusinessRuleViolation(gettext("Guruh boshqa filialga tegishli."))

    locked = Group.objects.select_for_update().get(pk=group.pk)
    active_count = Enrollment.objects.filter(
        group=locked, status=EnrollmentState.ACTIVE, end_date__isnull=True
    ).count()
    if locked.capacity and active_count >= locked.capacity:
        raise BusinessRuleViolation(
            gettext("'{name}' guruhi to'lgan ({active_count}/{capacity}).").format(
                name=locked.name, active_count=active_count, capacity=locked.capacity
            )
        )

    today = start_date or timezone.localdate()

    # Ochiq a'zolikni yopamiz — aks holda qisman unikal indeks yangi
    # yozuvni rad etardi.
    Enrollment.objects.filter(
        child=child, end_date__isnull=True, status=EnrollmentState.ACTIVE
    ).update(end_date=today, status=EnrollmentState.TRANSFERRED)

    enrollment = Enrollment.objects.create(
        organization=child.organization,
        branch=child.branch,
        child=child,
        group=locked,
        start_date=today,
    )
    recount_group(locked)
    return enrollment


@transaction.atomic
def end_enrollment(*, enrollment: Enrollment, end_date: date | None = None) -> Enrollment:
    enrollment.end_date = end_date or timezone.localdate()
    enrollment.status = EnrollmentState.ENDED
    enrollment.save(update_fields=["end_date", "status", "updated_at"])
    recount_group(enrollment.group)
    return enrollment


def recount_group(group: Group) -> int:
    """
    `enrolled_count` keshini qayta hisoblaydi.

    Kesh hech qachon haqiqat manbai emas (D3) — u faqat ro'yxatlarni tez
    ko'rsatish uchun va istalgan vaqtda enrollment'lardan tiklanadi.
    """
    count = Enrollment.objects.filter(
        group=group, status=EnrollmentState.ACTIVE, end_date__isnull=True
    ).count()
    Group.objects.filter(pk=group.pk).update(enrolled_count=count)
    return count


def group_occupancy(organization_id: Any) -> dict[str, int]:
    """Selector: guruh → faol bolalar soni (bitta so'rovda)."""
    rows = (
        Group.objects.filter(organization_id=organization_id)
        .annotate(
            active=Count(
                "enrollments",
                filter=Q(
                    enrollments__status=EnrollmentState.ACTIVE, enrollments__end_date__isnull=True
                ),
            )
        )
        .values_list("id", "active")
    )
    return {str(gid): count for gid, count in rows}
