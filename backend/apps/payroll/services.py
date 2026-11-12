"""
Oylik hisoblash mantiqi (docs/03 §14.3–14.4).

Holat mashinasi bir tomonlama: `draft → finalized → paid`.
Yakunlangan hisoblash o'zgarmaydi — xato keyingi oyda tuzatuvchi
bonus/ushlab qolish bilan hal qilinadi.
"""

from __future__ import annotations

import calendar
from datetime import date, datetime, time
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext

from apps.cash import services as cash
from apps.cash.models import CashAccount, MovementDirection, MovementSource
from apps.core.exceptions import BusinessRuleViolation
from apps.hr.models import Employee, EmploymentStatus
from apps.payroll.models import (
    EmployeeAdvance,
    PayoutPart,
    PayrollItem,
    PayrollPayout,
    PayrollRun,
    PayrollStatus,
)

__all__ = [
    "create_run",
    "eligible_employees",
    "missing_employees",
    "period_share",
    "update_item",
    "finalize_run",
    "mark_run_paid",
    "recompute_run_totals",
    "payslip",
]

CENT = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _rates() -> tuple[Decimal, Decimal, Decimal]:
    """
    Stavkalar — Sozlamalardan (ADR-18, Q10).

    Kodda emas: ular qaror bilan, ba'zan yil o'rtasida o'zgaradi, va
    stavkani servisga yozib qo'yish qonunga bo'ysunish uchun reliz
    talab qilardi.

    Uchtasi ikki xil tabiatga ega: birinchi ikkitasi xodimdan
    USHLANADI (uning qo'liga kam tegadi), uchinchisi esa bog'cha
    USTIGA to'laydi (xodimga ta'sir qilmaydi, xarajatni oshiradi).
    """
    from apps.settings_app.services import get_setting

    income = Decimal(str(get_setting(key="payroll.income_tax_rate")))
    pension = Decimal(str(get_setting(key="payroll.pension_rate")))
    social = Decimal(str(get_setting(key="payroll.social_tax_rate")))
    return income, pension, social


def recompute_item(
    item: PayrollItem, *, rates: tuple[Decimal, Decimal, Decimal] | None = None
) -> PayrollItem:
    """
    Satrning BARCHA hosila qiymatlarini qayta hisoblaydi (ADR-18).

    Hisoblash bitta joyda: ilgari `net` to'rt joyda alohida
    hisoblanardi va rasmiy/naqd bo'linishi qo'shilganda ularning biri
    ertami-kechmi qolib ketardi.

        rasmiy:  official_base − soliqlar        → bankka
        naqd:    (baza − rasmiy) + bonus
                 − ushlab qolish − avans         → kassadan

    Ikki sof summa alohida saqlanadi, chunki ular BOSHQA qoplardan
    chiqadi (docs/03 §13a).
    """
    income_rate, pension_rate, social_rate = rates if rates is not None else _rates()

    official = _money(min(item.official_base, item.base_amount))
    item.official_base = official
    item.tax_income = _money(official * income_rate / Decimal("100"))
    item.tax_pension = _money(official * pension_rate / Decimal("100"))
    item.official_net = _money(official - item.tax_income - item.tax_pension)
    # Ish beruvchi solig'i sof maoshga TEGMAYDI — u bog'chaning ustiga
    # qo'shiladigan xarajat (Q10).
    item.tax_social = _money(official * social_rate / Decimal("100"))

    cash_gross = (item.base_amount - official) + item.bonus
    cash_net = cash_gross - item.deduction - item.advance - item.tuition
    if cash_net < 0:
        # Ataylab xato: naqd qism ushlab qolish va avansni ko'tara
        # olmasa, payslip ma'nosiz raqam beradi. Buxgalter qaror
        # qabul qilishi kerak — tizim taxmin qilmaydi.
        raise BusinessRuleViolation(
            gettext(
                "{employee}: ushlab qolish va avans ({taken}) naqd qismdan ({cash}) oshib "
                "ketdi. Rasmiy maoshni yoki avansni toʻgʻrilang."
            ).format(
                employee=item.employee.full_name,
                taken=_money(item.deduction + item.advance + item.tuition),
                cash=_money(cash_gross),
            )
        )

    item.cash_net = _money(cash_net)
    item.gross = _money(item.base_amount + item.bonus)
    item.net = _money(item.official_net + item.cash_net)
    return item


