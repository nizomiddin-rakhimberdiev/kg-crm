"""Test sozlamalari — tez va tashqi xizmatlarsiz."""

import tempfile
from pathlib import Path
from typing import cast

from .base import *  # noqa: F403
from .base import DATABASES  # noqa: F401

DEBUG = False

# Kalit kamida 32 bayt: JWT HS256 shu uzunlikni talab qiladi (RFC 7518 §3.2)
# va PyJWT qisqasiga ogohlantirish beradi. Testlarda ham haqiqiy uzunlik —
# aks holda ogohlantirish oqimi haqiqiy muammolarni ko'mib yuboradi.
SECRET_KEY = "test-secret-key-not-for-deploy-0123456789abcdef"  # noqa: S105

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
#
# Ro'yxat BAZADAN olinadi, qo'lda yozilmaydi: yangi throttle scope
# qo'shilganda bu yerni yangilashni unutish testlarni 500 xato bilan
# yiqitardi — va sabab endpointda emas, shu faylda bo'lardi.
REST_FRAMEWORK = {  # noqa: F405
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_RATES": dict.fromkeys(
        cast("dict[str, str]", REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]),  # noqa: F405
        None,
    ),
}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Testlar yozgan fayllar loyihaga tushib qolmasin — vaqtinchalik papka
# har bir ishga tushishda tozalanadi.
MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="kg-crm-test-media-"))

# Frozen modules stay TESTED: the suite runs with them switched on, so the
# code is ready the day a customer asks (apps/core/features.py).
FEATURE_CONTRACTS = True
FEATURE_KITCHEN = True
