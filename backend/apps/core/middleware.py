"""Tenant kontekstini boshqaruvchi middleware."""

from __future__ import annotations

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from apps.core.rls import apply_tenant_setting, clear_request_settings
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

    **Ikkita holat tozalanadi, bittasi emas.** Kontekst ikki joyda
    yashaydi: Python `ContextVar` da (ilova filtri uchun) va Postgres
    GUC'ida (RLS uchun). Avval bu yerda faqat birinchisi tozalanardi.
    Natijada `CONN_MAX_AGE` bilan ulanish pulga GUC o'rnatilgan holda
    qaytardi, va RLS keyingi so'rovda "kontekst yo'q → hech narsa
    ko'rinmasin" o'rniga "kontekst yo'q → OLDINGI tenantni ko'rsat"
    holatiga tushardi. Ya'ni ikkinchi izolyatsiya qatlami fail-closed
    emas, fail-stale bo'lib qolgandi.

    Nega aynan shu yerda: bu so'rov hayot siklidagi ENG TASHQI nuqta
    bo'lib, `finally` unga har qanday yo'l bilan yetadi — normal javob,
    autentifikatsiya xatosi, ruxsat xatosi, ushlanmagan istisno. DRF
    javobni `_get_response` ichida render qiladi, ya'ni serializer'lar
    bazaga murojaat qilib bo'lgandan KEYIN bu yerga qaytiladi.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = getattr(request, "user", None)
        organization_id = getattr(user, "organization_id", None) if user else None
        set_current_organization_id(organization_id)
        # Sessiya yo'lida (JWT emas) GUC'ni ham SHU YER o'rnatadi.
        # Aks holda ilova filtri tashkilotni ko'rardi, RLS esa
        # ko'rmasdi — ikki qatlam bir-biriga zid javob berardi va
        # natija "hech narsa yo'q" bo'lardi.
        if organization_id is not None:
            apply_tenant_setting(organization_id)
        try:
            return self.get_response(request)
        finally:
            clear_current_organization()
            clear_request_settings()
