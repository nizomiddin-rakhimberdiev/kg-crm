"""
Oylik hisoblash mantiqi (docs/03 §14.3–14.4).

Holat mashinasi bir tomonlama: `draft → finalized → paid`.
Yakunlangan hisoblash o'zgarmaydi — xato keyingi oyda tuzatuvchi
bonus/ushlab qolish bilan hal qilinadi.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext

from apps.core.exceptions import BusinessRuleViolation
from apps.hr.models import Employee, EmploymentStatus
from apps.payroll.models import EmployeeAdvance, PayrollItem, PayrollRun, PayrollStatus

__all__ = [
    "create_run",
    "update_item",
    "finalize_run",
    "mark_run_paid",
    "recompute_run_totals",
    "payslip",
]

CENT = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _assert_editable(run: PayrollRun) -> None:
    if not run.is_editable:
        raise BusinessRuleViolation(
            gettext(
                "Hisoblash '{status}' holatida — o'zgartirib bo'lmaydi. "
                "Tuzatishni keyingi oyda bonus yoki ushlab qolish bilan kiriting."
            ).format(status=run.get_status_display())
        )


@transaction.atomic
def create_run(
    *, organization: Any, branch: Any, period_year: int, period_month: int
) -> PayrollRun:
    """
    Davr uchun qoralama hisoblash yaratadi va satrlarni faol xodimlardan
    to'ldiradi.

    Idempotentlik bazada: `uq_payroll_run_branch_period`. Ikkinchi
    hisoblash xodimga ikki marta oylik to'lash xavfini yaratardi.
    """
    if not 1 <= period_month <= 12:
        raise BusinessRuleViolation(gettext("Oy 1–12 oralig'ida bo'lishi kerak."))

    try:
        run = PayrollRun.objects.create(
            organization=organization,
            branch=branch,
            period_year=period_year,
            period_month=period_month,
        )
    except IntegrityError as exc:
        raise BusinessRuleViolation(
            gettext(
                "{period_year}-{period_month:02d} uchun bu filialda hisoblash allaqachon mavjud."
            ).format(period_year=period_year, period_month=period_month)
        ) from exc

    employees = Employee.objects.filter(
        branch=branch, is_active=True, employment_status=EmploymentStatus.ACTIVE
    )

    PayrollItem.objects.bulk_create(
        [
            PayrollItem(
                organization=organization,
                branch=branch,
                payroll_run=run,
                employee=employee,
                # Maosh SNAPSHOT sifatida ko'chiriladi: keyin oshsa ham
                # bu hisoblash o'zgarmasligi kerak.
                base_amount=employee.base_salary,
                gross=employee.base_salary,
                net=employee.base_salary,
            )
            for employee in employees
        ]
    )
    sync_advances(run)
    recompute_run_totals(run)
    return run


def _advance_totals(run: PayrollRun) -> dict[Any, Decimal]:
    """Davr ichida berilgan avanslar — xodim bo'yicha yig'indi."""
    rows = (
        EmployeeAdvance.objects.filter(
            branch=run.branch,
            paid_on__year=run.period_year,
            paid_on__month=run.period_month,
        )
        .values("employee_id")
        .annotate(total=Sum("amount"))
    )
    return {row["employee_id"]: row["total"] or Decimal("0") for row in rows}


@transaction.atomic
def sync_advances(run: PayrollRun) -> PayrollRun:
    """
    Davr avanslarini satrlarga ko'chiradi va sof maoshni qayta hisoblaydi.

    Bog'lanish DAVR bo'yicha (avans sanasi), maxsus ustun orqali emas —
    shunda qayta hisoblash idempotent: bir necha marta chaqirilsa ham
    natija bir xil bo'ladi.
    """
    _assert_editable(run)
    totals = _advance_totals(run)
    for item in run.items.select_related("employee"):
        advance = _money(totals.get(item.employee_id, Decimal("0")))
        if advance == item.advance:
            continue
        item.advance = advance
        item.gross = _money(item.base_amount + item.bonus)
        net = item.gross - item.deduction - item.advance
        if net < 0:
            raise BusinessRuleViolation(
                gettext(
                    "{employee}: avans ({advance}) yalpi maoshdan ({gross}) oshib ketdi."
                ).format(employee=item.employee.full_name, advance=advance, gross=item.gross)
            )
        item.net = _money(net)
        item.save(update_fields=["advance", "gross", "net", "updated_at"])
    return run


@transaction.atomic
def recalculate_run(run: PayrollRun) -> PayrollRun:
    """
    Qoralamani QAYTA hisoblaydi: yangi xodimlar qo'shiladi, ishdan
    bo'shaganlar (satrida qo'lda kiritilgan qiymat bo'lmasa) olib
    tashlanadi, avanslar yangilanadi.

    Nega kerak: hisoblash oy oxirida yaratiladi, lekin xodim oyning
    o'rtasida ishga kirishi yoki avans keyinroq berilishi mumkin. Usiz
    yagona yo'l hisoblashni o'chirib, qaytadan yaratish bo'lardi.
    Yakunlangan hisoblash O'ZGARMAYDI — `_assert_editable` shuni qo'riqlaydi.
    """
    _assert_editable(run)

    active = list(
        Employee.objects.filter(
            branch=run.branch, is_active=True, employment_status=EmploymentStatus.ACTIVE
        )
    )
    existing = {item.employee_id: item for item in run.items.all()}

    PayrollItem.objects.bulk_create(
        [
            PayrollItem(
                organization=run.organization,
                branch=run.branch,
                payroll_run=run,
                employee=employee,
                base_amount=employee.base_salary,
                gross=employee.base_salary,
                net=employee.base_salary,
            )
            for employee in active
            if employee.id not in existing
        ]
    )

    # Endi ishlamayotgan xodim satri — faqat unga hech narsa yozilmagan
    # bo'lsa olib tashlanadi. Bonus yoki izoh kiritilgan bo'lsa, u ataylab
    # qo'yilgan degani va uni jimgina yo'qotish mumkin emas.
    active_ids = {employee.id for employee in active}
    for employee_id, item in existing.items():
        untouched = item.bonus == 0 and item.deduction == 0 and not item.note
        if employee_id not in active_ids and untouched:
            item.delete()

    run.refresh_from_db()
    sync_advances(run)
    recompute_run_totals(run)
    return run


@transaction.atomic
def record_advance(
    *,
    employee: Any,
    amount: Decimal,
    paid_on: Any,
    note: str = "",
    created_by: Any = None,
) -> EmployeeAdvance:
    """Avans yozadi va o'sha davrning QORALAMA hisoblashini yangilaydi."""
    if amount <= 0:
        raise BusinessRuleViolation(gettext("Avans summasi musbat bo'lishi kerak."))

    advance = EmployeeAdvance.objects.create(
        organization=employee.organization,
        branch=employee.branch,
        employee=employee,
        amount=_money(amount),
        paid_on=paid_on,
        note=note[:255],
        created_by=created_by,
    )
    _sync_draft_for(advance)
    return advance


