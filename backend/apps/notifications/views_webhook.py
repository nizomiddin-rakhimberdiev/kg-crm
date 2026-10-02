"""
Telegram bot webhook'i (PLAN 3.7, ADR-23).

Bu **yagona** autentifikatsiyasiz yozuv nuqtasi, shuning uchun uning
har bir qoidasi ataylab:

* **Maxfiy yo'l.** URL ichidagi `TELEGRAM_WEBHOOK_SECRET` mos
  kelmasa — `404`, `403` emas: endpoint borligini tasdiqlash ham
  ma'lumot. Telegram bundan tashqari `X-Telegram-Bot-Api-Secret-Token`
  sarlavhasini yuboradi va u ham tekshiriladi.
* **Har doim `200`.** Telegram `2xx` bo'lmagan javobdan keyin
  update'ni QAYTA yuboradi — soatlab. Ya'ni bizning bir dona xatomiz
  cheksiz tsiklga aylanardi. Xato log'ga yoziladi, Telegramga esa
  "qabul qildim" deyiladi.
* **Faqat ikki buyruq.** `/start <kod>` va `/stop`. Qolgan hamma
  narsa jimgina tashlab yuboriladi: bot suhbat quradigan joy emas va
  ota-onaning yozgan matni bizda saqlanmaydi.
* **Hech qanday tenant konteksti yo'q.** Kod global unikal va
  qidiruv `platform_context()` orqali, nomi bilan so'raladi
  (`children/telegram.py`).
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.http import Http404
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.notifications.telegram_updates import handle_update

logger = logging.getLogger(__name__)

__all__ = ["TelegramWebhookView", "TelegramWebhookThrottle"]


class TelegramWebhookThrottle(AnonRateThrottle):
    """Telegram o'zi tezlikni ushlab turadi; bu — noto'g'ri yo'ldan kelganlar uchun."""

    scope = "telegram_webhook"


class TelegramWebhookView(APIView):
    """`POST /public/telegram/webhook/{secret}` — botdan kelgan update."""

    permission_classes = [AllowAny]
    authentication_classes: list[Any] = []
    throttle_classes = [TelegramWebhookThrottle]

    def post(self, request: Request, secret: str = "") -> Response:
        expected = str(getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "") or "")
        if not expected or secret != expected:
            # Sozlanmagan bo'lsa ham `404`: ochiq endpoint "men
            # borman, lekin sozlanmaganman" deb aytmasligi kerak.
            raise Http404

        header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if header is not None and header != expected:
            raise Http404

        try:
            # Mantiq `telegram_updates.handle_update` da — uzun so'rov
            # rejimi ham AYNI shu yo'ldan boradi (ikki nusxa bo'lsa
            # ular ajralib ketardi).
            handle_update(request.data if isinstance(request.data, dict) else {})
        except Exception:  # noqa: BLE001 — Telegram qayta yubormasligi uchun
            logger.exception("Telegram update'ini qayta ishlab bo'lmadi")

        return Response({"ok": True})
