from django.apps import AppConfig


class ParentBotConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.parent_bot"
    label = "parent_bot"
    verbose_name = "Parent bot"

    def ready(self) -> None:
        from apps.parent_bot import signals  # noqa: F401 — connects the receivers
