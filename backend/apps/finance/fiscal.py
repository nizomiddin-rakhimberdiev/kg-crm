"""
Fiskal chek holati (Bosqich 13.8, brif §9; test 13).

* Naqd va karta (terminal) to'lovida chekni BOG'CHA beradi — onlayn-NKM
  yoki virtual kassa. Raqam yoki QR shu yerga yoziladi.
* Click va Payme chekini TO'LOV TIZIMI beradi — ular qoplangan hisoblanadi.
* Bank o'tkazmasi va oylikdan ushlash chek talab qilmaydi.
* Chek turi to'lov qaysi oy uchun ekanidan: oldindan — "avans", o'sha oy —
  "sotuv", o'tgan oy qarzi — "kredit".

Nazorat `fiscal.control_from` sanasidan boshlanadi: undan oldingi to'lovlar
"cheksiz" deb sanalmaydi — yoqilgan kuni eski oylar qizarib ketmasin.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext

from apps.core.exceptions import BusinessRuleViolation
from apps.finance.models import FiscalIssuer, FiscalKind, Payment, PaymentFiscal

__all__ = [
    "PROVIDER_METHODS",
    "REQUIRED_METHODS",
    "control_from",
    "coverage",
    "missing",
    "receipt_kind",
    "record_receipt",
]

#: Chekni bog'cha beradi.
REQUIRED_METHODS = ("cash", "terminal")
#: Chekni to'lov tizimi beradi.
PROVIDER_METHODS = ("click", "payme", "online")


def control_from(branch_id: Any = None) -> date | None:
    from apps.settings_app.services import get_setting

    value = str(get_setting(key="fiscal.control_from", branch=branch_id) or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def receipt_kind(payment: Payment) -> str:
    """To'lov sanasini u yopgan oy bilan solishtiradi."""
    paid = timezone.localtime(payment.paid_at).date()
    allocation = (
        payment.allocations.filter(released_at__isnull=True)
        .select_related("invoice")
        .order_by("invoice__period_year", "invoice__period_month")
        .first()
    )
    invoice = allocation.invoice if allocation else payment.invoice
    if invoice is None:
        return FiscalKind.ADVANCE
    period = (invoice.period_year, invoice.period_month)
    if period > (paid.year, paid.month):
        return FiscalKind.ADVANCE
    if period < (paid.year, paid.month):
        return FiscalKind.CREDIT
    return FiscalKind.SALE


@transaction.atomic
def record_receipt(
    *, payment: Payment, number: str = "", qr: str = "", user: Any = None
) -> PaymentFiscal:
    number, qr = str(number or "").strip()[:64], str(qr or "").strip()[:500]
    if not number and not qr:
        raise BusinessRuleViolation(gettext("Chek raqami yoki QR havolasini kiriting."))
    if payment.reversed_at is not None:
        raise BusinessRuleViolation(gettext("Qaytarilgan toʻlovga chek yozilmaydi."))
    issuer = (
        FiscalIssuer.PROVIDER if payment.method in PROVIDER_METHODS else FiscalIssuer.KINDERGARTEN
    )
    fiscal, _ = PaymentFiscal.objects.update_or_create(
        payment=payment,
        defaults={
            "organization_id": payment.organization_id,
            "branch_id": payment.branch_id,
            "number": number,
            "qr": qr,
            "issuer": issuer,
            "kind": receipt_kind(payment),
            "recorded_by": user,
        },
    )
    return fiscal


def _scope(organization_id: Any, branch_id: Any, start: date, end: date) -> Any:
    from datetime import datetime, time

    since = control_from(branch_id)
    if since is None or since > end:
        return Payment.objects.none()
    begin = max(start, since)
    payments = Payment.objects.filter(
        organization_id=organization_id,
        reversed_at__isnull=True,
        paid_at__gte=timezone.make_aware(datetime.combine(begin, time.min)),
        paid_at__lte=timezone.make_aware(datetime.combine(end, time.max)),
    )
    return payments.filter(branch_id=branch_id) if branch_id else payments


def missing(*, organization_id: Any, start: date, end: date, branch_id: Any = None) -> Any:
    """Bog'cha chek berishi kerak, lekin yozilmagan to'lovlar."""
    return _scope(organization_id, branch_id, start, end).filter(
        method__in=REQUIRED_METHODS, fiscal__isnull=True
    )


def coverage(*, organization_id: Any, start: date, end: date, branch_id: Any = None) -> dict:
    payments = _scope(organization_id, branch_id, start, end)
    required = payments.filter(method__in=REQUIRED_METHODS)
    total = required.count()
    covered = required.filter(fiscal__isnull=False).count()
    since = control_from(branch_id)
    return {
        "control_from": since.isoformat() if since else None,
        "required": total,
        "covered": covered,
        "provider": payments.filter(method__in=PROVIDER_METHODS).count(),
        "percent": f"{covered * 100 / total:.1f}" if total else None,
    }
