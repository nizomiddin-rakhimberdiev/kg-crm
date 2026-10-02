"""
Django darajasidagi xato handlerlari.

DRF ning exception handler'i faqat view'ga yetib borgan so'rovlarni ko'radi.
URL umuman resolve bo'lmasa (`/api/v1/mavjud-emas`) yoki middleware'da xato
yuz bersa, Django o'zining HTML sahifasini qaytaradi — bu esa "har bir javob
bitta konvertda" qoidasini buzadi (docs/04 §2) va frontend'dagi yagona
handler'ni ishdan chiqaradi.
"""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest, JsonResponse
from django.utils.translation import gettext

__all__ = ["api_not_found", "api_server_error"]

_API_PREFIX = "/api/"


def _envelope(code: str, message: str, status: int) -> JsonResponse:
    return JsonResponse(
        {"success": False, "error": {"code": code, "message": message, "details": None}},
        status=status,
    )


def api_not_found(request: HttpRequest, exception: Exception | None = None) -> Any:
    if request.path.startswith(_API_PREFIX):
        return _envelope("NOT_FOUND", gettext("Soʻralgan resurs topilmadi."), 404)
    from django.views.defaults import page_not_found

    return page_not_found(request, exception)  # type: ignore[arg-type]


def api_server_error(request: HttpRequest) -> Any:
    if request.path.startswith(_API_PREFIX):
        # Ichki tafsilotlar hech qachon mijozga chiqmaydi (docs/02 §20).
        return _envelope("INTERNAL_ERROR", gettext("Kutilmagan xatolik yuz berdi."), 500)
    from django.views.defaults import server_error

    return server_error(request)
