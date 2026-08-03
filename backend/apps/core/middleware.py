"""Tenant kontekstini so'rovdan o'rnatuvchi middleware."""

from __future__ import annotations

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from apps.core.tenancy import clear_current_organization, set_current_organization_id


class TenantMiddleware:
    """
    Joriy tashkilotni **autentifikatsiya qilingan foydalanuvchidan** oladi.

    Tashkilot mijoz tomonidan HECH QACHON uzatilmaydi — na header, na query
    parametri, na body orqali (docs/04 §1). Aks holda u oddiy IDOR'ga
    aylanardi: token bir tashkilotniki, so'rov boshqasiniki.

    Har bir so'rov oxirida kontekst tozalanadi, chunki worker jarayonlari
    qayta ishlatiladi va oqib qolgan kontekst keyingi so'rovga tegishli
    bo'lmagan ma'lumot ko'rsatishi mumkin.
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
