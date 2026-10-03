from django.apps import AppConfig


class OnlinePaymentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.online_payments"
    label = "online_payments"
    verbose_name = "Online payments (Payme / Click)"
