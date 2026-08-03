"""Tenant kontekstini boshqaruvchi middleware."""

from __future__ import annotations

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from apps.core.tenancy import clear_current_organization, set_current_organization_id


class TenantMiddleware:
    """
    Kontekstni sessiya asosidagi so'rovlar uchun o'rnatadi va **har doim**
    so'rov oxirida tozalaydi.

    JWT so'rovlarida kontekstni `TenantJWTAuthentication` o'rnatadi (DRF
    autentifikatsiyasi middleware'dan keyin ishlaydi). Bu middleware esa
    Django admin kabi sessiya bilan ishlaydigan yo'llarni qoplaydi.

    Tozalash muhim: worker jarayonlari qayta ishlatiladi va oqib qolgan
    kontekst keyingi so'rovga begona tashkilot ma'lumotini ko'rsatishi mumkin.
    Tashkilot mijozdan HECH QACHON olinmaydi — na header, na query, na body
    orqali (docs/04 §1).
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = getattr(request, "user", None)
        organization_id = getattr(user, "organization_id", None) if user else None
        set_current_organization_id(organization_id)
        try:
            return self.get_response(request)
        finally:
            clear_current_organization()