ITEM_FIELDS = [
    "official_base",
    "tax_income",
    "tax_pension",
    "tax_social",
    "official_net",
    "cash_net",
    "gross",
    "net",
    "updated_at",
]


# --- Xodim oylikka qanday tushadi (PLAN 1.10) ---


def eligible_employees(*, branch: Any, period_year: int, period_month: int) -> Any:
    """
    Davr uchun oylik oladigan xodimlar.

    Ikki shart: faol va shu davr TUGAGUNCHA ishga kirgan. Ikkinchisi
    ilgari yo'q edi — 10-mayda kelgan xodim aprel hisobiga ham tushib
    ketardi, agar o'sha hisob keyinroq yaratilgan bo'lsa.
    """
    last_day = calendar.monthrange(period_year, period_month)[1]
    return Employee.objects.filter(
        branch=branch,
        is_active=True,
        employment_status=EmploymentStatus.ACTIVE,
        hire_date__lte=date(period_year, period_month, last_day),
    )


def missing_employees(*, run: PayrollRun) -> list[Employee]:
    """
    Hisobda BO'LISHI KERAK, lekin yo'q xodimlar.

    `create_run()` xodimlarni o'sha ondagi ro'yxatdan suratga oladi.
    Keyin qo'shilgan xodim qoralamaga `recalculate_run()` bilan tushadi,
    lekin hisob YAKUNLANGAN bo'lsa hech narsa qilib bo'lmaydi — va, eng
    yomoni, tushib qolgani hech qayerda ko'rinmaydi. Auditda aynan
    shunday bo'lgan: xodim bor, oyligi yo'q, xato yo'q.

    Bu funksiya jimlikni buzadi. Ekran uni ogohlantirish sifatida
    ko'rsatadi: "2 xodim bu hisobda yo'q".
    """
    present = set(run.items.values_list("employee_id", flat=True))
    return [
        employee
        for employee in eligible_employees(
            branch=run.branch, period_year=run.period_year, period_month=run.period_month
        )
        if employee.id not in present
    ]


def scheduled_days(*, employee: Employee, period_year: int, period_month: int) -> int:
    """Xodim shu oyda O'Z grafigi bo'yicha necha kun ishlashi kerak."""
    from apps.attendance.services_absence import working_days_in_month

    return working_days_in_month(
        organization_id=employee.organization_id,
        year=period_year,
        month=period_month,
        branch=employee.branch,
        weekdays=set(employee.weekdays),
    )


def period_share(*, employee: Employee, period_year: int, period_month: int) -> tuple[int, int]:
    """
    Xodimning shu oydagi ish kunlari va oyning jami ish kunlari.

    Ishga kirgan oyi to'liq hisoblangani — bog'cha uchun ortiqcha
    xarajat, xodim uchun esa keyingi oy "nega kam?" degan savol.

    Maxraj — XODIMNING o'z kunlari (PLAN 9.1), filialniki emas: haftada
    uch kun keladigan tarbiyachi oy o'rtasida ishga kirsa, 13/22 emas,
    8/14 olishi kerak. Grafigi bo'sh xodim uchun ikkalasi bir xil,
    ya'ni eski xatti-harakat o'zgarmaydi.
    """
    from apps.attendance.services_absence import billable_days

    weekdays = set(employee.weekdays)
    total = scheduled_days(employee=employee, period_year=period_year, period_month=period_month)
    last_day = calendar.monthrange(period_year, period_month)[1]
    month_start = date(period_year, period_month, 1)
    month_end = date(period_year, period_month, last_day)

    start = max(month_start, employee.hire_date) if employee.hire_date else month_start
    if start <= month_start:
        return total, total

    worked = billable_days(
        organization_id=employee.organization_id,
        date_from=start,
        date_to=month_end,
        branch=employee.branch,
        weekdays=weekdays,
    )
    return worked, total


