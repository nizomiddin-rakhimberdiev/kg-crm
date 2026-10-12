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

# --- Redis'siz lokal ishlatish ---
#
# Redis o'rnatilmagan mashinada (masalan Docker'siz Windows) kesh va
# Celery ulana olmaydi: so'rov limiti (throttle) keshga yozadi, shuning
# uchun HAR BIR ommaviy endpoint 500 beradi. `.env` ga
# `DEV_NO_REDIS=true` yozilsa, kesh xotirada ishlaydi, Celery vazifalari
# esa darhol (sinxron) bajariladi. Cheklov: `celery beat` ishlamaydi,
# ya'ni jadvalli xabarlar (Radix AI) avtomatik yuborilmaydi. Productionda
# va Docker'da bu o'zgaruvchi YOQILMAYDI.
if env.bool("DEV_NO_REDIS", default=False):
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}  # noqa: F811
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    CELERY_BROKER_URL = "memory://"
    CELERY_RESULT_BACKEND = "cache+memory://"
