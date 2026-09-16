"""Ildiz URL konfiguratsiyasi. Barcha API `/api/v1/` ostida (docs/02 §13)."""

from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

urlpatterns = [
    path("api/v1/", include("api.v1.urls")),
]

# Django admin — FAQAT lokal ishlab chiqishda (P2-006).
#
# Productionda u ADR-10 ga qarshi ikkinchi imtiyozli yo'l bo'lardi:
# sessiya bilan ishlaydi (JWT emas), 2FA talab qilmaydi, RBAC
# matritsasini chetlab o'tadi va `is_superuser` bilan hamma narsani
# ochadi. Vendor xodimi uchun platforma konsoli bor — u 2FA majburiy,
# har bir amal mijozning audit jurnalida ko'rinadi, va operatsion
# ma'lumotga faqat sabab yozilgan, muddatli ruxsat bilan kiriladi.
#
# Ustiga u RLS bilan ham nomuvofiq edi: sessiya yo'lida hech kim
# Postgres GUC'ini o'rnatmasdi, ya'ni admin sahifalari baribir bo'sh
# ko'rinardi. Ya'ni bu yo'l ishlamasdi ham, xavf ham tug'dirardi.
#
# Lokalda u qulay, shuning uchun butunlay olib tashlanmadi.
if settings.DEBUG:
    from django.contrib import admin

    urlpatterns += [path("admin/", admin.site.urls)]
    urlpatterns += static(  # type: ignore[arg-type]
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )

# URL resolve bo'lmagan holatlar ham konvertda qaytsin (docs/04 §2).
handler404 = "apps.core.views.api_not_found"
handler500 = "apps.core.views.api_server_error"
