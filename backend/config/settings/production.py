"""Ishlab chiqarish (production) sozlamalari."""

from .base import *  # noqa: F403
from .base import DATABASES, env

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
# TLS'ga haydash — bu o'rnatishda nginx ham qiladi (deploy/nginx/tls.conf),
# ya'ni bu ikkinchi qatlam. Sozlanadigan bo'lishi SHART, chunki ikki
# holatda u zarar qiladi:
#
#   1. BIRINCHI DEPLOY. Sertifikat hali yo'q va nginx HTTP rejimda —
#      Django esa har bir so'rovni mavjud bo'lmagan HTTPS'ga haydaydi,
#      ya'ni API umuman ishlamaydi va nosozlik sababi ko'rinmaydi.
#   2. TLS yuqorida tugaganda (load balancer, Cloudflare) — u yerda
#      haydash allaqachon bo'lgan.
#
# Sukut bo'yicha YOQILGAN: xavfsiz holat default bo'lishi kerak, uni
# o'chirish esa ongli qaror bo'lsin.
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Django 4+ proxy ortidagi HTTPS so'rovlarda `Origin` ni tekshiradi va
# u ro'yxatda bo'lmasa POST'ni rad etadi. Bu faqat sessiya bilan
# ishlaydigan yo'llarga tegadi (`/admin/`) — API JWT ishlatadi va CSRF
# tekshiruvidan o'tmaydi. Baribir kerak: usiz admin panelida har bir
# saqlash `403` berardi, va sabab ko'rinmasdi.
CSRF_TRUSTED_ORIGINS = env.list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    default=[f"https://{host}" for host in ALLOWED_HOSTS if host not in ("*", "")],
)

# --- Baza ---
#
# Baza alohida hostda bo'lsa, ulanish shifrlanishi SHART: u orqali
# bolalarning shaxsiy ma'lumoti va parol hashlari o'tadi.
#
# Sukut bo'yicha `prefer`, `require` emas: bu o'rnatishda baza bir xil
# Docker tarmog'ida va u yerda TLS sertifikati yo'q — `require` bilan
# ilova umuman ulanolmasdi. Bazani tashqi hostga (masalan boshqarilgan
# Postgres) ko'chirganda buni `require` ga o'zgartirish SHART.
DATABASES["default"]["OPTIONS"] = {  # noqa: F405
    **DATABASES["default"].get("OPTIONS", {}),  # noqa: F405
    "sslmode": env("POSTGRES_SSLMODE", default="prefer"),
}
