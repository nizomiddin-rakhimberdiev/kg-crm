"""`/api/v1/` URL'lari."""

from django.urls import path

from api.v1.router import router
from api.v1.views import ApiRootView, HealthCheckView
from apps.accounts.views_auth import (
    LoginView,
    LogoutView,
    MeView,
    PasswordChangeView,
    RefreshView,
    SelectOrganizationView,
    SignupView,
)

app_name = "v1"

auth_patterns = [
    path("auth/signup", SignupView.as_view(), name="auth-signup"),
    path("auth/login", LoginView.as_view(), name="auth-login"),
    path(
        "auth/select-organization",
        SelectOrganizationView.as_view(),
        name="auth-select-organization",
    ),
    path("auth/refresh", RefreshView.as_view(), name="auth-refresh"),
    path("auth/logout", LogoutView.as_view(), name="auth-logout"),
    path("auth/me", MeView.as_view(), name="auth-me"),
    path("auth/password/change", PasswordChangeView.as_view(), name="auth-password-change"),
]

urlpatterns = [
    path("", ApiRootView.as_view(), name="root"),
    path("health", HealthCheckView.as_view(), name="health"),
    *auth_patterns,
    *router.urls,
]
