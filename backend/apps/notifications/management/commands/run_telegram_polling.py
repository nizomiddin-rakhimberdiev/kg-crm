"""
Telegram botni UZUN SO'ROV rejimida ishga tushiradi (PLAN 3.7).

Ikki rejim bor va ikkalasi ham bir xil mantiqdan o'tadi
(`telegram_updates.handle_update`):

* **webhook** — Telegram bizga so'rov yuboradi. Ommaviy HTTPS manzili
  bo'lgan o'rnatma uchun eng arzon yo'l: hech narsa aylanib
  turmaydi.
* **uzun so'rov (bu buyruq)** — biz Telegramdan so'rab turamiz.
  Kerak bo'ladigan ikki holat:

  1. **lokal ishlab chiqish** — `localhost` ga Telegram so'rov
     yubora olmaydi, ya'ni webhook'ni sinab ko'rishning yo'li yo'q;
  2. **standalone o'rnatma** (ADR-13) — bog'chaning o'z serverida
     ommaviy HTTPS manzili va sertifikati bo'lmasligi mumkin.

**Telegram ikkalasini bir vaqtda qabul qilmaydi**: webhook
o'rnatilgan bo'lsa `getUpdates` `409 Conflict` beradi. Shuning uchun
buyruq boshida holatni tekshiradi va aniq aytadi — `--drop-webhook`
bilan uni olib tashlashga ruxsat beriladi, lekin JIMGINA emas: bu
prod o'rnatmaning botini o'chirib qo'yishi mumkin.

Ishlatish::

    # Lokal: botni ishga tushirish (Ctrl+C bilan to'xtatish)
    python manage.py run_telegram_polling

    # Bir marta so'rab, chiqish (cron yoki tekshiruv uchun)
    python manage.py run_telegram_polling --once

    # Webhook o'rnatilgan bo'lsa ham majburan polling'ga o'tish
    python manage.py run_telegram_polling --drop-webhook

`offset` xotirada: buyruq qayta ishga tushganda Telegram
yetkazilmagan update'larni qaytadan beradi (ular 24 soat saqlanadi),
va qayta ishlash XAVFSIZ — `/start` kodi bir martalik, `/stop` esa
idempotent.
"""

from __future__ import annotations

import signal
import time
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.notifications.telegram_updates import handle_update

#: Telegram so'rovni shuncha soniya ushlab turadi (long polling).
#: 30 — Telegram tavsiyasi: so'rovlar soni minimal, javob esa darhol.
LONG_POLL_SECONDS = 30

#: Tarmoq xatosidan keyin kutish. Telegram vaqtincha yiqilsa, buyruq
#: tsiklni yondirib yubormasligi kerak.
BACKOFF_SECONDS = 5


class Command(BaseCommand):
    help = "Telegram botni uzun so'rov rejimida ishga tushiradi."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--once", action="store_true", help="Bir marta so'rab chiqadi")
        parser.add_argument(
            "--drop-webhook",
            action="store_true",
            help="Webhook o'rnatilgan bo'lsa uni olib tashlaydi",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=LONG_POLL_SECONDS,
            help=f"Uzun so'rov soniyasi (sukut {LONG_POLL_SECONDS})",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        import requests

        token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        if not token:
            raise CommandError("TELEGRAM_BOT_TOKEN bo'sh — `.env` ni to'ldiring.")
        api = f"https://api.telegram.org/bot{token}"

        me = requests.get(f"{api}/getMe", timeout=15).json()
        if not me.get("ok"):
            raise CommandError(f"Token ishlamadi: {me}")
        username = (me.get("result") or {}).get("username")

        self._ensure_no_webhook(api, drop=bool(options.get("drop_webhook")))

        self.stdout.write(self.style.SUCCESS(f"@{username} — uzun so'rov rejimida"))
        self.stdout.write("To'xtatish: Ctrl+C")

        running = True

        def stop(*_: Any) -> None:
            nonlocal running
            running = False
            self.stdout.write("\nTo'xtatilmoqda…")

        signal.signal(signal.SIGINT, stop)
        signal.signal(signal.SIGTERM, stop)

        offset: int | None = None
        handled = 0
        timeout = int(options.get("timeout") or LONG_POLL_SECONDS)

        while running:
            params: dict[str, str | int] = {
                "timeout": timeout,
                "allowed_updates": '["message"]',
            }
            if offset is not None:
                params["offset"] = offset

            try:
                response = requests.get(
                    f"{api}/getUpdates",
                    params=params,
                    # Tarmoq kutish vaqti Telegramning kutishidan
                    # UZOQROQ: aks holda har bir normal uzun so'rov
                    # "timeout" bo'lib ko'rinardi.
                    timeout=timeout + 15,
                )
                payload = response.json()
            except Exception as exc:  # noqa: BLE001 — tsikl to'xtamasligi kerak
                self.stderr.write(f"Tarmoq xatosi: {exc}")
                time.sleep(BACKOFF_SECONDS)
                continue

            if not payload.get("ok"):
                self.stderr.write(f"Telegram: {payload}")
                time.sleep(BACKOFF_SECONDS)
                continue

            for update in payload.get("result") or []:
                offset = int(update["update_id"]) + 1
                try:
                    outcome = handle_update(update)
                except Exception as exc:  # noqa: BLE001 — bitta update tsiklni to'xtatmaydi
                    self.stderr.write(f"Update {update.get('update_id')}: {exc}")
                    continue
                handled += 1
                chat = ((update.get("message") or {}).get("chat") or {}).get("id")
                self.stdout.write(f"  {outcome}  chat={chat}")

            if options.get("once"):
                break

        self.stdout.write(self.style.SUCCESS(f"Tugadi. Qayta ishlangan update: {handled}"))

    # --- Yordamchi ---

    def _ensure_no_webhook(self, api: str, *, drop: bool) -> None:
        """
        Webhook va uzun so'rov BIR VAQTDA ishlamaydi.

        Buni oldin aytmasak, xato Telegramdan `409 Conflict` bo'lib
        keladi va u nima bo'layotganini tushuntirmaydi.
        """
        import requests

        info = requests.get(f"{api}/getWebhookInfo", timeout=15).json()
        url = ((info.get("result") or {}).get("url") or "").strip()
        if not url:
            return
        if not drop:
            raise CommandError(
                f"Webhook o'rnatilgan ({url}). Uzun so'rov u bilan birga ishlamaydi.\n"
                "Agar bu shu mashinaning webhook'i bo'lsa: --drop-webhook qo'shing.\n"
                "Agar bu PRODUCTION webhook'i bo'lsa — uni o'chirmang, "
                "aks holda bog'chalar bildirishnomasiz qoladi."
            )
        requests.post(f"{api}/deleteWebhook", timeout=15)
        self.stdout.write(f"Webhook olib tashlandi: {url}")
