"""Lokal ishlab chiqish sozlamalari."""

from .base import *  # noqa: F403
from .base import INSTALLED_APPS, env

DEBUG = env.bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = INSTALLED_APPS + ["django_extensions"]

# Lokalda brauzerda API'ni ko'rish qulay bo'lishi uchun.
REST_FRAMEWORK_BROWSABLE = True
