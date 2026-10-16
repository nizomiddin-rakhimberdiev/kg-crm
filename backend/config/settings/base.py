"""
Barcha muhitlar uchun umumiy sozlamalar.

Muhit-maxsus sozlamalar: development.py · production.py · test.py
Tuzilma: docs/02_Software_Architecture.md §5
"""

from datetime import timedelta
from pathlib import Path

import environ
from celery.schedules import crontab
from corsheaders.defaults import default_headers as cors_default_headers
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

# --- Asosiy ---
# Default ataylab uzun (32+ bayt): qisqa kalit JWT imzosini zaiflashtiradi
# va PyJWT har bir token uchun ogohlantirish beradi. Prod'da bu default
# umuman ishlatilmaydi — u yerda kalit majburiy va uzunligi tekshiriladi.
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="insecure-dev-key-change-me-0123456789abcdef",  # noqa: S106
)
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
    "apps.cash",
    "apps.hr",
    "apps.payroll",
    "apps.inventory",
    "apps.expenses",
    "apps.notifications",
    "apps.settings_app",
    "apps.reports",
    "apps.subscriptions",
    "apps.platform",
    "apps.intelligence",
    "apps.online_payments",
    "apps.parent_bot",
    "apps.contracts",
    "apps.kitchen",
    "apps.audit",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# --- Middleware ---
