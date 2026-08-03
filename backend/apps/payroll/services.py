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

from apps.core.exceptions import BusinessRuleViolation
from apps.hr.models import Employee, EmploymentStatus
from apps.payroll.models import PayrollItem, PayrollRun, PayrollStatus

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
            f"Hisoblash '{run.get_status_display()}' holatida — o'zgartirib bo'lmaydi. "
            f"Tuzatishni keyingi oyda bonus yoki ushlab qolish bilan kiriting."
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
        raise BusinessRuleViolation("Oy 1–12 oralig'ida bo'lishi kerak.")

    try:
        run = PayrollRun.objects.create(
            organization=organization,
            branch=branch,
            period_year=period_year,
            period_month=period_month,
        )
    except IntegrityError as exc:
        raise BusinessRuleViolation(
            f"{period_year}-{period_month:02d} uchun bu filialda hisoblash allaqachon mavjud."
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
    recompute_run_totals(run)
    return run


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
            raise BusinessRuleViolation("Bonus manfiy bo'lolmaydi.")
        item.bonus = _money(bonus)
    if deduction is not None:
        if deduction < 0:
            raise BusinessRuleViolation("Ushlab qolish manfiy bo'lolmaydi.")
        item.deduction = _money(deduction)
    if note is not None:
        item.note = note[:255]

    item.gross = _money(item.base_amount + item.bonus)
    net = item.gross - item.deduction
    if net < 0:
        raise BusinessRuleViolation(
            f"Ushlab qolish yalpi maoshdan oshib ketdi ({item.deduction} > {item.gross}). "
            f"Sof maosh manfiy bo'lolmaydi."
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
        raise BusinessRuleViolation("Faqat qoralama hisoblashni yakunlash mumkin.")

    if not PayrollItem.objects.filter(payroll_run=run).exists():
        raise BusinessRuleViolation("Bo'sh hisoblashni yakunlab bo'lmaydi — xodimlar yo'q.")

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
        raise BusinessRuleViolation("Faqat yakunlangan hisoblashni to'langan deb belgilash mumkin.")
    run.status = PayrollStatus.PAID
    run.paid_at = timezone.now()
    run.save(update_fields=["status", "paid_at", "updated_at"])
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
        "gross": str(item.gross),
        "net": str(item.net),
        "note": item.note,
        "finalized_at": run.finalized_at.isoformat() if run.finalized_at else None,
    }