@transaction.atomic
def delete_advance(*, advance: EmployeeAdvance) -> None:
    """Avansni o'chiradi (yakunlangan davrga tegmaydi)."""
    run = _draft_run_for(advance)
    advance.delete()
    if run is not None:
        sync_advances(run)
        recompute_run_totals(run)


def _draft_run_for(advance: EmployeeAdvance) -> PayrollRun | None:
    return PayrollRun.objects.filter(
        branch=advance.branch,
        period_year=advance.paid_on.year,
        period_month=advance.paid_on.month,
        status=PayrollStatus.DRAFT,
    ).first()


def _sync_draft_for(advance: EmployeeAdvance) -> None:
    run = _draft_run_for(advance)
    if run is not None:
        sync_advances(run)
        recompute_run_totals(run)


@transaction.atomic
def update_item(
    *,
    item: PayrollItem,
    bonus: Decimal | None = None,
    deduction: Decimal | None = None,
    note: str | None = None,
) -> PayrollItem:
    """Qoralama satrini tahrirlaydi va yalpi/sof qiymatlarni qayta hisoblaydi."""
    _assert_editable(item.payroll_run)

    if bonus is not None:
        if bonus < 0:
            raise BusinessRuleViolation(gettext("Bonus manfiy bo'lolmaydi."))
        item.bonus = _money(bonus)
    if deduction is not None:
        if deduction < 0:
            raise BusinessRuleViolation(gettext("Ushlab qolish manfiy bo'lolmaydi."))
        item.deduction = _money(deduction)
    if note is not None:
        item.note = note[:255]

    item.gross = _money(item.base_amount + item.bonus)
    # Avans — xodim oy davomida ALLAQACHON olgan pul, shuning uchun u ham
    # sof maoshdan chiqadi (ushlab qolishdan alohida ustunda turadi).
    net = item.gross - item.deduction - item.advance
    if net < 0:
        raise BusinessRuleViolation(
            gettext(
                "Ushlab qolish va avans yalpi maoshdan oshib ketdi "
                "({deduction} > {gross}). Sof maosh manfiy bo'lolmaydi."
            ).format(deduction=item.deduction + item.advance, gross=item.gross)
        )
    item.net = _money(net)
    item.save(update_fields=["bonus", "deduction", "note", "gross", "net", "updated_at"])

    recompute_run_totals(item.payroll_run)
    return item