# TenantMiddleware AuthenticationMiddleware dan KEYIN turishi shart:
# u tashkilotni autentifikatsiya qilingan foydalanuvchidan oladi.
MIDDLEWARE = [
    # Eng tashqarida: identifikator BARCHA log yozuvlarini qamrashi
    # kerak, shu jumladan boshqa middleware'lardagi xatolarni ham.
    "apps.core.logging.RequestIdMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # Javob tili — `Accept-Language` dan (frontend ilova tilini yuboradi).
    # URL prefiksi yo'q (`i18n_patterns` ishlatilmaydi): API manzili bitta,
    # faqat xabar matni o'zgaradi. Sukut — LANGUAGE_CODE (uz).
    "django.middleware.locale.LocaleMiddleware",
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

# Minimal uzunlik — 12, Django sukuti 8 emas (PLAN 11.10).
#
# Tizim bolalarning shaxsiy maʼlumotini va pulni saqlaydi; OWASP ASVS
# shunday ilova uchun 12 belgini talab qiladi. Kirish 20/min bilan
# cheklangan, yaʼni onlayn tanlash sekin — asosiy xavf zaif yoki
# boshqa saytdan oʻgʻirlangan parol, va unga qarshi UZUNLIK ishlaydi.
#
# **Murakkablik qoidasi ataylab YOʻQ.** Aynan u xodimni parolni
# qogʻozga yozishga majbur qiladi; uzunlik esa qilmaydi —
# "bahorbogchasi2026" oson eslanadi va teriladi. ADR-24 bogʻcha
# xodimlari haqida shu mulohazani yuritadi va bu unga zid emas.
#
# Mavjud parollar TEGILMAYDI: validator faqat parol oʻrnatilganda
# ishlaydi, yaʼni hech kim tizimdan chiqib qolmaydi.
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Til va vaqt ---
# Foydalanuvchiga boradigan xabarlar (validatsiya, xatolar, tanlov yorliqlari)
# manbada O'ZBEKCHA yoziladi va `gettext` bilan o'raladi; ru/en tarjimalari
# `locale/<til>/LC_MESSAGES/django.po` da. Yangi xabar qo'shilganda:
#   python manage.py makemessages -l ru -l en --ignore=.venv --ignore=venv
#   (tarjimani yozing) → python manage.py compilemessages
# Docker tasviri `compilemessages` ni build paytida bajaradi.
LANGUAGE_CODE = env("LANGUAGE_CODE", default="uz")
LANGUAGES = [("uz", "O‘zbekcha"), ("ru", "Русский"), ("en", "English")]
# Ikkita katalog:
#   `locale/`             — o'zimizning xabarlar, `makemessages` yuritadi (ru, en).
#   `vendor_i18n/locale/` — DRF va Django'ning O'Z xabarlari o'zbekchada, QO'LDA.
#     DRF'da uz tili umuman yo'q, Django'da qisman: ularsiz ilovaning asosiy
#     tili o'zbekcha bo'la turib "This field may not be blank." chiqardi.
#     Papka ataylab `locale` deb nomlangan — `compilemessages` uni sozlamasiz
#     ham topadi (Docker build), `makemessages` esa faqat LOCALE_PATHS[0] ga
#     yozadi, ya'ni bu faylni hech qachon ustidan yozmaydi.
LOCALE_PATHS = [BASE_DIR / "locale", BASE_DIR / "vendor_i18n" / "locale"]
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

# --- Ishonchlilik ---
#
# Avval bu yerda hech narsa yo'q edi va sukut bo'yicha Celery vazifani
# ISHGA TUSHISHIDAN OLDIN tasdiqlaydi. Ya'ni ishchi vazifa o'rtasida
# yiqilsa (OOM, deploy, server qayta yuklandi) — vazifa jimgina
# YO'QOLADI. Oyning 1-kunidagi hisob-faktura generatsiyasi uchun bu
# "o'sha oy hisoblari chiqmadi va buni hech kim bilmadi" degani.
#
# `acks_late` buni teskari qiladi: vazifa TUGAGANDAN keyin tasdiqlanadi,
# yiqilsa qayta yetkaziladi. Buning sharti — vazifalar idempotent
# bo'lishi. Ular shunday: hisob-faktura `uq_invoice_child_period` qisman
# indeksi bilan bazada himoyalangan, qarz eslatmasi esa kunlik
# takrorlanishni `queue_debt_reminders` ichida to'xtatadi.
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True

# `acks_late` bilan birga MAJBURIY: sukut bo'yicha ishchi o'ziga bir
# nechta vazifani oldindan oladi va ular yiqilganda hammasi qayta
# yetkaziladi. Bittadan olish qayta bajarish doirasini bitta vazifa
# bilan cheklaydi.
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# Osilgan vazifa ishchini ABADIY band qilmasin. Yumshoq chegara avval
# ishlaydi va `SoftTimeLimitExceeded` ko'taradi — vazifa o'zini tartibli
# yig'ib ulgurishi uchun; qattiq chegara esa kafolat.
CELERY_TASK_SOFT_TIME_LIMIT = env.int("CELERY_SOFT_TIME_LIMIT", default=540)
CELERY_TASK_TIME_LIMIT = env.int("CELERY_TIME_LIMIT", default=600)

# Redis brokerida "ko'rinmaslik muddati" — ishchi shu vaqt ichida
# tasdiqlamasa, vazifa boshqasiga beriladi. U `TIME_LIMIT` dan KATTA
# bo'lishi shart: teng yoki kichik bo'lsa, uzoq (lekin sog'lom) vazifa
# hali ishlayotgan paytda ikkinchi ishchiga ham berilardi — ya'ni sozlama
# o'zi takrorlanish yaratardi.
CELERY_BROKER_TRANSPORT_OPTIONS = {"visibility_timeout": 900}

# Broker deploy paytida bir soniyaga yo'qolsa, ishchi yiqilib qolmasin.
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# Natijalar abadiy saqlanmasin — ular faqat diagnostika uchun.
CELERY_RESULT_EXPIRES = timedelta(days=2)
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
    # Har kuni tunda: eskirgan va yetim eksport fayllari.
    #
    # Eksport — vaqtinchalik hujjat, lekin uni hech narsa o'chirmasdi:
    # `debtors-…csv` oilalarning ismi va qarzi bilan serverda cheksiz
    # yotaverardi. Bir marta qo'lda tozalash yetmaydi — ertaga yana
    # yig'ila boshlaydi (PLAN 11.9).
    "purge-old-exports": {
        "task": "reports.purge_old_exports",
        "schedule": crontab(hour=4, minute=30),
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
    # Navbatdagi xabarlarni uzatish — har 5 daqiqada.
    #
    # To'lov kvitansiyasi `record_payment` ichida NAVBATGA qo'yiladi,
    # lekin u yerda uzatilmaydi: pul qabul qilish SMS shlyuzining
    # tirikligiga bog'liq bo'lmasligi kerak. Bu vazifa esa navbatni
    # bo'shatadi. Usiz kvitansiya xabari `queued` holatda abadiy
    # qolardi — xatosiz va jimgina.
    "dispatch-queued-notifications": {
        "task": "notifications.dispatch_queued",
        "schedule": crontab(minute="*/5"),
    },
    # Har kecha: kesh va ledger solishtiruvi (docs/03 §26). Farq
    # topilsa log'ga yoziladi — kutib o'tirmasdan.
    "recompute-balances": {
        "task": "reports.recompute_balances",
        "schedule": crontab(hour=4, minute=30),
    },
    # Radix Intelligence (docs/07 §11): `mark-overdue-invoices` (03:00) dan
    # KEYIN — qoida `status` ga tayanmasa ham, ikkisi bir kechada bir xil
    # manzarani ko'rsin.
    "generate-insights": {
        "task": "intelligence.generate_insights",
        "schedule": crontab(hour=3, minute=30),
    },
    # Egaga kunlik xulosa (Bosqich 13.4): har soat boshida; har bog'cha o'z
    # soatini (`alerts.digest_hour`) tanlaydi, vazifa o'sha soatda yuboradi.
    "send-daily-digests": {
        "task": "intelligence.send_daily_digests",
        "schedule": crontab(minute=0),
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
    # Anonim VA kirgan foydalanuvchi — ikkalasi ham cheklanadi.
    #
    # Avval faqat `AnonRateThrottle` bor edi, ya'ni kirgan foydalanuvchi
    # umuman cheklovsiz edi. Bu ko'p ijarali tizimda alohida ma'noga ega:
    # bitta mijozning skripti (yoki cheksiz aylanadigan sahifasi) butun
    # serverni band qilib, QOLGAN bog'chalarni sekinlashtirardi. Chegara
    # keng — normal ishlashga xalaqit bermaydi, lekin nosozlikni bitta
    # tenant bilan cheklaydi.
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "120/hour",
        "user": env("USER_THROTTLE_RATE", default="2000/hour"),
        # Login alohida — brute-force'ga qarshi (docs/02 §20.2).
        #
        # Chegara IP bo'yicha, bog'chada esa HAMMA bitta Wi-Fi ortida: 10/min
        # da o'nta xodim birga kirishga urinsa (yoki bir nechtasi parolni
        # xato tersa — birinchi kuni odatiy hol) oxirgilari "so'rovlar soni
        # chegaradan oshdi" olardi va bu tizim buzuq degan taassurot berardi.
        # 20/min onlayn brute-force uchun baribir foydasiz, lekin jamoaviy
        # ishga xalaqit bermaydi; muvaffaqiyatsiz urinishlar auditga tushadi.
        "login": env("LOGIN_THROTTLE_RATE", default="20/min"),
        # Token yangilash — ALOHIDA va keng.
        #
        # Access token faqat xotirada yashaydi (XSS uchun), ya'ni HAR sahifa
        # yuklanishi va har 15 daqiqada bitta `POST /auth/refresh` bo'ladi.
        # So'rov anonim (token sarlavhada emas, tanada), shuning uchun u
        # `anon` = 120/soat chegarasiga tushardi — bitta IP ortidagi butun
        # bog'cha uchun. Natija: ish o'rtasida 429 → mijoz sessiyani
        # tugagan deb hisoblaydi → xodimlar tizimdan chiqib ketadi.
        # Bu yerda chegara xavfsizlik vositasi emas (refresh token —
        # 100+ belgili tasodifiy sir, uni topish imkonsiz); u faqat
        # suiiste'molni cheklaydi.
        "refresh": env("REFRESH_THROTTLE_RATE", default="60/min"),
        # Eksport — eng qimmat endpoint: u butun davrni o'qiydi va fayl
        # yozadi. Cheklovsiz bo'lsa, tugmani qayta-qayta bosish bitta
        # mijozning ishchilarini band qilib, QOLGAN mijozlarning
        # vazifalarini navbatda ushlab turardi.
        "export": env("EXPORT_THROTTLE_RATE", default="20/hour"),
        # Public lead endpoint: normal foydalanuvchi formani bir marta
        # yuboradi, bot esa qisqa vaqtda ko'p marta. Chegara privacy va
        # operator vaqtini himoya qiladi; CAPTCHA keyingi qatlam sifatida
        # deploy konfiguratsisida qo'shilishi mumkin.
        "lead": env("LEAD_THROTTLE_RATE", default="5/hour"),
        # Self-signup (PLAN 6.7): every request sends an e-mail.
        "signup": env("SIGNUP_THROTTLE_RATE", default="5/hour"),
        "public_pricing": env("PUBLIC_PRICING_THROTTLE_RATE", default="120/min"),
        # Telegram webhook: Telegram o'zi tezlikni ushlab turadi va
        # bitta bog'cha uchun update'lar kam. Chegara ataylab keng —
        # haqiqiy update'ni yo'qotish ota-onaning ulanmay qolishi
        # degani, va u buni "ishlamadi" deb tushunadi.
        "telegram_webhook": env("TELEGRAM_WEBHOOK_THROTTLE_RATE", default="600/min"),
        # Parolni tiklash: har so'rov XAT yuboradi, ya'ni cheklovsiz
        # endpoint begona odamga bizning pochtamiz bilan boshqa odamni
        # bezovta qilish imkonini berardi. Normal odam parolni kuniga
        # bir-ikki marta tiklaydi.
        "password_reset": env("PASSWORD_RESET_THROTTLE_RATE", default="5/hour"),
    },
}

# --- Cookie bilan ishlash (PLAN 5.1) ---
#
# Refresh token `httpOnly` cookie'da. Brauzer uni faqat o'sha
# origin'ga yuboradi, lekin ishlab chiqishda frontend boshqa portda
# (`localhost:5173` → `localhost:8000`) va cookie'li so'rov uchun
# server ham ruxsat berishi kerak.
CORS_ALLOW_CREDENTIALS = True

# `Strict` cookie uchun domenlar ro'yxati. Django POST so'rovida
# `Origin` ni shu ro'yxat bilan solishtiradi.
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=["http://localhost:5173", "http://127.0.0.1:5173"],
)

