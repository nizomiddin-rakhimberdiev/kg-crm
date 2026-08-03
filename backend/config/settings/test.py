"""Test sozlamalari — tez va tashqi xizmatlarsiz."""

from .base import *  # noqa: F403
from .base import DATABASES  # noqa: F401

DEBUG = False
SECRET_KEY = "test-secret-key"  # noqa: S105 — faqat testlar uchun, deploy'ga chiqmaydi

# Parol hashlash testlarni sekinlashtirmasin.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
