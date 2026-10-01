"""
Platforma ogohlantirishlari — Telegram (PLAN 3.6).

Nega kerak: saytdan kelgan ariza hozir faqat bazada turadi va uni
ko'rish uchun kimdir konsolga kirishi kerak. Amalda ariza kechqurun
keladi, ertasi kuni ko'riladi va o'sha vaqtda mijoz boshqa tizimni
tanlab bo'lgan bo'ladi. Birinchi javob tezligi — sotuvda eng kuchli
omil.

**Ariza SAQLANISHI birinchi.** Telegram ishlamasa ham lead yo'qolmaydi:
bu yerdagi har qanday xato ushlanadi va log'ga yoziladi. Bildirishnoma
qulaylik, ma'lumot esa biznes.

**Sozlanmagan bo'lsa jimgina o'tkazib yuboriladi** — ishlab chiqish
muhitida va standalone o'rnatmada Telegram yo'q va u yerda xato
chiqarishning ma'nosi yo'q.
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)

__all__ = ["telegram_configured", "send_telegram", "notify_new_lead"]

TIMEOUT = 10


def telegram_configured() -> bool:
    return bool(getattr(settings, "TELEGRAM_BOT_TOKEN", "")) and bool(
        getattr(settings, "TELEGRAM_LEADS_CHAT_ID", "")
    )


def send_telegram(text: str) -> bool:
    """Xabarni yuboradi; sozlanmagan yoki xato bo'lsa `False`."""
    if not telegram_configured():
        logger.debug("Telegram sozlanmagan — ogohlantirish o'tkazib yuborildi")
        return False

    try:
        import requests

        response = requests.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": settings.TELEGRAM_LEADS_CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=TIMEOUT,
        )
        if response.status_code >= 400:
            logger.warning("Telegram %s: %s", response.status_code, response.text[:300])
            return False
        return True
    except Exception:  # noqa: BLE001 — ogohlantirish hech qachon oqimni yiqitmaydi
        logger.exception("Telegram ogohlantirishi yuborilmadi")
        return False


def _escape(value: Any) -> str:
    """HTML parse_mode uchun: mijoz nomidagi `<` xabarni buzmasin."""
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").strip()


def notify_new_lead(lead: Any) -> bool:
    """
    Yangi ariza haqida sotuvga xabar (PLAN 3.6).

    Xabarda **darhol harakat qilish uchun kerak bo'lgan hamma narsa**
    bor: kim, qaysi bog'cha, nechta bola, shahar va telefon. Sotuvchi
    konsolni ochmasdan qo'ng'iroq qila olishi kerak — konsolga kirish
    bu bir necha daqiqa va amalda shu daqiqalar yo'qoladi.
    """
    lines = [
        "🌱 <b>Yangi ariza — Radix CRM</b>",
        "",
        f"👤 {_escape(lead.name)}",
        f"🏫 {_escape(lead.kindergarten_name)}",
        f"👶 {lead.children_count} ta bola · 📍 {_escape(lead.city)}",
        f"📞 {_escape(lead.phone)}",
        f"🗣 {_escape(lead.language)} · {_escape(lead.source)}",
    ]
    if lead.message:
        lines += ["", f"💬 {_escape(lead.message)[:400]}"]
    return send_telegram("\n".join(lines))