# --- Pochta (PLAN 5.2) ---
#
# Parolni tiklash havolasi email bilan ketadi: xodimning telefoni
# almashishi mumkin, email esa hisobning o'zi (login).
#
# Sukut — KONSOL: sozlanmagan muhitda xat log'ga yoziladi va hech
# qayerga ketmaydi. Bu ongli tanlov: yarim sozlangan SMTP xatni
# jimgina yo'qotardi va foydalanuvchi "havola kelmadi" deb kutib
# o'tirardi (ADR-22 bilan bir xil mantiq — yetkazilmagan xabar
# "yuborildi" deb ko'rinmasligi kerak).
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Radix CRM <noreply@radix-crm.uz>")

#: Havoladagi manzil. Frontend va backend bir domenda bo'lsa ham
#: alohida sozlama: lokal ishlab chiqishda ular boshqa portda.
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:5173")

# Parolni tiklash havolasi 30 daqiqa yashaydi (PLAN 5.2).
#
# Django'ning standart qiymati 3 kun — pochta qutisiga kirgan odam
# uchun uzoq oyna. 30 daqiqa: havola xodimning o'zi so'ragan paytda
# ishlaydi, keyin esa o'lik qog'oz.
PASSWORD_RESET_TIMEOUT = env.int("PASSWORD_RESET_TIMEOUT", default=30 * 60)

