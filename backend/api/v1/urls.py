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
from apps.core.deployment import is_saas
from apps.notifications.views_webhook import TelegramWebhookView
from apps.organizations.views import OrganizationLogoView, OrganizationView
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
    *auth_patterns,
    *router.urls,
]

# Vendor tekisligi va sotuv yo'llari FAQAT SaaS nusxasida (ADR-13).
#
# Mijozning o'z serverida vendor konsoli ham, lead formasi ham, narx
# kalkulyatori ham ma'noga ega emas — u tizimni bir marta sotib olgan.
# Ular shunchaki yashirilmaydi, balki MARSHRUTLANMAYDI: ko'rinmaydigan,
# lekin javob beradigan yo'l — bu o'sha yo'lning ochiq qolgani.
if is_saas():
    urlpatterns += [
        path("organization/logo", OrganizationLogoView.as_view(), name="organization-logo"),
        path("public/leads", PublicLeadCreateView.as_view(), name="public-lead-create"),
        # Telegram webhook: maxfiy qism YO'LDA, chunki Telegram
        # ixtiyoriy sarlavha qo'yadi va eski botlar uni yubormaydi.
        path(
            "public/telegram/webhook/<str:secret>",
            TelegramWebhookView.as_view(),
            name="telegram-webhook",
        ),
        path("public/pricing", PublicPricingView.as_view(), name="public-pricing"),
        *platform_patterns,
    ]
