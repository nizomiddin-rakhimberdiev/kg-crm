"""`/api/v1/` URL'lari."""

from django.urls import path

from api.v1.router import router
from api.v1.views import ApiRootView, HealthCheckView

app_name = "v1"

urlpatterns = [
    path("", ApiRootView.as_view(), name="root"),
    path("health", HealthCheckView.as_view(), name="health"),
    *router.urls,
]
