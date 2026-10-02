"""
Yagona xato formati va xato kodlari taksonomiyasi (docs/04 §2).

    {"success": false, "error": {"code": ..., "message": ..., "details": ...}}
"""

from __future__ import annotations

import logging
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.db import IntegrityError
from django.http import Http404
from django.utils.translation import gettext_lazy
from rest_framework import exceptions as drf_exceptions
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from apps.core.tenancy import TenantScopeMissing

logger = logging.getLogger(__name__)

__all__ = [
    "BusinessRuleViolation",
    "SubscriptionInactive",
    "envelope_exception_handler",
]


class BusinessRuleViolation(drf_exceptions.APIException):
    """422 — kirish ma'lumoti to'g'ri, lekin domen qoidasini buzadi."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = gettext_lazy("Bu amal biznes qoidasini buzadi.")
    default_code = "BUSINESS_RULE_VIOLATION"


class SubscriptionInactive(drf_exceptions.APIException):
    """
    402 — tashkilot to'xtatilgan: yozish bloklanadi, o'qish ishlaydi.

    Ma'lumot HECH QACHON o'chirilmaydi yoki yashirilmaydi (docs/03 §20.6).
    """

    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = gettext_lazy(
        "Obuna faol emas. Maʼlumotlarni oʻqish mumkin, oʻzgartirish mumkin emas."
    )
    default_code = "SUBSCRIPTION_INACTIVE"


_STATUS_TO_CODE = {
    400: "VALIDATION_ERROR",
    401: "AUTHENTICATION_REQUIRED",
    402: "SUBSCRIPTION_INACTIVE",
    403: "PERMISSION_DENIED",
    404: "NOT_FOUND",
    405: "VALIDATION_ERROR",
    409: "CONFLICT",
    422: "BUSINESS_RULE_VIOLATION",
    429: "RATE_LIMITED",
}

_DEFAULT_MESSAGES = {
    "VALIDATION_ERROR": gettext_lazy("Yuborilgan maʼlumot notoʻgʻri."),
    "AUTHENTICATION_REQUIRED": gettext_lazy("Autentifikatsiya talab qilinadi."),
    # Platforma konsoli: 2FA yoqilgan, lekin so'rovda `code` yo'q (ADR-15).
    "TOTP_REQUIRED": gettext_lazy("Authenticator kodini kiriting."),
    "PERMISSION_DENIED": gettext_lazy("Bu amalga ruxsat yoʻq."),
    "NOT_FOUND": gettext_lazy("Soʻralgan resurs topilmadi."),
    "CONFLICT": gettext_lazy("Bu amal mavjud maʼlumot bilan ziddiyatga kirdi."),
    "RATE_LIMITED": gettext_lazy("Soʻrovlar soni chegaradan oshdi."),
    "INTERNAL_ERROR": gettext_lazy("Kutilmagan xatolik yuz berdi."),
}


def _extract(detail: Any) -> tuple[str, Any]:
    """DRF `detail` dan (xabar, tafsilotlar) juftligini ajratadi."""
    if isinstance(detail, dict):
        message = str(_DEFAULT_MESSAGES["VALIDATION_ERROR"])
        if "detail" in detail and isinstance(detail["detail"], str):
            message = detail["detail"]
            detail = {k: v for k, v in detail.items() if k != "detail"}
        return message, detail or None
    if isinstance(detail, list):
        return (str(detail[0]) if detail else ""), {"non_field_errors": detail}
    return str(detail), None


def envelope_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """DRF xatolarini yagona konvertga soladi."""

    # Tenant konteksti yo'q — bu dasturchi xatosi, mijozga hech narsa aytilmaydi.
    if isinstance(exc, TenantScopeMissing):
        logger.exception("Tenant konteksti o'rnatilmagan holda so'rov bajarildi")
        return _error_response(500, "INTERNAL_ERROR", str(_DEFAULT_MESSAGES["INTERNAL_ERROR"]))

    # Django darajasidagi xatolarni DRF ekvivalentiga o'giramiz.
    if isinstance(exc, (Http404, ObjectDoesNotExist)):
        exc = drf_exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = drf_exceptions.PermissionDenied()
    elif isinstance(exc, IntegrityError):
        logger.warning("Integrity error: %s", exc)
        return _error_response(409, "CONFLICT", str(_DEFAULT_MESSAGES["CONFLICT"]))

    response = drf_exception_handler(exc, context)
    if response is None:
        # Ushlanmagan istisno: log'ga to'liq, mijozga hech qanday ichki tafsilot yo'q.
        logger.exception("Ushlanmagan istisno", exc_info=exc)
        return _error_response(500, "INTERNAL_ERROR", str(_DEFAULT_MESSAGES["INTERNAL_ERROR"]))

    code = _STATUS_TO_CODE.get(response.status_code, "INTERNAL_ERROR")
    if isinstance(exc, drf_exceptions.APIException) and isinstance(
        getattr(exc, "default_code", None), str
    ):
        # Maxsus istisnolar o'z kodini olib keladi (masalan SUBSCRIPTION_INACTIVE).
        declared = exc.default_code.upper()
        if declared in _DEFAULT_MESSAGES or declared in _STATUS_TO_CODE.values():
            code = declared

    message, details = _extract(response.data)
    response.data = {
        "success": False,
        "error": {"code": code, "message": message, "details": details},
    }
    return response


def _error_response(status_code: int, code: str, message: str) -> Response:
    return Response(
        {"success": False, "error": {"code": code, "message": message, "details": None}},
        status=status_code,
    )
