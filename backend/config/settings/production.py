"""Ishlab chiqarish (production) sozlamalari."""

from .base import *  # noqa: F403
from .base import env

DEBUG = False

# Production'da SECRET_KEY majburiy — default bilan ishga tushmasin.
SECRET_KEY = env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

# Kalit HS256 uchun imzo kaliti ham hisoblanadi (`SIMPLE_JWT.SIGNING_KEY`),
# ya'ni uning uzunligi to'g'ridan-to'g'ri tokenlar qanchalik ishonchli
# imzolanishini belgilaydi. RFC 7518 §3.2 kamida 32 baytni talab qiladi.
# Ogohlantirish bilan cheklanmaymiz: zaif kalit bilan ishga tushgan server
# haftalab shu holatda qolib ketishi mumkin, shuning uchun boot'da to'xtaydi.
if len(SECRET_KEY.encode()) < 32:
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY kamida 32 bayt bo'lishi kerak (RFC 7518 §3.2). "
        'Yangi kalit: python -c "import secrets; print(secrets.token_urlsafe(48))"'
    )

# --- Xavfsizlik (docs/02 §20) ---
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
