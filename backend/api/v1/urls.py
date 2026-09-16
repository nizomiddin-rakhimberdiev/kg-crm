"""`/api/v1/` URL'lari."""

from django.urls import path

from api.v1.router import router
from api.v1.views import ApiRootView, HealthCheckView
from apps.accounts.views_auth import (
    LoginView,
    LogoutView,
    MeView,
    PasswordChangeView,
    ProfilePhotoView,
    RefreshView,
    SelectOrganizationView,
)
from apps.organizations.views import OrganizationView
from apps.platform.views import PlatformLoginView
from apps.platform.views_leads import PublicLeadCreateView, PublicPricingView

app_name = "v1"

auth_patterns = [
    path("auth/login", LoginView.as_view(), name="auth-login"),
    path(
        "auth/select-organization",
        SelectOrganizationView.as_view(),
        name="auth-select-organization",
    ),
    path("auth/refresh", RefreshView.as_view(), name="auth-refresh"),
    path("auth/logout", LogoutView.as_view(), name="auth-logout"),
    path("auth/me", MeView.as_view(), name="auth-me"),
    path("auth/me/photo", ProfilePhotoView.as_view(), name="auth-me-photo"),
    path("auth/password/change", PasswordChangeView.as_view(), name="auth-password-change"),
]

# Platforma kirishi ALOHIDA yo'lda (ADR-10): mijoz `/auth/login` ni,
# vendor `/platform/auth/login` ni ishlatadi. Ikki yo'l, ikki jadval,
# ikki token turi — ular hech qachon almashinmaydi.
platform_patterns = [
    path("platform/auth/login", PlatformLoginView.as_view(), name="platform-login"),
]

urlpatterns = [
    path("", ApiRootView.as_view(), name="root"),
    path("health", HealthCheckView.as_view(), name="health"),
    # Singleton resurs — ID yo'q, tashkilot tokendan olinadi (docs/04 §16).
    path("organization", OrganizationView.as_view(), name="organization"),
    path("public/leads", PublicLeadCreateView.as_view(), name="public-lead-create"),
    path("public/pricing", PublicPricingView.as_view(), name="public-pricing"),
    *auth_patterns,
    *platform_patterns,
    *router.urls,
]