def present_days(*, employee: Employee, period_year: int, period_month: int) -> int | None:
    """
    Tabel bo'yicha kelgan kunlar. Tabel umuman to'ldirilmagan bo'lsa — `None`.

    Farq muhim: nol kun "kelmadi" degani, `None` esa "hech kim
    belgilamagan". Soatbay xodim uchun ikkalasiga bir xil javob
    bermaymiz (pastga qarang).
    """
    from apps.attendance.models_staff import StaffAttendance, StaffAttendanceStatus

    last_day = calendar.monthrange(period_year, period_month)[1]
    rows = StaffAttendance.objects.filter(
        employee=employee,
        attendance_date__gte=date(period_year, period_month, 1),
        attendance_date__lte=date(period_year, period_month, last_day),
    )
    total = rows.count()
    if total == 0:
        return None
    return rows.filter(status=StaffAttendanceStatus.PRESENT).count()


def hourly_amount(*, employee: Employee, period_year: int, period_month: int) -> Decimal:
    """
    Soatbay xodimning shu oydagi summasi: kunlar × kunlik soat × soat narxi.

    Kunlar tabeldan olinadi. Tabel yuritilmagan bo'lsa — grafik
    bo'yicha: nolga tushirish "texnik jihatdan to'g'ri" bo'lardi,
    lekin bu sabab ko'rsatilmagan nol bo'lib, tabelni hech kim
    to'ldirmaydigan bog'chada har bir soatbay xodim oyligini
    ololmay qolardi.
    """
    days = present_days(employee=employee, period_year=period_year, period_month=period_month)
    if days is None:
        days = scheduled_days(employee=employee, period_year=period_year, period_month=period_month)
    return _money(Decimal(days) * employee.hours_per_day * employee.hourly_rate)


def base_for_period(*, employee: Employee, period_year: int, period_month: int) -> Decimal:
    """Xodimning shu oydagi bazaviy summasi — rejimiga qarab."""
    from apps.hr.models import WorkMode

    if employee.work_mode == WorkMode.HOURLY:
        return hourly_amount(employee=employee, period_year=period_year, period_month=period_month)
    return _prorated_salary(
        employee=employee,
        amount=employee.base_salary,
        period_year=period_year,
        period_month=period_month,
    )


def _prorated_salary(
    *, employee: Employee, amount: Decimal, period_year: int, period_month: int
) -> Decimal:
    """Ishga kirgan oyi uchun proporsional maosh."""
    worked, total = period_share(
        employee=employee, period_year=period_year, period_month=period_month
    )
    if total <= 0 or worked >= total:
        return amount
    return _money(amount * worked / total)