# --- Kirish urinishlari chegarasi (PLAN 5.3) ---
#
# Tezlik chegarasi (`login` throttle) IP bo'yicha va JAMOAVIY:
# bog'chada hamma bitta Wi-Fi ortida. Bu esa HISOB bo'yicha ikkinchi
# qatlam — bitta hisobga qarshi parol terishni to'xtatadi, hujumchi
# IP'ni almashtirsa ham.
#
# Blok qisqa (15 daqiqa) va avtomatik yechiladi: abadiy blok qo'lda
# aralashuvni talab qiladi, ya'ni bog'chaning ishi egasining
# telefoniga bog'liq bo'lib qolardi.
LOGIN_MAX_ATTEMPTS = env.int("LOGIN_MAX_ATTEMPTS", default=10)
LOGIN_BLOCK_SECONDS = env.int("LOGIN_BLOCK_SECONDS", default=15 * 60)

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

# `Idempotency-Key` standart ro'yxatda YO'Q, uni ochiq qo'shish kerak.
#
# Productionda SPA va API bitta origin'da (nginx `/` va `/api/`), ya'ni
# preflight umuman bo'lmaydi va kamchilik ko'rinmaydi. Ammo lokal ishlab
# chiqishda (`:5173` → `:8001`) va API alohida domenga chiqarilganda
# (`app.` / `api.`) brauzer to'lov so'rovini BUTUNLAY bloklaydi — ya'ni
# ikki marta yozishdan himoya (docs/04 §1) jimgina yo'qoladi.
# `x-csrftoken` — cookie bilan ishlaydigan yangilash so'rovi uchun
# (PLAN 5.1). `corsheaders` ning sukut ro'yxatida u bor, lekin bu
# yerda ataylab ko'rsatilgan: ro'yxat qo'lda yozilgan va sukut
# o'zgarsa, sabab ko'rinmaydigan `CORS` xatosi chiqardi.
CORS_ALLOW_HEADERS = (*cors_default_headers, "idempotency-key", "x-csrftoken")

