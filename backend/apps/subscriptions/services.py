"""
Obuna biznes mantiqi (docs/03 §20.6, docs/01 §4.3–4.4).

Bu yerda tizimning **daromadi** hal bo'ladi, shuning uchun har bir qoida
alohida yozilgan va alohida sinalgan. Uchta narsa hech qachon
buzilmasligi kerak:

1. Hisob HAR DOIM yopilgan `usage_snapshot` dan chiqadi — jonli
   hisoblagichdan emas (P11).
2. Yozilgan hisob-faktura o'zgarmaydi. Xato bo'lsa — bekor qilinadi va
   yangisi yoziladi.
3. To'lamagan mijozning ma'lumoti O'CHIRILMAYDI va yashirilmaydi;
   faqat yozish to'xtaydi (docs/03 §20.6).
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext

from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context, platform_context
from apps.subscriptions import pricing
from apps.subscriptions.models import (
    GRACE_DAYS,
    TERM_DISCOUNTS,
    TERM_MONTHS,
    TRIAL_DAYS,
    MeasurementMethod,
    PaymentTerm,
    Subscription,
    SubscriptionInvoice,
    SubscriptionInvoiceStatus,
    SubscriptionPayment,
    SubscriptionPlan,
    SubscriptionStatus,
    UsageSnapshot,
)

logger = logging.getLogger(__name__)

__all__ = [
    "current_plan",
    "start_trial",
    "accept_trial",
    "change_payment_term",
    "record_daily_usage",
    "close_period",
    "issue_invoice",
    "record_subscription_payment",
    "expire_trials",
    "mark_past_due",
    "suspend_unpaid",
    "projected_usage",
    "add_months",
    "adjust_usage",
]


# --- Plan ---


def current_plan(code: str = "standard", *, on: date | None = None) -> SubscriptionPlan:
    """
    Berilgan sanada amal qiladigan plan versiyasi.

    Plan versiyalanadi (docs/03 §20.1), shuning uchun "joriy plan" har
    doim sanaga bog'liq savol.
    """
    when = on or timezone.localdate()
    plan = (
        SubscriptionPlan.objects.filter(code=code, valid_from__lte=when)
        .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=when))
        .order_by("-valid_from")
        .first()
    )
    if plan is None:
        raise BusinessRuleViolation(
            gettext("'{code}' uchun amaldagi plan topilmadi.").format(code=code)
        )
    return plan


# --- Hayotiy sikl ---


def _month_end(value: date) -> date:
    return (value.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)


def add_months(value: date, months: int) -> date:
    total = value.year * 12 + (value.month - 1) + months
    year, month = divmod(total, 12)
    day = min(
        value.day, [31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month]
    )
    return date(year, month + 1, day)


@transaction.atomic
def start_trial(
    *, organization: Any, plan: SubscriptionPlan | None = None, trial_days: int = TRIAL_DAYS
) -> Subscription:
    """
    Ro'yxatdan o'tgan tashkilotga sinov obunasi ochadi (vendor: 15 kun,
    mustaqil ro'yxatdan o'tish: 14 kun — PLAN 6.7).

    Karta so'ralmaydi va oldindan to'lov olinmaydi (docs/01 §4.4).
    """
    if (
        Subscription.objects.filter(organization=organization)
        .exclude(status=SubscriptionStatus.CANCELLED)
        .exists()
    ):
        raise BusinessRuleViolation(gettext("Bu tashkilotda allaqachon obuna bor."))

    now = timezone.now()
    today = timezone.localdate()
    resolved_plan = plan or current_plan()

    return Subscription.objects.create(
        organization=organization,
        plan=resolved_plan,
        status=SubscriptionStatus.TRIALING,
        payment_term=PaymentTerm.MONTHLY,
        discount_percent=Decimal("0"),
        trial_started_at=now,
        trial_ends_at=now + timedelta(days=trial_days),
        current_period_start=today,
        current_period_end=_month_end(today)
        if _month_end(today) > today
        else today + timedelta(days=1),
    )


@transaction.atomic
def accept_trial(
    *,
    subscription: Subscription,
    payment_term: str = PaymentTerm.MONTHLY,
    committed_children: int | None = None,
) -> SubscriptionInvoice:
    """
    Sinovni to'lovli rejimga o'tkazadi va BIRINCHI hisobni yozadi.

    **Birinchi to'langan davr sinov kunidan boshlanadi** (docs/01 §4.4):
    `period_start = trial_started_at`, qabul qilingan sana emas. Bu
    ro'yxatdan o'tishda taklifda aytilgan bo'lishi SHART — sxema
    siyosatni qo'llab-quvvatlaydi, lekin uni halol qiladigan narsa faqat
    ochiq aytilgani.
    """
    if subscription.status != SubscriptionStatus.TRIALING:
        raise BusinessRuleViolation(gettext("Faqat sinov davridagi obunani oʻtkazish mumkin."))
    if payment_term not in TERM_DISCOUNTS:
        raise BusinessRuleViolation(
            gettext("Nomaʼlum toʻlov muddati: {payment_term}").format(payment_term=payment_term)
        )

    months = TERM_MONTHS[payment_term]
    # Chegirma obunaga NUSXA qilinadi: keyin vendor "yillik" nimaga
    # arziyotganini o'zgartirsa, bu shartnomaga tegmasin.
    subscription.payment_term = payment_term
    subscription.discount_percent = TERM_DISCOUNTS[payment_term]

    started = timezone.localtime(subscription.trial_started_at).date()
    period_start = started
    period_end = add_months(period_start, months) - timedelta(days=1)

    peak = _current_child_count(subscription.organization_id)
    snapshot = _open_snapshot(subscription, period_start.year, period_start.month, peak)
    snapshot = close_period(snapshot=snapshot)

    subscription.committed_children = (
        committed_children if committed_children is not None else snapshot.billable_children
    )
    subscription.current_period_start = period_start
    subscription.current_period_end = period_end
    subscription.status = SubscriptionStatus.PENDING_PAYMENT
    subscription.save(
        update_fields=[
            "payment_term",
            "discount_percent",
            "committed_children",
            "current_period_start",
            "current_period_end",
            "status",
            "updated_at",
        ]
    )

    return issue_invoice(
        subscription=subscription,
        snapshot=snapshot,
        period_start=period_start,
        period_end=period_end,
        months=months,
    )


def change_payment_term(*, subscription: Subscription, payment_term: str) -> Subscription:
    """
    Muddatni o'zgartiradi — KEYINGI davrdan boshlab.

    Joriy davrni o'rtasida qayta narxlash allaqachon yozilgan hisobni
    o'zgartirishni talab qilardi, ya'ni yuridik hujjatni orqaga qaytib
    tahrirlashni.
    """
    if payment_term not in TERM_DISCOUNTS:
        raise BusinessRuleViolation(
            gettext("Nomaʼlum toʻlov muddati: {payment_term}").format(payment_term=payment_term)
        )
    if subscription.status in (SubscriptionStatus.CANCELLED, SubscriptionStatus.SUSPENDED):
        raise BusinessRuleViolation(gettext("Bu holatda muddatni oʻzgartirib boʻlmaydi."))

    subscription.payment_term = payment_term
    subscription.discount_percent = TERM_DISCOUNTS[payment_term]
    subscription.save(update_fields=["payment_term", "discount_percent", "updated_at"])
    return subscription


# --- Hisoblash (metering) ---


def _current_child_count(organization_id: Any) -> int:
    """
    Hozirgi faol bolalar soni.

    `reports` selektoridan foydalanadi — ta'rif bitta joyda tursin,
    aks holda dashboard va hisob-faktura bir-biriga zid raqam
    ko'rsatardi.
    """
    from apps.reports.selectors import active_children_count

    return active_children_count(organization_id=organization_id)


def _open_snapshot(subscription: Subscription, year: int, month: int, peak: int) -> UsageSnapshot:
    """Davr uchun o'lchov qatorini ochadi yoki eng yuqori nuqtani ko'taradi."""
    snapshot = UsageSnapshot.objects.filter(
        subscription=subscription,
        period_year=year,
        period_month=month,
        measurement_method=MeasurementMethod.DAILY_PEAK,
    ).first()

    included = subscription.plan.included_children
    if snapshot is None:
        return UsageSnapshot.objects.create(
            organization=subscription.organization,
            subscription=subscription,
            period_year=year,
            period_month=month,
            peak_children=peak,
            peak_observed_at=timezone.now(),
            billable_children=pricing.billable_children(peak=peak, included=included),
        )

    if snapshot.closed_at is not None:
        # Yopilgan davr muzlagan. Bu xato emas — kechikkan vazifa
        # yopilgandan keyin ishga tushishi normal holat.
        return snapshot

    if peak > snapshot.peak_children:
        snapshot.peak_children = peak
        snapshot.peak_observed_at = timezone.now()
        snapshot.billable_children = pricing.billable_children(peak=peak, included=included)
        snapshot.save(
            update_fields=["peak_children", "peak_observed_at", "billable_children", "updated_at"]
        )
    return snapshot


def record_daily_usage(*, subscription: Subscription) -> UsageSnapshot:
    """
    Kunlik o'lchov — eng yuqori nuqtani yozib boradi.

    **Nega eng yuqori, oy oxiridagi son emas?** Oy oxiridagi o'lchovni
    aldash oson: 30-kuni bolalarni nofaol qilib, 1-kuni qaytarish
    kifoya. Eng yuqori nuqta esa haqiqatda iste'mol qilingan xizmatni
    aks ettiradi (docs/03 §20.3).
    """
    today = timezone.localdate()
    peak = _current_child_count(subscription.organization_id)
    return _open_snapshot(subscription, today.year, today.month, peak)


@transaction.atomic
def close_period(*, snapshot: UsageSnapshot) -> UsageSnapshot:
    """
    O'lchovni muzlatadi — shundan keyin hisob undan chiqadi.

    Yopilgan qator o'zgarmaydi: agar keyin tuzatish kerak bo'lsa, u
    `manual_adjustment` qatori sifatida, majburiy izoh bilan qo'shiladi
    (D3 bilan bir xil intizom).
    """
    if snapshot.closed_at is not None:
        return snapshot
    snapshot.closed_at = timezone.now()
    snapshot.save(update_fields=["closed_at", "updated_at"])
    return snapshot


def adjust_usage(*, snapshot: UsageSnapshot, billable_children: int, note: str) -> UsageSnapshot:
    """
    Qo'lda tuzatish — YANGI qator sifatida, hech qachon tahrir emas.

    Izoh majburiy va bu bazada ham tekshiriladi: "kim va nega
    o'zgartirdi" javobsiz qolsa, dalilning butun ma'nosi yo'qoladi.
    """
    if not note.strip():
        raise BusinessRuleViolation(gettext("Tuzatish uchun izoh majburiy."))

    return UsageSnapshot.objects.create(
        organization=snapshot.organization,
        subscription=snapshot.subscription,
        period_year=snapshot.period_year,
        period_month=snapshot.period_month,
        peak_children=snapshot.peak_children,
        peak_observed_at=snapshot.peak_observed_at,
        billable_children=billable_children,
        measurement_method=MeasurementMethod.MANUAL_ADJUSTMENT,
        note=note.strip(),
        closed_at=timezone.now(),
    )


def projected_usage(*, subscription: Subscription) -> dict[str, Any]:
    """
    Joriy davr uchun **prognoz** — hisob emas.

    `is_projection: true` bezak emas: u raqam hali OLINMAGANINI
    bildiradi. Haqiqiy hisob doim yopilgan dalildan chiqadi. Bu
    endpointning umuman mavjudligi — ushlab qolish qarori: sonning
    o'zgarishini ko'rib turgan mijoz kutilmagan hisob olmaydi.
    """
    today = timezone.localdate()
    peak = _current_child_count(subscription.organization_id)
    snapshot = UsageSnapshot.objects.filter(
        subscription=subscription,
        period_year=today.year,
        period_month=today.month,
        measurement_method=MeasurementMethod.DAILY_PEAK,
    ).first()
    observed_peak = max(peak, snapshot.peak_children if snapshot else 0)

    # Oldindan to'langan muddat ichida baza allaqachon to'langan —
    # prognozda faqat o'sish ko'rsatiladi (docs/01 §4.3).
    prepaid = subscription.payment_term != PaymentTerm.MONTHLY and (
        subscription.current_period_start <= today <= subscription.current_period_end
    )
    committed = subscription.committed_children or 0
    # Oldindan to'langan muddatda baza ham, KELISHILGAN sondagi ortiqcha
    # ham allaqachon to'langan. Shuning uchun prognozda faqat o'sha
    # sondan oshgani ko'rsatiladi — aks holda ekran har oy hech qachon
    # kelmaydigan hisobni ko'rsatib turardi.
    quote = pricing.quote(
        plan=subscription.plan,
        peak_children=observed_peak,
        discount_percent=subscription.discount_percent,
        include_base=not prepaid,
        covered_children=committed if prepaid else None,
    )

    return {
        "period": {"year": today.year, "month": today.month},
        "current_children": peak,
        "peak_children": observed_peak,
        "included_children": quote.included_children,
        "billable_children": quote.billable_children,
        "overage_steps": quote.overage_steps,
        "prepaid_base": prepaid,
        "projected": {
            "base_amount": f"{quote.base_amount:.2f}",
            "overage_amount": f"{quote.overage_amount:.2f}",
            "discount_amount": f"{quote.discount_amount:.2f}",
            "total_amount": f"{quote.total_amount:.2f}",
            "currency": quote.currency,
        },
        "is_projection": True,
    }


# --- Hisob-faktura ---


def _next_invoice_number() -> str:
    """
    Vendor bo'ylab GLOBAL ketma-ketlik.

    Mijozlar bo'yicha emas: hujjatni yozayotgan taraf bitta — vendor, va
    uning raqamlash tartibi buxgalteriya uchun uzluksiz bo'lishi kerak.
    """
    year = timezone.localdate().year
    prefix = f"KG-{year}-"

    # Ketma-ketlik VENDOR bo'ylab global, ya'ni oxirgi raqamni topish
    # cross-tenant so'rov. RLS buni ochib berdi: `all_objects` ilova
    # filtridan qutuladi, lekin bazadagi siyosatdan emas — va tenant
    # kontekstida turib qidirilsa, boshqa mijozning hisobi ko'rinmay,
    # o'sha raqam QAYTA beriladi. Bu unique cheklovga urilardi, ya'ni
    # ikkinchi mijozning konvertatsiyasi yiqilardi.
    with platform_context():
        last = (
            SubscriptionInvoice.all_objects.filter(number__startswith=prefix)
            .order_by("-number")
            .values_list("number", flat=True)
            .first()
        )
    sequence = int(last.rsplit("-", 1)[1]) + 1 if last else 1
    return f"{prefix}{sequence:05d}"


@transaction.atomic
def issue_invoice(
    *,
    subscription: Subscription,
    snapshot: UsageSnapshot,
    period_start: date,
    period_end: date,
    months: int = 1,
    include_base: bool = True,
    covered_children: int | None = None,
) -> SubscriptionInvoice:
    """
    Yopilgan dalildan hisob-faktura yozadi.

    `covered_children` — oldindan to'langan muddat ichidagi o'sish
    hisobi uchun: mijoz kelishilgan songacha allaqachon to'lagan,
    ya'ni ortiqcha faqat undan oshgani uchun olinadi (docs/01 §4.3).
    """
    if snapshot.closed_at is None:
        raise BusinessRuleViolation(gettext("Yopilmagan oʻlchovdan hisob yozib boʻlmaydi."))

    quote = pricing.quote(
        plan=subscription.plan,
        peak_children=snapshot.billable_children,
        discount_percent=subscription.discount_percent,
        months=months,
        include_base=include_base,
        covered_children=covered_children,
    )

    today = timezone.localdate()
    return SubscriptionInvoice.objects.create(
        organization=subscription.organization,
        subscription=subscription,
        usage_snapshot=snapshot,
        number=_next_invoice_number(),
        issued_at=today,
        due_at=today + timedelta(days=GRACE_DAYS),
        period_start=period_start,
        period_end=period_end,
        # Summalar NUSXA qilinadi: hisob-faktura yuridik hujjat va u uch
        # yildan keyin ham aynan shunday ko'rinishi kerak.
        billable_children=quote.billable_children,
        base_amount=quote.base_amount,
        overage_amount=quote.overage_amount,
        discount_amount=quote.discount_amount,
        total_amount=quote.total_amount,
        currency=quote.currency,
    )


@transaction.atomic
def record_subscription_payment(
    *,
    invoice: SubscriptionInvoice,
    amount: Decimal,
    method: str = "bank_transfer",
    reference: str = "",
    recorded_by: Any = None,
) -> SubscriptionPayment:
    """
    Hisob bo'yicha tushumni yozadi va obunani faollashtiradi.

    Qator qulflanadi: ikkita platforma xodimi bir vaqtda bir xil
    o'tkazmani kiritsa, ikkinchisi ortiqcha to'lov yaratardi.
    """
    locked = SubscriptionInvoice.objects.select_for_update().get(pk=invoice.pk)
    if locked.status == SubscriptionInvoiceStatus.CANCELLED:
        raise BusinessRuleViolation(gettext("Bekor qilingan hisobga toʻlov yozib boʻlmaydi."))
    if amount <= 0:
        raise BusinessRuleViolation(gettext("Toʻlov summasi noldan katta boʻlishi kerak."))

    paid = sum((payment.amount for payment in locked.payments.all()), Decimal("0"))
    if paid + amount > locked.total_amount:
        raise BusinessRuleViolation(
            gettext("Ortiqcha toʻlov: qoldiq {v}, kiritilgan {amount}.").format(
                v=locked.total_amount - paid, amount=amount
            )
        )

    payment = SubscriptionPayment.objects.create(
        organization=locked.organization,
        subscription_invoice=locked,
        amount=amount,
        method=method,
        reference=reference,
        received_at=timezone.now(),
        recorded_by=recorded_by,
    )

    if paid + amount >= locked.total_amount:
        locked.status = SubscriptionInvoiceStatus.PAID
        locked.save(update_fields=["status", "updated_at"])

        subscription = locked.subscription
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.save(update_fields=["status", "updated_at"])

    return payment


# --- Rejalashtirilgan o'tishlar ---


def expire_trials() -> int:
    """Muddati tugagan, qabul qilinmagan sinovlarni bekor qiladi."""
    now = timezone.now()
    # Tenantlar bo'ylab — platforma tekisligi. `subscription`
    # metama'lumot jadvali, shuning uchun bu ochiq (docs/03 §6.3).
    with platform_context():
        expired = list(
            Subscription.all_objects.filter(
                status=SubscriptionStatus.TRIALING, trial_ends_at__lt=now
            )
        )
    count = 0
    for subscription in expired:
        with organization_context(subscription.organization_id):
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.cancelled_at = now
            subscription.save(update_fields=["status", "cancelled_at", "updated_at"])
        count += 1
    return count


def mark_past_due() -> int:
    """Muddati o'tgan hisoblarni belgilaydi va obunani `past_due` qiladi."""
    today = timezone.localdate()
    with platform_context():
        overdue = list(
            SubscriptionInvoice.all_objects.filter(
                status=SubscriptionInvoiceStatus.ISSUED, due_at__lt=today
            ).select_related("subscription")
        )

    count = 0
    for invoice in overdue:
        with organization_context(invoice.organization_id):
            invoice.status = SubscriptionInvoiceStatus.OVERDUE
            invoice.save(update_fields=["status", "updated_at"])

            subscription = invoice.subscription
            if subscription.status in (
                SubscriptionStatus.ACTIVE,
                SubscriptionStatus.PENDING_PAYMENT,
            ):
                subscription.status = SubscriptionStatus.PAST_DUE
                subscription.save(update_fields=["status", "updated_at"])
        count += 1
    return count


def suspend_unpaid(*, grace_days: int = GRACE_DAYS) -> int:
    """
    Kutish muddati tugagan to'lanmaganlarni faqat O'QISHGA o'tkazadi.

    Ma'lumot o'chirilmaydi va yashirilmaydi: mijoz o'z moliyaviy
    tarixini ko'rib turadi va istalgan payt to'lab qaytishi mumkin
    (docs/03 §20.6).
    """
    cutoff = timezone.localdate() - timedelta(days=grace_days)
    with platform_context():
        unpaid = list(
            SubscriptionInvoice.all_objects.filter(
                status=SubscriptionInvoiceStatus.OVERDUE, due_at__lt=cutoff
            ).select_related("subscription")
        )

    count = 0
    for invoice in unpaid:
        with organization_context(invoice.organization_id):
            subscription = invoice.subscription
            if subscription.status not in (
                SubscriptionStatus.SUSPENDED,
                SubscriptionStatus.CANCELLED,
            ):
                subscription.status = SubscriptionStatus.SUSPENDED
                subscription.save(update_fields=["status", "updated_at"])
                count += 1
    return count
