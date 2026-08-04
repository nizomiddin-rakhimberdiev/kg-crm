"""
Barcha muhitlar uchun umumiy sozlamalar.

Muhit-maxsus sozlamalar: development.py · production.py · test.py
Tuzilma: docs/02_Software_Architecture.md §5
"""

from datetime import timedelta
from pathlib import Path

import environ
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

# --- Asosiy ---
SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-dev-key-change-me")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# --- Ilovalar ---
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "django_filters",
    "corsheaders",
    "django_celery_beat",
]

# Tartib muhim: core (umumiy yadro) → organizations (tenancy ildizi) → qolganlari.
LOCAL_APPS = [
    "apps.core",
    "apps.organizations",
    "apps.branches",
    "apps.accounts",
    "apps.children",
    "apps.attendance",
    "apps.finance",
    "apps.hr",
    "apps.payroll",
    "apps.inventory",
    "apps.expenses",
    "apps.notifications",
    "apps.settings_app",
    "apps.reports",
    "apps.subscriptions",
    "apps.platform",
    "apps.audit",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# --- Middleware ---
# TenantMiddleware AuthenticationMiddleware dan KEYIN turishi shart:
# u tashkilotni autentifikatsiya qilingan foydalanuvchidan oladi.
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.core.middleware.TenantMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# --- Ma'lumotlar bazasi ---
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="kg_crm"),
        "USER": env("POSTGRES_USER", default="kg_crm"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="kg_crm"),
        "HOST": env("POSTGRES_HOST", default="localhost"),
        "PORT": env.int("POSTGRES_PORT", default=5432),
        "CONN_MAX_AGE": 60,
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ADR-4: biznes rollari Django guruhlari emas. Maxsus User modeli loyiha
# boshidan belgilanadi — AUTH_USER_MODEL ni keyin almashtirish Django'da
# eng og'riqli migratsiyalardan biri.
AUTH_USER_MODEL = "accounts.User"