# --- Mijoz manzili (apps/core/tenant_address.py) ---
#
# `TENANT_URL_STYLE` ni `subdomain` ga o'zgartirish — kelajakdagi
# ko'chishning BUTUN backend qismi. Buning uchun wildcard DNS va
# wildcard TLS sertifikati kerak bo'ladi; shu tayyor bo'lmaguncha
# `path` qoladi.
PUBLIC_BASE_URL = env("PUBLIC_BASE_URL", default="http://localhost:5173")
TENANT_URL_STYLE = env("TENANT_URL_STYLE", default="path")

# --- Deploy rejimi (docs/02 ADR-13) ---
#
# `saas`       — radix-crm.uz dagi ko'p ijarachili xizmat (obuna bilan).
# `standalone` — bitta bog'cha uchun, uning O'Z serverida, bir martalik
#                to'lov evaziga: obuna, tarif va sinov muddati yo'q.
#
# Noto'g'ri yozilgan qiymat JIMGINA `saas` ga tushmasligi kerak: mijoz
# serverida obuna darvozasi kutilmaganda yonib, butun bog'chani yozishdan
# to'xtatardi — va sabab `.env` dagi bitta harf xatosi bo'lardi.
DEPLOYMENT_MODE = env("DEPLOYMENT_MODE", default="saas")
if DEPLOYMENT_MODE not in ("saas", "standalone"):
    raise ImproperlyConfigured(
        f"DEPLOYMENT_MODE noto'g'ri: {DEPLOYMENT_MODE!r}. 'saas' yoki 'standalone' bo'lishi kerak."
    )

# --- SaaS / obuna (docs/01 §4) ---
# Platforma (vendor) konsolida ikkinchi omil — TOTP (ADR-15, ADR-24).
#
# Sukut YOQILGAN (ADR-24, 2026-10-02 — ADR-15 dagi "o'chiq" qarorini
# bekor qiladi). Sabab o'zgardi: konsol bitta parol ortida butun mijoz
# ro'yxatini, obunalarni va qo'llab-quvvatlash ruxsatlarini boshqaradi,
# ya'ni u eng qimmatli bitta hisob. Zaxira kodlari (PLAN 5.4) qulflanib
# qolish xavfini olib tashladi — ilgari aynan shu xavf "keyin yoqaman"
# qarorining asosi edi.
#
# Kalit QOLADI: standalone o'rnatma yoki namoyish nusxasida uni
# o'chirish kerak bo'lishi mumkin, va bu bitta `.env` qatori.
PLATFORM_2FA_REQUIRED = env.bool("PLATFORM_2FA_REQUIRED", default=True)

# --- Online payments (PLAN 6.1, ADR-26) ---
#
# Fernet key that encrypts kindergartens' Payme / Click secrets at rest.
# Generate: see the MERCHANT_SECRET_KEY note in .env.example.
# In development an empty value falls back to a key derived from SECRET_KEY;
# in production (`MERCHANT_KEY_REQUIRED`) saving a merchant key without it
# is refused — the server still boots, so a missing value cannot take the
# whole site down on deploy.
MERCHANT_SECRET_KEY = env("MERCHANT_SECRET_KEY", default="")
MERCHANT_KEY_REQUIRED = env.bool("MERCHANT_KEY_REQUIRED", default=False)

# Parent bot contact index (ADR-27): HMAC key for phone / chat digests.
# Empty = derived from SECRET_KEY. Changing it (or SECRET_KEY) requires
# `python manage.py rebuild_contact_index --apply`.
# Frozen product modules (apps/core/features.py): built and tested, switched
# off until a customer needs them. Tables exist either way.
FEATURE_CONTRACTS = env.bool("FEATURE_CONTRACTS", default=False)
FEATURE_KITCHEN = env.bool("FEATURE_KITCHEN", default=False)

CONTACT_INDEX_KEY = env("CONTACT_INDEX_KEY", default="")