def _assert_editable(run: PayrollRun) -> None:
    if not run.is_editable:
        raise BusinessRuleViolation(
            gettext(
                "Hisoblash '{status}' holatida — oʻzgartirib boʻlmaydi. "
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
        raise BusinessRuleViolation(gettext("Oy 1–12 oraligʻida boʻlishi kerak."))

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

    employees = eligible_employees(
        branch=branch, period_year=period_year, period_month=period_month
    )

    PayrollItem.objects.bulk_create(
        [
            PayrollItem(
                organization=organization,
                branch=branch,
                payroll_run=run,
                employee=employee,
                # Maosh SNAPSHOT sifatida ko'chiriladi: keyin oshsa ham
                # bu hisoblash o'zgarmasligi kerak. Ishga kirgan oyi
                # esa proporsional (PLAN 1.10).
                base_amount=base_for_period(
                    employee=employee, period_year=period_year, period_month=period_month
                ),
                official_base=_prorated_salary(
                    employee=employee,
                    amount=employee.official_salary,
                    period_year=period_year,
                    period_month=period_month,
                ),
                gross=employee.base_salary,
                net=employee.base_salary,
            )
            for employee in employees
        ]
    )
    _recompute_all(run)
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
    from apps.finance.selectors import payroll_tuition_totals

    _assert_editable(run)
    totals = _advance_totals(run)
    items = list(run.items.select_related("employee"))
    # Farzandining bog'cha to'lovi ham shu yo'l bilan keladi (Bosqich
    # 12.4): davr bo'yicha, idempotent.
    tuition = payroll_tuition_totals(
        employee_ids=[item.employee_id for item in items],
        period_year=run.period_year,
        period_month=run.period_month,
    )
    rates = _rates()
    for item in items:
        advance = _money(totals.get(item.employee_id, Decimal("0")))
        withheld = _money(tuition.get(item.employee_id, Decimal("0")))
        if advance == item.advance and withheld == item.tuition:
            continue
        item.advance = advance
        item.tuition = withheld
        recompute_item(item, rates=rates)
        item.save(update_fields=["advance", "tuition", *ITEM_FIELDS])
    return run


def _recompute_all(run: PayrollRun) -> None:
    """Barcha satrlarni qayta hisoblaydi — stavka yoki maosh o'zgarganda."""
    rates = _rates()
    for item in run.items.select_related("employee"):
        recompute_item(item, rates=rates)
        item.save(update_fields=ITEM_FIELDS)


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
        eligible_employees(
            branch=run.branch, period_year=run.period_year, period_month=run.period_month
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
                base_amount=_prorated_salary(
                    employee=employee,
                    amount=employee.base_salary,
                    period_year=run.period_year,
                    period_month=run.period_month,
                ),
                official_base=_prorated_salary(
                    employee=employee,
                    amount=employee.official_salary,
                    period_year=run.period_year,
                    period_month=run.period_month,
                ),
                gross=employee.base_salary,
                net=employee.base_salary,
            )
            for employee in active
            if employee.id not in existing
        ]
    )

    # Rasmiy/naqd BO'LINISHI ham yangilanadi (ADR-18).
    #
    # `base_amount` ataylab suratda qoladi — keyin oshgan maosh o'tgan
    # hisoblashni o'zgartirmasligi kerak. Lekin rasmiy qism summa emas,
    # TASNIF: buxgalter xodimni oy o'rtasida rasmiylashtirsa, "qayta
    # hisoblash" aynan shu o'zgarishni tortib olish uchun bosiladi.
    # Usiz tugma bosilardi, raqam esa o'zgarmasdi.
    by_employee = {employee.id: employee for employee in active}
    for employee_id, item in existing.items():
        employee = by_employee.get(employee_id)
        if employee is not None and item.official_base != employee.official_salary:
            item.official_base = employee.official_salary
            item.save(update_fields=["official_base", "updated_at"])

    # Endi ishlamayotgan xodim satri — faqat unga hech narsa yozilmagan
    # bo'lsa olib tashlanadi. Bonus yoki izoh kiritilgan bo'lsa, u ataylab
    # qo'yilgan degani va uni jimgina yo'qotish mumkin emas.
    active_ids = {employee.id for employee in active}
    for employee_id, item in existing.items():
        untouched = item.bonus == 0 and item.deduction == 0 and not item.note
        if employee_id not in active_ids and untouched:
            item.delete()

    _recompute_all(run)
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
    cash_account: Any = None,
    allow_negative: bool = False,
    created_by: Any = None,
) -> EmployeeAdvance:
    """
    Avans yozadi va o'sha davrning QORALAMA hisoblashini yangilaydi.

    `cash_account` — pul QAYSI qopdan chiqqani (ADR-29). Berilmasa
    naqd kassa olinadi, lekin endi u yozuvda qoladi: ilgari tanlov
    ham, iz ham yo'q edi va "pul qayerdan ketdi?" degan savol
    javobsiz qolardi.
    """
    if amount <= 0:
        raise BusinessRuleViolation(gettext("Avans summasi musbat boʻlishi kerak."))
    # Kassadan hali chiqmagan pul — "hozir qancha pulim bor?" degan
    # savolga noto'g'ri javob. `pay_run` bilan bir xil matn.
    if paid_on > timezone.localdate():
        raise BusinessRuleViolation(gettext("Toʻlov sanasi kelajakda boʻlishi mumkin emas."))

    account = cash_account or cash.account_for_method(branch=employee.branch, method="cash")
    if account.organization_id != employee.organization_id:
        raise BusinessRuleViolation(gettext("Kassa hisobi boshqa tashkilotga tegishli."))

    advance = EmployeeAdvance.objects.create(
        organization=employee.organization,
        branch=employee.branch,
        employee=employee,
        amount=_money(amount),
        paid_on=paid_on,
        cash_account=account,
        note=note[:255],
        created_by=created_by,
    )

    # Avans — kassadan ALLAQACHON chiqqan pul (ADR-17). Uni oylik
    # hisoblanishini kutib turib yozish "hozir qancha pulim bor?"
    # degan savolga oyning yarmi davomida noto'g'ri javob berardi.
    cash.post_movement(
        account=account,
        direction=MovementDirection.OUT,
        amount=advance.amount,
        source_type=MovementSource.ADVANCE,
        source_id=advance.id,
        description=gettext("Avans: {employee}").format(employee=employee.full_name)[:255],
        occurred_at=timezone.make_aware(datetime.combine(advance.paid_on, time.min)),
        created_by=created_by,
        allow_negative=allow_negative,
    )

    _sync_draft_for(advance)
    return advance