# auth.E003 `USERNAME_FIELD` global unikal bo'lishini talab qiladi. Bizda email
# ATAYLAB faqat tashkilot ichida unikal (docs/03 §10.6): bir odam ikki bog'chada
# ishlashi mumkin, va global unikallik ro'yxatdan o'tishda "bu email boshqa
# tenant'da bor" faktini oshkor qilardi.
#
# Django bu tekshiruvni default ModelBackend email bo'yicha bitta foydalanuvchi
# topishiga tayangani uchun qo'yadi. Sprint 1 da email → tashkilot(lar)
# ko'pligini hal qiladigan maxsus backend qo'shiladi (docs/04 §5:
# `/auth/select-organization`). Sprint 0 da auth endpointi umuman yo'q.
#
# SHART: Sprint 1 da maxsus backend qo'shilmasa, bu qatorni o'chirib
# `AUTH_USER_MODEL` ni qayta ko'rib chiqish kerak.
SILENCED_SYSTEM_CHECKS = ["auth.E003"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Til va vaqt ---
LANGUAGE_CODE = env("LANGUAGE_CODE", default="uz")
TIME_ZONE = env("TIME_ZONE", default="Asia/Tashkent")
USE_I18N = True
USE_TZ = True  # D7: har doim timestamptz (UTC)

# --- Statik va media ---
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "mediafiles"

# --- Cache (Redis) ---
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://localhost:6379/0"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}

# --- Celery ---
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/2")
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Rejalashtirilgan vazifalar (docs/02 §18).
#
# `DatabaseScheduler` jadvalni bazadan o'qiydi, ya'ni buni admin orqali
# ham o'zgartirish mumkin. Bu yerdagi ro'yxat — BOSHLANG'ICH holat:
# yangi o'rnatishda kimdir "hisob-faktura generatsiyasini yoqishni
# unutdim" degan holatga tushmasligi uchun.
CELERY_BEAT_SCHEDULE = {
    # Har oyning 1-kuni, ertalab: oylik hisob-fakturalar.
    "generate-monthly-invoices": {
        "task": "finance.generate_monthly_invoices",
        "schedule": crontab(hour=2, minute=0, day_of_month="1"),
    },
    # Har kuni: muddati o'tganlarni belgilash.
    "mark-overdue-invoices": {
        "task": "finance.mark_overdue_invoices",
        "schedule": crontab(hour=3, minute=0),
    },
    # Har kuni tushdan oldin: qarzdorlarga eslatma. Kechqurun emas —
    # ota-onaga ish vaqtida yetib borsin.
    "send-debt-reminders": {
        "task": "reports.send_debt_reminders",
        "schedule": crontab(hour=10, minute=0),
    },
    # Har kecha: kesh va ledger solishtiruvi (docs/03 §26). Farq
    # topilsa log'ga yoziladi — kutib o'tirmasdan.
    "recompute-balances": {
        "task": "reports.recompute_balances",
        "schedule": crontab(hour=4, minute=30),
    },
    # --- Obuna (ADR-11) ---
    #
    # Kunlik o'lchov o'tkazib yuborilsa hisob KAMAYADI va o'tmishdagi
    # bolalar sonini qayta tiklab bo'lmaydi. Shuning uchun u eng
    # ertalabki vazifa va boshqa hech narsaga bog'liq emas.
    "record-daily-peak": {
        "task": "subscriptions.record_daily_peak",
        "schedule": crontab(hour=1, minute=0),
    },
    "close-subscription-periods": {
        "task": "subscriptions.close_periods_and_invoice",
        "schedule": crontab(hour=5, minute=0),
    },
    "expire-trials": {
        "task": "subscriptions.expire_trials",
        "schedule": crontab(hour=5, minute=30),
    },
    "subscription-dunning": {
        "task": "subscriptions.dunning",
        "schedule": crontab(hour=6, minute=0),
    },
}

# --- DRF (docs/04 §1–3) ---
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["apps.core.renderers.EnvelopeJSONRenderer"],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.EnvelopePageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "EXCEPTION_HANDLER": "apps.core.exceptions.envelope_exception_handler",
    # P5: deny-by-default. Ochiq endpoint har doim aniq belgilanadi.
    #
    # `SubscriptionWriteGate` bu yerda EMAS, har bir viewset'da.
    # Sabab: `DEFAULT_PERMISSION_CLASSES` view'da `permission_classes`
    # e'lon qilinishi bilan BUTUNLAY qoplanadi, va bu loyihada har bir
    # viewset uni e'lon qiladi. Ya'ni bu yerga yozish "global himoya
    # bor" degan yolg'on tuyg'u berardi, aslida esa hech qayerda
    # ishlamasdi. Unutib qoldirishdan `test_write_gate_is_everywhere`
    # himoya qiladi.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    # TenantJWTAuthentication tenant kontekstini o'rnatadi (apps/core/authentication.py).
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.core.authentication.TenantJWTAuthentication",
    ],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "120/hour",
        # Login alohida va qattiqroq — brute-force'ga qarshi (docs/02 §20.2).
        "login": env("LOGIN_THROTTLE_RATE", default="10/min"),
        # Eksport — eng qimmat endpoint: u butun davrni o'qiydi va fayl
        # yozadi. Cheklovsiz bo'lsa, tugmani qayta-qayta bosish bitta
        # mijozning ishchilarini band qilib, QOLGAN mijozlarning
        # vazifalarini navbatda ushlab turardi.
        "export": env("EXPORT_THROTTLE_RATE", default="20/hour"),
    },
}

# --- JWT (ADR-3) ---
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=env.int("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", default=15)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_TOKEN_LIFETIME_DAYS", default=7)),
    "ROTATE_REFRESH_TOKENS": True,
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# --- CORS ---
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:5173"])
CORS_ALLOW_CREDENTIALS = True

# --- SaaS / obuna (docs/01 §4) ---
TRIAL_DAYS = env.int("TRIAL_DAYS", default=15)
PAYMENT_GRACE_DAYS = env.int("PAYMENT_GRACE_DAYS", default=7)
CHURN_EXPORT_RETENTION_DAYS = env.int("CHURN_EXPORT_RETENTION_DAYS", default=30)

# --- Bildirishnomalar (docs/02 §17) ---
# Provayder adapter orqali almashtiriladi; real SMS shlyuzi birinchi
# mijozgacha kechiktirilgan (apps/notifications/providers.py).
NOTIFICATION_PROVIDER = env("NOTIFICATION_PROVIDER", default="console")

# --- Loglash ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "{levelname} {asctime} {name} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}
