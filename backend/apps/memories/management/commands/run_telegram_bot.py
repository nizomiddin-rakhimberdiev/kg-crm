"""
`python manage.py run_telegram_bot` — botni MAHALLIY kompyuterda ishlatish (polling).

Telegram webhook'i faqat ochiq HTTPS manzilga yuboradi, `localhost`ga yetmaydi —
shuning uchun kompyuterda bot `/start` ga javob bermaydi. Bu buyruq Telegram'dan
yangilanishlarni o'zi so'raydi (getUpdates) va webhook bilan BIR XIL
`handle_update` ga beradi: mantiq ham, tenant izolyatsiyasi ham o'zgarmaydi.

Productionda ishlatilmaydi — u yerda webhook (`/api/v1/telegram/webhook`).
Token faqat `TELEGRAM_BOT_TOKEN` sozlamasidan o'qiladi va log'ga yozilmaydi.
"""

from __future__ import annotations

import logging
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.memories import services
from apps.memories.telegram import HttpTelegramClient, TelegramError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Telegram botni polling rejimida ishga tushiradi (faqat mahalliy ishlab chiqish)."

    def add_arguments(self, parser):  # type: ignore[no-untyped-def]
        parser.add_argument("--once", action="store_true", help="Bir marta so'rab chiqib ketadi.")

    def handle(self, *args, **options):  # type: ignore[no-untyped-def]
        if not settings.TELEGRAM_BOT_TOKEN:
            raise CommandError("TELEGRAM_BOT_TOKEN sozlanmagan (.env ga qo'shing).")
        if not settings.DEBUG:
            raise CommandError("Polling faqat DEBUG rejimida; productionda webhook ishlating.")
        client = HttpTelegramClient()
        try:
            client.delete_webhook()
        except TelegramError as exc:
            raise CommandError(f"Webhook o'chirilmadi: {exc}") from None
        self.stdout.write("Bot ishlayapti. To'xtatish: Ctrl+C")
        offset: int | None = None
        while True:
            try:
                updates = client.get_updates(offset)
            except TelegramError as exc:
                self.stderr.write(f"Telegram: {exc}; 5 soniyadan keyin qayta uriniladi")
                time.sleep(5)
                continue
            for update in updates:
                offset = int(update["update_id"]) + 1
                try:
                    services.handle_update(update)
                except Exception:  # noqa: BLE001 — bitta xato butun botni to'xtatmasin
                    logger.exception("Telegram update qayta ishlanmadi")
            if options["once"]:
                return