def recompute_run_totals(run: PayrollRun) -> PayrollRun:
    """
    Yig'indilarni satrlardan QAYTA HISOBLAYDI.

    Inkremental yangilash bitta o'tkazib yuborilgan hodisada jimgina
    siljiydi — moliyaviy keshlar bilan bir xil qoida (D3).
    """
    totals = PayrollItem.objects.filter(payroll_run=run).aggregate(
        gross=Sum("gross"), deductions=Sum("deduction"), net=Sum("net")
    )
    PayrollRun.objects.filter(pk=run.pk).update(
        total_gross=_money(totals["gross"] or Decimal("0")),
        total_deductions=_money(totals["deductions"] or Decimal("0")),
        total_net=_money(totals["net"] or Decimal("0")),
    )
    run.refresh_from_db()
    return run


@transaction.atomic
def finalize_run(*, run: PayrollRun, finalized_by: Any = None) -> PayrollRun:
    """
    Hisoblashni yakunlaydi — shundan keyin u o'zgarmas.

    Yakunlashdan oldin yig'indilar qayta hisoblanadi: yakunlangan
    hisoblash yig'indisi satrlar bilan mos kelmasa, uni keyin tuzatib
    bo'lmaydi.
    """
    if run.status != PayrollStatus.DRAFT:
        raise BusinessRuleViolation(gettext("Faqat qoralama hisoblashni yakunlash mumkin."))

    if not PayrollItem.objects.filter(payroll_run=run).exists():
        raise BusinessRuleViolation(
            gettext("Bo'sh hisoblashni yakunlab bo'lmaydi — xodimlar yo'q.")
        )

    recompute_run_totals(run)
    run.status = PayrollStatus.FINALIZED
    run.finalized_at = timezone.now()
    run.finalized_by = finalized_by
    run.save(update_fields=["status", "finalized_at", "finalized_by", "updated_at"])
    return run


@transaction.atomic
def mark_run_paid(*, run: PayrollRun) -> PayrollRun:
    """Yakunlangan hisoblashni to'langan deb belgilaydi."""
    if run.status != PayrollStatus.FINALIZED:
        raise BusinessRuleViolation(
            gettext("Faqat yakunlangan hisoblashni to'langan deb belgilash mumkin.")
        )
    run.status = PayrollStatus.PAID
    run.paid_at = timezone.now()
    run.save(update_fields=["status", "paid_at", "updated_at"])
    return run


@transaction.atomic
def reopen_run(*, run: PayrollRun, reason: str) -> PayrollRun:
    """
    Yakunlangan yoki to'langan hisoblashni QORALAMAGA qaytaradi.

    Nega qo'shildi: birinchi mijozda hisoblash yakunlanib qolgan va
    undagi xatoni — kiritilmagan bonus, noto'g'ri ushlab qolish —
    tuzatishning hech qanday yo'li qolmagan edi. "Keyingi oyda tuzatuv
    kiriting" degan maslahat buxgalteriyada to'g'ri, lekin oyning
    o'zida xato raqam bilan oylik bergan bog'cha uchun javob emas.

    Bu ledger qoidasini (D3) buzmaydi: `payroll_run` — hisoblangan
    hujjat, o'zgarmas pul yozuvi emas. Pul yozuvi bo'lgan avans
    (`employee_advance`) va chiqim o'z joyida qoladi; qayta ochish
    faqat hisoblashning holatini va sanalarini tiklaydi.

    Sabab MAJBURIY va audit jurnaliga tushadi: yakunlangan hujjatni
    ochish izsiz bo'lmasligi kerak.
    """
    if run.status == PayrollStatus.DRAFT:
        raise BusinessRuleViolation(gettext("Hisoblash allaqachon qoralama."))

    cleaned = (reason or "").strip()
    if not cleaned:
        raise BusinessRuleViolation(gettext("Qayta ochish sababini ko'rsating."))

    run.status = PayrollStatus.DRAFT
    run.finalized_at = None
    run.finalized_by = None
    run.paid_at = None
    run.save(update_fields=["status", "finalized_at", "finalized_by", "paid_at", "updated_at"])

    # Qayta ochilgan davrda avans keyinroq yozilgan bo'lishi mumkin —
    # endi u satrlarga tushadi va sof maosh to'g'rilanadi.
    sync_advances(run)
    recompute_run_totals(run)
    return run


def payslip(*, item: PayrollItem) -> dict[str, Any]:
    """
    Oylik varaqasi ma'lumoti (PDF Sprint 9 da, storage bilan birga).

    Barcha qiymatlar `payroll_item` dan olinadi, xodimning joriy
    maoshidan emas — varaqa o'sha oyning holatini ko'rsatishi kerak.
    """
    run = item.payroll_run
    return {
        "employee": {
            "id": str(item.employee_id),
            "full_name": item.employee.full_name,
            "position": item.employee.position.title if item.employee.position else None,
        },
        "period": f"{run.period_year}-{run.period_month:02d}",
        "status": run.status,
        "base_amount": str(item.base_amount),
        "bonus": str(item.bonus),
        "deduction": str(item.deduction),
        "advance": str(item.advance),
        "gross": str(item.gross),
        "net": str(item.net),
        "note": item.note,
        "finalized_at": run.finalized_at.isoformat() if run.finalized_at else None,
    }
