"""Ildiz URL konfiguratsiyasi. Barcha API `/api/v1/` ostida (docs/02 §13)."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("api.v1.urls")),
]

if settings.DEBUG:
    urlpatterns += static(  # type: ignore[arg-type]
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )

# URL resolve bo'lmagan holatlar ham konvertda qaytsin (docs/04 §2).
handler404 = "apps.core.views.api_not_found"
handler500 = "apps.core.views.api_server_error"