# Radix's OWN merchant for subscription invoices (PLAN 6.4, P6-3). Empty =
# the "pay online" button is hidden and bank transfer stays the way to pay.
RADIX_PAYME_MERCHANT_ID = env("RADIX_PAYME_MERCHANT_ID", default="")
RADIX_PAYME_KEY = env("RADIX_PAYME_KEY", default="")
RADIX_PAYME_SANDBOX = env.bool("RADIX_PAYME_SANDBOX", default=False)
RADIX_CLICK_MERCHANT_ID = env("RADIX_CLICK_MERCHANT_ID", default="")
RADIX_CLICK_SERVICE_ID = env("RADIX_CLICK_SERVICE_ID", default="")
RADIX_CLICK_SECRET = env("RADIX_CLICK_SECRET", default="")

TRIAL_DAYS = env.int("TRIAL_DAYS", default=15)
PAYMENT_GRACE_DAYS = env.int("PAYMENT_GRACE_DAYS", default=7)
CHURN_EXPORT_RETENTION_DAYS = env.int("CHURN_EXPORT_RETENTION_DAYS", default=30)

# --- Bildirishnomalar (docs/02 §17) ---
# Provayder adapter orqali almashtiriladi; real SMS shlyuzi birinchi
# mijozgacha kechiktirilgan (apps/notifications/providers.py).
NOTIFICATION_PROVIDER = env("NOTIFICATION_PROVIDER", default="console")

# --- Eskiz.uz (Q8, PLAN 3.1) ---
#
# Uchalasi ham bo'lmasa provayder ishga tushmaydi. `ESKIZ_FROM`
# ataylab majburiy: Eskiz tasdiqlanmagan jo'natuvchi nomi bilan
# xabarni QABUL qiladi, lekin yetkazmaydi — jurnal "yuborildi"
# deydi, ota-ona esa hech narsa olmaydi.
ESKIZ_EMAIL = env("ESKIZ_EMAIL", default="")
ESKIZ_PASSWORD = env("ESKIZ_PASSWORD", default="")
ESKIZ_FROM = env("ESKIZ_FROM", default="")

# --- Telegram: yangi ariza haqida ogohlantirish (PLAN 3.6) ---
#
# Sozlanmagan bo'lsa ogohlantirish jimgina o'tkazib yuboriladi va
# ariza baribir saqlanadi: bildirishnoma qulaylik, ma'lumot esa
# biznes. Chat ID manfiy bo'lishi mumkin (guruh) — shuning uchun u
# satr sifatida o'qiladi.
# Bitta bot ikki ish qiladi: sotuvga yangi ariza haqida xabar beradi
# va ota-onalarga bog'cha xabarlarini yuboradi (ADR-23). Token bo'sh
# bo'lsa ikkalasi ham jimgina o'chadi.
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN", default="")
TELEGRAM_LEADS_CHAT_ID = env("TELEGRAM_LEADS_CHAT_ID", default="")

# Bot nomi — ota-onaga beriladigan havola uchun (`t.me/<nom>?start=…`).
# Bo'sh bo'lsa ekran havola emas, "bot sozlanmagan" deb ko'rsatadi:
# ishlamaydigan havolani berib qo'yish eng yomon variant.
TELEGRAM_BOT_USERNAME = env("TELEGRAM_BOT_USERNAME", default="")

# Webhook URL'ining maxfiy qismi. Bo'sh bo'lsa endpoint `404` beradi —
# ya'ni sozlanmagan o'rnatmada u umuman mavjud emas.
TELEGRAM_WEBHOOK_SECRET = env("TELEGRAM_WEBHOOK_SECRET", default="")

# Konsol provayderi xabar MATNINI log'ga yozsinmi.
#
# Sukut bo'yicha YO'Q: matn ichida bolaning ismi, summa va bog'cha nomi
# bor. Faqat lokal disk bilan cheklanmagan joyga (monitoring, zaxira,
# xato kuzatuvi) tushadigan log'da bularning o'rni yo'q.
NOTIFICATION_LOG_BODY = env.bool("NOTIFICATION_LOG_BODY", default=False)

# --- Loglash ---
# Loglar STDOUT ga — fayl aylantirish (rotation) ham, disk to'lishi ham
# konteynerning ishi emas: Docker ularni o'zi yig'adi va cheklaydi.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {"()": "apps.core.logging.RequestIdFilter"},
    },
    "formatters": {
        # `request_id` har bir qatorda. Nosozlikni tekshirishda bu
        # farqni ko'rsatadi: "shu ID bo'yicha grep" — bitta
        # foydalanuvchining bitta harakatining butun izi.
        "verbose": {
            "format": "{levelname} {asctime} [{request_id}] {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "filters": ["request_id"],
        },
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}
