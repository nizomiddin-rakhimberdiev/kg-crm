"""`/api/v1/` URL'lari."""

from django.urls import path

from api.v1.router import router
from api.v1.views import ApiRootView, HealthCheckView
from apps.accounts.views_auth import (
    InviteAcceptView,
    LoginView,
    LogoutView,
    MeView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    ProfilePhotoView,
    RefreshView,
    SelectOrganizationView,
    TelegramLinkView,
    TwoFactorBackupCodesView,
    TwoFactorConfirmView,
    TwoFactorDisableView,
    TwoFactorSetupView,
)
from apps.core.deployment import is_saas
from apps.notifications.views_webhook import TelegramWebhookView
from apps.online_payments.views import (
    ClickWebhookView,
    MerchantCredentialListView,
    MerchantCredentialView,
    PaymentLinkCreateView,
    PaymeWebhookView,
    PublicPayLinkView,
)
from apps.organizations.views import OrganizationLogoView, OrganizationView
from apps.platform.views import PlatformLoginView
from apps.platform.views_leads import PublicLeadCreateView, PublicPricingView
from apps.platform.views_signup import SignupConfirmView, SignupRequestView
from apps.subscriptions.views_online import (
    SubscriptionClickWebhookView,
    SubscriptionPaymeWebhookView,
)

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
    path("auth/telegram", TelegramLinkView.as_view(), name="auth-telegram"),
    path("auth/password/change", PasswordChangeView.as_view(), name="auth-password-change"),
    # Parolni tiklash — standalone nusxada ham kerak (ADR-13): u
    # vendor xizmati emas, hisobning o'ziga tegishli amal.
    path("auth/password-reset", PasswordResetRequestView.as_view(), name="auth-password-reset"),
    path(
        "auth/password-reset/confirm",
        PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
    # Taklif havolasi — yangi bog'cha egasi parolni o'zi o'rnatadi
    # (PLAN 5.5). Standalone nusxada ham kerak: u yerda ham birinchi
    # hisob shu yo'l bilan ochilishi mumkin.
    path("auth/invite/accept", InviteAcceptView.as_view(), name="auth-invite-accept"),
    # Ikki bosqichli tasdiqlash — o'z hisobi uchun (PLAN 5.4, ADR-24).
    path("auth/2fa/setup", TwoFactorSetupView.as_view(), name="auth-2fa-setup"),
    path("auth/2fa/confirm", TwoFactorConfirmView.as_view(), name="auth-2fa-confirm"),
    path("auth/2fa/disable", TwoFactorDisableView.as_view(), name="auth-2fa-disable"),
    path(
        "auth/2fa/backup-codes",
        TwoFactorBackupCodesView.as_view(),
        name="auth-2fa-backup-codes",
    ),
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
    path("organization/logo", OrganizationLogoView.as_view(), name="organization-logo"),
    *auth_patterns,
    # Online payments (PLAN 6.1, ADR-26). In BOTH deployment modes: a
    # standalone kindergarten takes Payme / Click into its own account too.
    path(
        "public/pay/payme/<uuid:organization_id>",
        PaymeWebhookView.as_view(),
        name="payme-webhook",
    ),
    path(
        "public/pay/click/<uuid:organization_id>",
        ClickWebhookView.as_view(),
        name="click-webhook",
    ),
    path("public/pay/link/<str:token>", PublicPayLinkView.as_view(), name="pay-link"),
    path("online-payments/links", PaymentLinkCreateView.as_view(), name="payment-link-create"),
    path(
        "online-payments/credentials",
        MerchantCredentialListView.as_view(),
        name="merchant-credentials",
    ),
    path(
        "online-payments/credentials/<str:provider>",
        MerchantCredentialView.as_view(),
        name="merchant-credential",
    ),
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
        path("public/leads", PublicLeadCreateView.as_view(), name="public-lead-create"),
        # Telegram webhook: maxfiy qism YO'LDA, chunki Telegram
        # ixtiyoriy sarlavha qo'yadi va eski botlar uni yubormaydi.
        path(
            "public/telegram/webhook/<str:secret>",
            TelegramWebhookView.as_view(),
            name="telegram-webhook",
        ),
        path("public/pricing", PublicPricingView.as_view(), name="public-pricing"),
        # Self-signup with a 14-day trial (PLAN 6.7, ADR-28).
        path("public/signup", SignupRequestView.as_view(), name="public-signup"),
        path("public/signup/confirm", SignupConfirmView.as_view(), name="public-signup-confirm"),
        # Radix's own merchant — subscription invoices (PLAN 6.4).
        path(
            "public/pay/subscription/payme",
            SubscriptionPaymeWebhookView.as_view(),
            name="subscription-payme-webhook",
        ),
        path(
            "public/pay/subscription/click",
            SubscriptionClickWebhookView.as_view(),
            name="subscription-click-webhook",
        ),
        *platform_patterns,
    ]
