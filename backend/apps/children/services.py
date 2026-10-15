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
    phone_alt: str = "",
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
        updated: list[str] = []
        if language and existing.language != language:
            existing.language = language
            updated.append("language")
        # Ikkinchi raqam ham FAQAT berilganda yangilanadi (PLAN 7.4):
        # ikkinchi farzandni qo'shayotganda bo'sh qiymat avval
        # kiritilgan raqamni o'chirib yuborardi.
        if phone_alt and existing.phone_alt != phone_alt:
            existing.phone_alt = phone_alt
            updated.append("phone_alt")
        if updated:
            existing.save(update_fields=[*updated, "updated_at"])
        return existing
    return Guardian.objects.create(
        organization=organization,
        branch=branch,
        phone=phone,
        first_name=first_name,
        last_name=last_name,
        email=email,
        language=language,
        phone_alt=phone_alt,
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

# --- Oila (Bosqich 12.2) ---


def family_of(child: Child) -> list[Child]:
    """
    Bola va umumiy vasiy orqali bog'langan barcha bolalar — o'zi ham ichida.

    Oila FAMILIYA bilan emas, vasiy bilan aniqlanadi (brif §1): Excel'da
    aka-ukalik familiyaga qarab taxmin qilinardi, va ikki xil oilaning bir
    xil familiyali bolalari chegirma olardi, onasining familiyasini
    olgan uka esa olmasdi. Bog'lanish o'tishli: ota Ali va Vali bilan, ona
    Vali va Soli bilan bog'langan bo'lsa — uchalasi bitta oila.
    Vasiylar telefon bo'yicha bir xil yozuvga tushadi (`upsert_guardian`),
    ya'ni importda ham oila o'zi yig'iladi.
    """
    from apps.children.models import ChildGuardian

    seen_children = {child.id}
    seen_guardians: set[Any] = set()
    frontier = {child.id}
    while frontier:
        guardians = set(
            ChildGuardian.objects.filter(child_id__in=frontier)
            .exclude(guardian_id__in=seen_guardians)
            .values_list("guardian_id", flat=True)
        )
        if not guardians:
            break
        seen_guardians |= guardians
        children = set(
            ChildGuardian.objects.filter(guardian_id__in=guardians).values_list(
                "child_id", flat=True
            )
        )
        frontier = children - seen_children
        seen_children |= children
    return list(Child.objects.filter(id__in=seen_children).order_by("enrolled_on", "created_at"))


# --- "Bir oylik ariza" (Bosqich 12.1) ---


def pause_for(child: Child, year: int, month: int) -> Any:
    """Shu oyni qamraydigan pauza yoki `None`."""
    from apps.children.models import ChildPause

    first = date(year, month, 1)
    return (
        ChildPause.objects.filter(child=child, month_from__lte=first, month_to__gte=first)
        .order_by("-month_from")
        .first()
    )


@transaction.atomic
def pause_child(
    *,
    child: Child,
    year: int,
    month: int,
    reason: str,
    year_to: int | None = None,
    month_to: int | None = None,
    created_by: Any = None,
) -> Any:
    """
    Bolani bir (yoki bir necha) oyga to'xtatadi — joyi saqlanadi.

    Holat O'ZGARMAYDI: bola faol, guruhda. O'sha oy(lar)ning hisob-fakturasi
    0 so'm bo'lib, sababi bilan yoziladi (`charges.plan_month`).
    """
    from apps.children.models import ChildPause

    cleaned = (reason or "").strip()
    if not cleaned:
        raise BusinessRuleViolation(gettext("Pauza sababini yozing."))
    start = date(year, month, 1)
    end = date(year_to or year, month_to or month, 1)
    if end < start:
        raise BusinessRuleViolation(gettext("Pauza oxiri boshidan oldin boʻlishi mumkin emas."))
    if ChildPause.objects.filter(child=child, month_from__lte=end, month_to__gte=start).exists():
        raise BusinessRuleViolation(gettext("Bu oylar uchun pauza allaqachon bor."))
    pause = ChildPause.objects.create(
        organization=child.organization,
        branch=child.branch,
        child=child,
        month_from=start,
        month_to=end,
        reason=cleaned[:255],
        created_by=created_by,
    )
    _reissue_paused_months(child=child, pause=pause, created_by=created_by)
    return pause


def _reissue_paused_months(*, child: Child, pause: Any, created_by: Any = None) -> None:
    """
    Pauza oyiga faktura allaqachon chiqqan bo'lsa — bekor qilib, 0 so'mlik qayta yozadi.

    Ariza ko'pincha oyning 1-kunidagi avtomatik fakturadan KEYIN keladi.
    Hujjat tahrirlanmaydi: mavjud yo'l — `cancel_invoice` (qarshi yozuv) va
    yangi `issue_invoice`, u esa pauzani ko'rib 0 yozadi. To'lov tushgan
    oyda tizim to'xtaydi: bu pulni qaytarish yoki keyingi oyga o'tkazish —
    odamning qarori, jimgina avans qilib qo'yish emas.
    """
    from apps.finance import services as finance
    from apps.finance.models import Invoice, InvoiceStatus

    month = pause.month_from
    while month <= pause.month_to:
        invoice = (
            Invoice.objects.filter(child=child, period_year=month.year, period_month=month.month)
            .exclude(status=InvoiceStatus.CANCELLED)
            .first()
        )
        if invoice is not None and invoice.amount_due > 0:
            if invoice.amount_paid > 0:
                raise BusinessRuleViolation(
                    gettext(
                        "{month} uchun toʻlov tushgan — avval toʻlovni qaytaring yoki "
                        "pauzani keyingi oydan boshlang."
                    ).format(month=f"{month.month:02d}/{month.year}")
                )
            finance.cancel_invoice(
                invoice=invoice,
                reason=gettext("pauza: {reason}").format(reason=pause.reason),
                created_by=created_by,
            )
            finance.issue_invoice(
                child=child,
                period_year=month.year,
                period_month=month.month,
                created_by=created_by,
            )
        month = date(month.year + (month.month // 12), month.month % 12 + 1, 1)


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
    # Holat sanasi — bola bog'chada BO'LMAGAN birinchi kun. 1-sanadan
    # ketgan bola o'sha oyning birorta kunida ham bo'lmagan, shuning
    # uchun qat'iy `>`: ilgari `>=` edi va "1-oktabrdan chiqib ketgan"
    # bolaga oktabr uchun to'liq oylik yozilardi (brief §6, 5-qadam).
    return child.status_changed_on > date(period_year, period_month, 1)


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