@transaction.atomic
def delete_advance(*, advance: EmployeeAdvance, reason: str = "", created_by: Any = None) -> None:
    """
    Avansni o'chiradi (yakunlangan davrga tegmaydi).

    Yakunlangan hisoblash YARATILGANDA mavjud bo'lgan avans uning sof
    maoshiga allaqachon tushgan: uni olib tashlash hisoblashni
    o'zgartirmaydi, faqat summaning ortidagi sababni yo'qotadi.
    Yakunlashdan KEYIN berilgan avans hisoblashga tushmagan — uni
    o'chirish xavfsiz.
    """
    closed = PayrollRun.objects.filter(
        branch=advance.branch,
        period_year=advance.paid_on.year,
        period_month=advance.paid_on.month,
        finalized_at__gte=advance.created_at,
    ).exclude(status=PayrollStatus.DRAFT)
    if closed.exists():
        raise BusinessRuleViolation(
            gettext(
                "Bu avans yakunlangan hisoblashga kirgan — uni oʻchirib boʻlmaydi. "
                "Tuzatish keyingi oyning hisoblashida."
            )
        )
    run = _draft_run_for(advance)
    # Kassa yozuvi O'CHIRILMAYDI — qarshi yozuv qo'shiladi (D3).
    # Avansning o'zi o'chiriladi, chunki u hali hisoblashga tushmagan
    # qoralama yozuv; kassadan chiqqan pulning izi esa qoladi.
    cash.reverse_movements_for(
        source_type=MovementSource.ADVANCE,
        source_id=advance.id,
        description=(reason.strip() or gettext("avans bekor qilindi"))[:255],
        created_by=created_by,
    )
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
            raise BusinessRuleViolation(gettext("Bonus manfiy boʻlolmaydi."))
        item.bonus = _money(bonus)
    if deduction is not None:
        if deduction < 0:
            raise BusinessRuleViolation(gettext("Ushlab qolish manfiy boʻlolmaydi."))
        item.deduction = _money(deduction)
    if note is not None:
        item.note = note[:255]

    # Avans — xodim oy davomida ALLAQACHON olgan pul, shuning uchun u ham
    # naqd qismdan chiqadi (ushlab qolishdan alohida ustunda turadi).
    recompute_item(item)
    item.save(update_fields=["bonus", "deduction", "note", *ITEM_FIELDS])
    recompute_run_totals(item.payroll_run)
    return item


def recompute_run_totals(run: PayrollRun) -> PayrollRun:
    """
    Yig'indilarni satrlardan QAYTA HISOBLAYDI.

    Inkremental yangilash bitta o'tkazib yuborilgan hodisada jimgina
    siljiydi — moliyaviy keshlar bilan bir xil qoida (D3).
    """
    totals = PayrollItem.objects.filter(payroll_run=run).aggregate(
        gross=Sum("gross"),
        deductions=Sum("deduction"),
        net=Sum("net"),
        social=Sum("tax_social"),
    )
    PayrollRun.objects.filter(pk=run.pk).update(
        total_gross=_money(totals["gross"] or Decimal("0")),
        total_deductions=_money(totals["deductions"] or Decimal("0")),
        total_net=_money(totals["net"] or Decimal("0")),
        total_social_tax=_money(totals["social"] or Decimal("0")),
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
            gettext("Boʻsh hisoblashni yakunlab boʻlmaydi — xodimlar yoʻq.")
        )

    recompute_run_totals(run)
    run.status = PayrollStatus.FINALIZED
    run.finalized_at = timezone.now()
    run.finalized_by = finalized_by
    run.save(update_fields=["status", "finalized_at", "finalized_by", "updated_at"])
    return run


