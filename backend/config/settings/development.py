"""Lokal ishlab chiqish sozlamalari."""

from .base import *  # noqa: F403
from .base import INSTALLED_APPS, env

DEBUG = env.bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = INSTALLED_APPS + ["django_extensions"]

# Lokalda brauzerda API'ni ko'rish qulay bo'lishi uchun.
REST_FRAMEWORK_BROWSABLE = True

# Brauzer uchun `localhost` va `127.0.0.1` — IKKI XIL origin, garchi ular
# bir xil mashinaga ishora qilsa ham. Faqat bittasi ruxsat etilsa,
# ikkinchisida ochilgan sahifada HAR BIR so'rov jimgina bloklanadi va
# xato konsolda "Network Error" bo'lib ko'rinadi — sabab esa umuman
# boshqa joyda qidiriladi. Lokalda ikkalasi ham ochiq.
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:5173", "http://127.0.0.1:5173"],
)
