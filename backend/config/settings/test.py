"""Test sozlamalari — tez va tashqi xizmatlarsiz."""

from .base import *  # noqa: F403
from .base import DATABASES  # noqa: F401

DEBUG = False
SECRET_KEY = "test-secret-key"  # noqa: S105 — faqat testlar uchun, deploy'ga chiqmaydi

# Parol hashlash testlarni sekinlashtirmasin.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# Throttling testlar orasida keshda qolib, aloqasiz testlarni yiqitadi.
# Shuning uchun u bu yerda o'chiriladi va ATAYLAB alohida sinaladi —
# `apps/accounts/tests/test_throttling.py` uni qayta yoqib tekshiradi.
#
# Kalitlar `None` qiymat bilan QOLDIRILADI: DRF `THROTTLE_RATES[scope]` ni
# izlaydi va kalit yo'q bo'lsa `KeyError` bilan yiqiladi. `None` esa
# "cheklov yo'q" degani.
REST_FRAMEWORK = {  # noqa: F405
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_RATES": {"anon": None, "login": None},
}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