@transaction.atomic
def planned_payouts(run: PayrollRun) -> list[dict[str, Any]]:
    """
    Hisoblashdan kelib chiqadigan to'lovlar TAKLIFI (docs/03 §14.4a).

    Rasmiy sof maosh bank hisobiga, naqd qism kassaga. Bu faqat
    taklif — foydalanuvchi qopni o'zgartira oladi; yozuv esa
    `pay_run()` yaratgan qatorlar.
    """
    bank = cash.account_for_method(branch=run.branch, method="bank_transfer")
    till = cash.account_for_method(branch=run.branch, method="cash")

    rows: list[dict[str, Any]] = []
    for item in run.items.select_related("employee"):
        for part, amount, account in (
            (PayoutPart.OFFICIAL, item.official_net, bank),
            (PayoutPart.CASH, item.cash_net, till),
        ):
            if amount <= 0:
                continue
            rows.append(
                {
                    "payroll_item_id": item.id,
                    "employee": item.employee.full_name,
                    "part": part,
                    "amount": amount,
                    "cash_account_id": account.id,
                    "cash_account_name": account.name,
                }
            )
    return rows


@transaction.atomic
def pay_run(
    *,
    run: PayrollRun,
    payouts: list[dict[str, Any]] | None = None,
    paid_on: Any = None,
    allow_negative: bool = False,
    created_by: Any = None,
) -> PayrollRun:
    """
    Hisoblashni to'laydi: pulni kassadan chiqaradi va holatni yopadi.

    `payouts` berilmasa taklif qabul qilinadi (`planned_payouts`).
    Har bir qator o'z `cash_movement` ini yozadi — hisoblash bilan
    BITTA tranzaksiyada, chunki "to'langan" deb belgilangan, lekin
    kassadan chiqmagan oylik jimgina noto'g'ri qoldiq degani.

    **Soliqlar bu yerda chiqmaydi.** Ushlab qolingan summa bank
    hisobida qoladi va davlatga to'langanda oddiy chiqim bo'lib
    yoziladi (ADR-18) — aks holda pul ikki marta chiqib ketardi.
    """
    if run.status != PayrollStatus.FINALIZED:
        raise BusinessRuleViolation(
            gettext("Faqat yakunlangan hisoblashni toʻlangan deb belgilash mumkin.")
        )

    rows = payouts if payouts is not None else planned_payouts(run)
    if not rows:
        raise BusinessRuleViolation(gettext("Toʻlanadigan summa yoʻq."))

    when = paid_on or timezone.localdate()
    # Pul qaysi KUNI chiqqani — tugma bosilgan vaqt emas (audit,
    # 2026-10-30). Sana ikki tomondan chegaralangan: kelajak
    # boʻlmaydi, va hisoblash davri boshlanishidan oldin ham
    # boʻlmaydi — may oyligini aprelda toʻlab boʻlmaydi.
    if when > timezone.localdate():
        raise BusinessRuleViolation(gettext("Toʻlov sanasi kelajakda boʻlishi mumkin emas."))
    period_start = date(run.period_year, run.period_month, 1)
    if when < period_start:
        raise BusinessRuleViolation(
            gettext("Toʻlov sanasi {period} dan oldin boʻlishi mumkin emas.").format(
                period=period_start.strftime("%d.%m.%Y")
            )
        )
    items = {item.id: item for item in run.items.select_related("employee")}
    # Har bir satr-qism bo'yicha allaqachon to'langan summa: qisman
    # to'lovdan keyin qayta chaqirilsa, ikki marta to'lamaslik uchun.
    already: dict[tuple[Any, str], Decimal] = {}
    for payout in PayrollPayout.objects.filter(payroll_run=run):
        key = (payout.payroll_item_id, payout.part)
        already[key] = already.get(key, Decimal("0")) + payout.amount

    for row in rows:
        amount = _money(Decimal(row["amount"]))
        if amount <= 0:
            continue
        item_id = row.get("payroll_item_id")
        item = items.get(item_id) if item_id else None
        part = row["part"]

        if item is not None:
            allowed = item.official_net if part == PayoutPart.OFFICIAL else item.cash_net
            paid_before = already.get((item.id, part), Decimal("0"))
            if paid_before + amount > allowed:
                raise BusinessRuleViolation(
                    gettext(
                        "{employee}: toʻlov summasi hisoblangandan oshib ketdi "
                        "({total} > {allowed})."
                    ).format(
                        employee=item.employee.full_name,
                        total=_money(paid_before + amount),
                        allowed=_money(allowed),
                    )
                )
            already[(item.id, part)] = paid_before + amount

        account = CashAccount.objects.filter(
            pk=row["cash_account_id"], organization_id=run.organization_id, is_active=True
        ).first()
        if account is None:
            raise BusinessRuleViolation(gettext("Kassa hisobi topilmadi."))

        payout = PayrollPayout.objects.create(
            organization=run.organization,
            branch=run.branch,
            payroll_run=run,
            payroll_item=item,
            cash_account=account,
            part=part,
            amount=amount,
            paid_on=when,
            note=str(row.get("note", ""))[:255],
            created_by=created_by,
        )
        cash.post_movement(
            account=account,
            direction=MovementDirection.OUT,
            amount=amount,
            source_type=MovementSource.PAYROLL,
            source_id=payout.id,
            description=gettext("Oylik {period}: {employee}").format(
                period=f"{run.period_year}-{run.period_month:02d}",
                employee=item.employee.full_name if item else "—",
            )[:255],
            occurred_at=timezone.make_aware(datetime.combine(when, time.min)),
            created_by=created_by,
            allow_negative=allow_negative,
        )

    # Bo'lib to'lash (Bosqich 13.2d): iyul oyligi 28.08 da yarmi, 08.09 da
    # qolgani. Hisoblash faqat hammasi to'langanda "to'langan" bo'ladi —
    # ilgari birinchi qisman to'lovdayoq yopilib, qolganini to'lab bo'lmasdi.
    owed = sum((item.official_net + item.cash_net for item in items.values()), Decimal("0"))
    paid = PayrollPayout.objects.filter(payroll_run=run).aggregate(total=Sum("amount"))[
        "total"
    ] or Decimal("0")
    if paid >= owed:
        run.status = PayrollStatus.PAID
        # Belgi ham PUL KUNIDAN olinadi: `now()` boʻlsa, sentabr
        # oyligi oktabrda "toʻlangan" deb turardi va kassa usulidagi
        # hisobot uni notoʻgʻri oyga qoʻyardi (audit, 2026-10-30).
        run.paid_at = timezone.make_aware(datetime.combine(when, time.min))
        run.save(update_fields=["status", "paid_at", "updated_at"])
    return run


def mark_run_paid(*, run: PayrollRun) -> PayrollRun:
    """Eski nom — `pay_run()` ning taklifni qabul qiladigan ko'rinishi."""
    return pay_run(run=run)


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
        raise BusinessRuleViolation(gettext("Qayta ochish sababini koʻrsating."))

    # To'langan hisoblashni ochish — pulni KASSAGA QAYTARISH demak.
    #
    # To'lov qatorlari o'chiriladi (ular hujjat, hisoblashning o'zi
    # kabi), lekin kassa yozuvlari O'CHIRILMAYDI: asl chiqim ham,
    # qarshi kirim ham jurnalda qoladi. D3 aynan shu yerda bog'laydi —
    # pul izi hech qachon yo'qolmaydi, hujjat esa qayta ochiladi.
    for payout in PayrollPayout.objects.filter(payroll_run=run):
        cash.reverse_movements_for(
            source_type=MovementSource.PAYROLL,
            source_id=payout.id,
            description=gettext("oylik qayta ochildi"),
        )
        payout.delete()

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
        "tuition": str(item.tuition),
        "gross": str(item.gross),
        "net": str(item.net),
        "note": item.note,
        "finalized_at": run.finalized_at.isoformat() if run.finalized_at else None,
    }
