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

logger = logging.getLogger(__name__)

__all__ = ["TelegramWebhookView", "TelegramWebhookThrottle"]

START_HELP = {
    "uz": (
        "Assalomu alaykum! Bu bog'chaning xabar boti.\n\n"
        "Ulanish uchun bog'chadan olgan havolani bosing — unda sizga "
        "tegishli kod bo'ladi."
    ),
    "ru": (
        "Здравствуйте! Это бот уведомлений детского сада.\n\n"
        "Чтобы подключиться, откройте ссылку, которую вам дали в садике — "
        "в ней ваш персональный код."
    ),
}

LINKED = {
    "uz": (
        "Rahmat, {name}! Endi bog'chadan xabarlar shu yerga keladi:\n"
        "to'lov kvitansiyasi, qarzdorlik eslatmasi va muhim xabarnomalar.\n\n"
        "To'xtatish uchun /stop yuboring."
    ),
    "ru": (
        "Спасибо, {name}! Теперь уведомления садика будут приходить сюда:\n"
        "квитанции об оплате, напоминания о задолженности и важные сообщения.\n\n"
        "Чтобы отключить, отправьте /stop."
    ),
}

UNKNOWN_CODE = {
    "uz": ("Havola eskirgan yoki allaqachon ishlatilgan.\n\nBog'chadan yangi havola so'rang."),
    "ru": ("Ссылка устарела или уже использована.\n\nПопросите в садике новую ссылку."),
}

STOPPED = {
    "uz": "Xabarlar to'xtatildi. Qayta ulanish uchun bog'chadan havola so'rang.",
    "ru": "Уведомления отключены. Для повторного подключения попросите ссылку в садике.",
}


class TelegramWebhookThrottle(AnonRateThrottle):
    """Telegram o'zi tezlikni ushlab turadi; bu — noto'g'ri yo'ldan kelganlar uchun."""

    scope = "telegram_webhook"


def _reply(chat_id: str, text: str) -> None:
    """
    Botning javobi. Yuborilmasa ham bog'lanish SAQLANADI.

    Javob — xushmuomalalik, bog'lanish esa ish. Ikkinchisi birinchisiga
    bog'liq bo'lmasligi kerak.
    """
    from apps.notifications.providers import TelegramProvider

    try:
        TelegramProvider().send(address=chat_id, body=text)
    except Exception:  # noqa: BLE001 — javob bermaslik bog'lanishni buzmaydi
        logger.exception("Telegram javobi yuborilmadi")


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
            self._handle(request.data if isinstance(request.data, dict) else {})
        except Exception:  # noqa: BLE001 — Telegram qayta yubormasligi uchun
            logger.exception("Telegram update'ini qayta ishlab bo'lmadi")

        return Response({"ok": True})

    # --- Ichki mantiq ---

    def _handle(self, update: dict[str, Any]) -> None:
        message = update.get("message") or update.get("edited_message") or {}
        chat_id = str(((message.get("chat") or {}).get("id")) or "").strip()
        text = str(message.get("text") or "").strip()
        if not chat_id or not text:
            return

        from apps.children import telegram as links

        if text.startswith("/start"):
            code = text[len("/start") :].strip()
            if not code:
                _reply(chat_id, START_HELP["uz"])
                return
            guardian = links.link_from_start(code=code, chat_id=chat_id)
            if guardian is None:
                _reply(chat_id, UNKNOWN_CODE["uz"])
                return
            language = (guardian.language or "uz") if guardian.language in LINKED else "uz"
            _reply(chat_id, LINKED[language].format(name=guardian.first_name or ""))
            logger.info("Telegram bog'landi: vasiy=%s", guardian.id)
            return

        if text.startswith("/stop"):
            removed = links.unlink_chat(chat_id)
            _reply(chat_id, STOPPED["uz"])
            logger.info("Telegram uzildi: %s qator", removed)
            return

        # Qolgani — javobsiz. Bot suhbat quradigan joy emas.
