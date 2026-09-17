"""
Mijozning manzili — YAGONA joyda quriladi.

Bugun har bir bog'cha `https://kg-crm.uz/t/<slug>` da yashaydi. Ertaga
`https://<slug>.kg-crm.uz` ga o'tish mumkin, va o'sha o'tish shu fayldagi
bitta `if` ni almashtirish bo'lishi kerak — beshta joyni qidirib yurish
emas.

Nega path bilan boshlanadi:

  * subdomen wildcard DNS yozuvi VA wildcard TLS sertifikatini talab
    qiladi; Let's Encrypt wildcard uchun DNS-01 tekshiruvi kerak, u esa
    DNS provayder API'siga doimiy ulanishni talab qiladi. Sertifikat
    yangilanmay qolsa — 90 kundan keyin, kutilmagan paytda, JIMGINA
    buziladi;
  * path'da bitta nginx bloki, bitta sertifikat, bitta CORS origin;
  * eng muhimi: bu arxitekturada URL **tenant mexanizmi emas**. Tashkilot
    JWT ichidagi `organization_id` dan aniqlanadi va RLS bilan
    majburlanadi (docs/04 §1 — tashkilot mijozdan hech qachon
    olinmaydi). Ya'ni manzil brending va kirish nuqtasi, izolyatsiya
    emas — shuning uchun uni keyin o'zgartirish xavfsizlikka tegmaydi.

Nega `/t/` prefiksi bor, slug to'g'ridan-to'g'ri ildizda emas: ildizda
`/platform`, `/login` kabi yo'llar bor va ertaga `/pricing`, `/help`
qo'shiladi. Slug ildizda tursa, `login` nomli slug olgan mijoz butun
ilovani sindiradi — va siz abadiy "taqiqlangan nomlar" ro'yxatini
yuritishga majbur bo'lasiz. Bitta segment bu sinfdagi xatoni butunlay
yo'q qiladi.
"""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from django.conf import settings

from apps.core.deployment import is_standalone

__all__ = ["tenant_base_url", "tenant_login_url", "TENANT_PATH_PREFIX"]

TENANT_PATH_PREFIX = "t"


def tenant_base_url(slug: str) -> str:
    """
    Bog'chaning ildiz manzili, oxirida `/` siz.

    `PUBLIC_BASE_URL` — SPA qayerda turgani (masalan `https://kg-crm.uz`).
    `TENANT_URL_STYLE` — `path` yoki `subdomain`.
    """
    base = str(settings.PUBLIC_BASE_URL).rstrip("/")
    style = str(settings.TENANT_URL_STYLE)

    # Standalone nusxada bog'cha bitta va ilova ildizda yashaydi
    # (ADR-13): `/t/<slug>` prefiksi hech narsani ajratmaydi, faqat
    # mijozning o'z domenidagi havolasini uzaytirardi.
    if is_standalone():
        return base

    if style == "subdomain":
        parts = urlsplit(base)
        # `netloc` port bilan kelishi mumkin (`example.com:8000`) —
        # subdomen faqat host qismiga qo'shiladi.
        host, _, port = parts.netloc.partition(":")
        netloc = f"{slug}.{host}" + (f":{port}" if port else "")
        return urlunsplit((parts.scheme, netloc, parts.path.rstrip("/"), "", ""))

    return f"{base}/{TENANT_PATH_PREFIX}/{slug}"


def tenant_login_url(slug: str) -> str:
    """Bog'chaga beriladigan kirish havolasi."""
    return f"{tenant_base_url(slug)}/login"
