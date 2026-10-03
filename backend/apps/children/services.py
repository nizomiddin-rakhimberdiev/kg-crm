"""
Bolalar domenining biznes mantiqi — mutatsiyalar faqat shu yerda (P3).
"""

from __future__ import annotations

from datetime import date, timedelta
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
    EnrollmentStatus,
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
    "change_status",
    "is_billable_for",
    "archive_child",
    "restore_child",
    "delete_child",
    "deletion_blockers",
    "CLOSED_STATUSES",
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
    language: str = "",
) -> Guardian:
    """
    Telefon bo'yicha vasiyni topadi yoki yaratadi.

    Import va ikkinchi farzandni qo'shishda takroriy vasiy yaratilmasligi
    uchun: bitta oilaning ikki bolasi bir xil onaga bog'lanishi kerak,
    ikkita alohida yozuvga emas (docs/03 §11.2).
    """
    existing = Guardian.objects.filter(branch=branch, phone=phone, is_active=True).first()
    if existing:
        # Mavjud vasiyning tilini faqat YANGI qiymat berilganda
        # yangilaymiz: ikkinchi farzandni qo'shayotganda bo'sh qiymat
        # avval tanlangan tilni o'chirib yuborardi (PLAN 3.4).
        if language and existing.language != language:
            existing.language = language
            existing.save(update_fields=["language", "updated_at"])
        return existing
    return Guardian.objects.create(
        organization=organization,
        branch=branch,
        phone=phone,
        first_name=first_name,
        last_name=last_name,
        email=email,
        language=language,
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
            gettext("'{name}' guruhi toʻlgan ({active_count}/{capacity}).").format(
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


# --- Holat va arxiv (PLAN 2.1, 2.2; Q5, Q6) ---

#: Shu holatlardan keyin hisob-faktura yozilmaydi.
CLOSED_STATUSES = (
    EnrollmentStatus.PAUSED,
    EnrollmentStatus.GRADUATED,
    EnrollmentStatus.WITHDRAWN,
)

#: Xato yozuvni o'chirish oynasi (Q6).
DELETE_WINDOW = timedelta(hours=24)


@transaction.atomic
def change_status(
    *,
    child: Child,
    status: str,
    on_date: date,
    reason: str,
    actor: Any = None,
) -> Child:
    """
    Bolaning holatini SANA va SABAB bilan o'zgartiradi (Q5).

    Ikkalasi ham majburiy va bu ataylab: "Chiqib ketgan" degan holat
    o'zi hech narsa demaydi. Savol har doim pul bilan birga keladi —
    "qachondan buyon?" — chunki o'sha sanadan keyin hisob-faktura
    yozilmasligi kerak.

    Joriy oy uchun kredit **avtomatik emas** (Q5): u alohida, tasdiqli
    amal. Bola oyning 25-kunida ketgan bo'lsa ham, bog'cha o'sha oyni
    to'liq olishi mumkin — bu shartnoma masalasi, tizimning qarori emas.
    """
    if status not in EnrollmentStatus.values:
        raise BusinessRuleViolation(gettext("Nomaʼlum holat."))
    if not reason.strip():
        raise BusinessRuleViolation(gettext("Holatni oʻzgartirish uchun sabab yozing."))
    if on_date > timezone.localdate():
        raise BusinessRuleViolation(gettext("Sana kelajakda boʻla olmaydi."))

    child.enrollment_status = status
    child.status_changed_on = on_date
    child.status_reason = reason.strip()[:255]
    child.save(
        update_fields=["enrollment_status", "status_changed_on", "status_reason", "updated_at"]
    )

    # Guruhdan ham chiqariladi: "chiqib ketgan" bola davomat
    # ro'yxatida turishi tarbiyachini chalkashtiradi.
    if status in CLOSED_STATUSES:
        for enrollment in child.enrollments.filter(status=EnrollmentState.ACTIVE):
            # Holat sanasi guruhga qo'shilgan kundan OLDIN bo'lishi
            # mumkin (orqaga sanab yozilgan chiqish). Bola guruhdan
            # qo'shilmasdan oldin chiqa olmaydi — a'zolik boshlangan
            # kunida yopiladi. Aks holda `ck_enrollment_dates` buzilib,
            # foydalanuvchi ma'nosiz 409 ko'rardi. Hisob-faktura
            # qarori bola holatining sanasidan (`is_billable_for`), bu
            # yerdan emas — ya'ni pulga ta'siri yo'q.
            end_enrollment(enrollment=enrollment, end_date=max(on_date, enrollment.start_date))

    return child


def is_billable_for(child: Child, *, period_year: int, period_month: int) -> bool:
    """
    Shu davr uchun hisob-faktura yozilishi kerakmi?

    Holat yopiq va o'zgarish sanasi davr boshidan OLDIN bo'lsa —
    yo'q. Oy o'rtasida ketgan bolaga esa o'sha oy uchun hujjat
    yoziladi: u oyning bir qismida bog'chada bo'lgan, va pulni
    qaytarish — alohida qaror (Q5).
    """
    if child.enrollment_status not in CLOSED_STATUSES:
        return True
    if child.status_changed_on is None:
        return False
    return child.status_changed_on >= date(period_year, period_month, 1)


@transaction.atomic
def archive_child(*, child: Child, actor: Any = None, reason: str = "") -> Child:
    """
    Bolani arxivga oladi (Q6) — o'chirmaydi.

    Arxivlangan bola ro'yxatlardan chiqadi, lekin uning hisob-fakturasi,
    to'lovi va davomati joyida qoladi: ular bog'chaning moliyaviy
    tarixi va ularni yo'qotish hisobotni buzardi.
    """
    if child.archived_at is not None:
        return child
    child.archived_at = timezone.now()
    child.archived_by = actor
    child.is_active = False
    if reason.strip():
        child.status_reason = reason.strip()[:255]
    child.save(
        update_fields=["archived_at", "archived_by", "is_active", "status_reason", "updated_at"]
    )
    return child


@transaction.atomic
def restore_child(*, child: Child) -> Child:
    """Arxivdan qaytaradi — xato arxivlash tuzatilishi kerak."""
    child.archived_at = None
    child.archived_by = None
    child.is_active = True
    child.save(update_fields=["archived_at", "archived_by", "is_active", "updated_at"])
    return child


def deletion_blockers(child: Child) -> list[str]:
    """
    Bolani QATTIQ o'chirishga to'sqinlik qiladigan sabablar (Q6).

    Bo'sh ro'yxat — o'chirish mumkin. Istisno tor: moliyaviy yozuvi
    yo'q va 24 soat ichida yaratilgan yozuv. Ya'ni "ism noto'g'ri
    yozildi, qaytadan kiritaman" degan holat — va faqat o'sha.
    """
    from apps.attendance.models import AttendanceRecord
    from apps.finance.models import ChildLedgerEntry, Invoice, Payment

    blockers: list[str] = []
    if Invoice.objects.filter(child=child).exists():
        blockers.append(gettext("hisob-faktura"))
    if Payment.objects.filter(child=child).exists():
        blockers.append(gettext("toʻlov"))
    if ChildLedgerEntry.objects.filter(child=child).exists():
        blockers.append(gettext("moliyaviy yozuv"))
    if AttendanceRecord.objects.filter(child=child).exists():
        blockers.append(gettext("davomat"))
    if timezone.now() - child.created_at > DELETE_WINDOW:
        blockers.append(gettext("24 soatdan eski yozuv"))
    return blockers


@transaction.atomic
def delete_child(*, child: Child, actor: Any = None) -> None:
    """
    Xato kiritilgan yozuvni butunlay o'chiradi (Q6).

    Bu YAGONA qattiq o'chirish yo'li va u ataylab tor: bolalar
    o'chirilmaydi, arxivlanadi. Lekin "TEST Sinov" deb yozib yuborilgan
    yozuvni abadiy ro'yxatda saqlash ham to'g'ri emas.

    Audit izi qoladi — chaqiruvchi `audit.record()` ni yozadi.
    """
    blockers = deletion_blockers(child)
    if blockers:
        raise BusinessRuleViolation(
            gettext(
                "Bu bolani oʻchirib boʻlmaydi ({reasons}). Uni ARXIVGA oling — "
                "maʼlumot saqlanadi, roʻyxatlardan chiqadi."
            ).format(reasons=", ".join(blockers))
        )
    child.guardian_links.all().delete()
    child.enrollments.all().delete()
    child.delete()
