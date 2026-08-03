"""Celery ilovasi va vazifalarni avtomatik topish."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("kg_crm")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
