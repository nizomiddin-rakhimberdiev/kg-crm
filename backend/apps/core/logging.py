"""
So'rov izi — har bir so'rovga bitta identifikator (P1-008).

Muammo oddiy, lekin u faqat nosozlik paytida ko'rinadi: log'da yuzlab
qator bor, ularning qaysi biri bitta foydalanuvchining bitta bosishiga
tegishli ekani noma'lum. "Kecha soat 14:30 da xato chiqdi" degan
shikoyatni tekshirish shu sababli soatlab davom etadi.

Yechim ikki qismdan iborat:

  * `RequestIdMiddleware` har bir so'rovga `X-Request-ID` beradi (mijoz
    o'zi yuborsa — o'shani ishlatadi, ya'ni frontend xatosi bilan
    backend logi bitta ip bilan bog'lanadi);
  * `RequestIdFilter` uni har bir log qatoriga qo'shadi.

Identifikator JAVOBGA ham qo'shiladi. Shunda mijoz "xato bo'ldi" degan
ekranda kod ko'rsatadi va siz uni log'dan bir urinishda topasiz.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from contextvars import ContextVar

from django.http import HttpRequest, HttpResponse

__all__ = ["RequestIdMiddleware", "RequestIdFilter", "get_request_id", "HEADER"]

HEADER = "X-Request-ID"

# `ContextVar` — `threading.local` emas: u async view va Celery
# vazifalarida ham to'g'ri ishlaydi (apps/core/tenancy.py bilan bir xil
# sabab).
_request_id: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    return _request_id.get()


class RequestIdMiddleware:
    """So'rov identifikatorini o'rnatadi va javobga qaytaradi."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Mijoz bergan qiymat ISHLATILADI, lekin ishonchsiz manba
        # sifatida: uzunligi cheklanadi, aks holda log'ga bir necha
        # kilobaytlik "identifikator" yozib yuborish mumkin bo'lardi.
        incoming = (request.headers.get(HEADER) or "").strip()[:64]
        request_id = incoming or uuid.uuid4().hex[:16]

        token = _request_id.set(request_id)
        try:
            response = self.get_response(request)
            response[HEADER] = request_id
            return response
        finally:
            _request_id.reset(token)


class RequestIdFilter(logging.Filter):
    """Har bir log yozuviga `request_id` qo'shadi."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True
