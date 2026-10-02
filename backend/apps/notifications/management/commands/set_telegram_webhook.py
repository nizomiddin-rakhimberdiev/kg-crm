"""
Telegram botning webhook'ini ro'yxatdan o'tkazadi (PLAN 3.7).

Deployda bir marta bajariladigan ish. Qo'lda `curl` bilan ham
bo'lardi, lekin o'shanda URL va maxfiy qism qo'lda yozilardi — va
aynan shu joyda adashish "bot ishlamaydi, sababi ko'rinmaydi" degan
holatga olib keladi. Bu buyruq URL'ni `.env` dagi qiymatlardan
yig'adi, ya'ni ilova kutayotgan manzil bilan BIR XIL bo'ladi.

Ishlatish::

    # Avval KO'RISH — Telegramga hech narsa yuborilmaydi
    python manage.py set_telegram_webhook --base-url https://radix-crm.uz --dry-run

    # To'g'ri bo'lsa, o'rnatish
    python manage.py set_telegram_webhook --base-url https://radix-crm.uz

    # Holatni tekshirish
    python manage.py set_telegram_webhook --info

`--delete` webhook'ni olib tashlaydi (masalan lokal ishlab chiqishga
o'tganda).
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Telegram bot webhook'ini o'rnatadi yoki holatini ko'rsatadi."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--base-url", help="Masalan https://radix-crm.uz")
        parser.add_argument("--dry-run", action="store_true", help="Faqat URL'ni ko'rsatadi")
        parser.add_argument("--info", action="store_true", help="Amaldagi holatni so'raydi")
        parser.add_argument("--delete", action="store_true", help="Webhook'ni olib tashlaydi")

    def handle(self, *args: Any, **options: Any) -> None:
        import requests

        token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        secret = getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "")
        if not token:
            raise CommandError("TELEGRAM_BOT_TOKEN bo'sh — `.env` ni to'ldiring.")

        api = f"https://api.telegram.org/bot{token}"

        if options.get("info"):
            response = requests.get(f"{api}/getWebhookInfo", timeout=15)
            self.stdout.write(response.text)
            return

        if options.get("delete"):
            response = requests.post(f"{api}/deleteWebhook", timeout=15)
            self.stdout.write(response.text)
            return

        if not secret:
            raise CommandError("TELEGRAM_WEBHOOK_SECRET bo'sh — tasodifiy 32+ belgi qo'ying.")
        base = (options.get("base_url") or "").rstrip("/")
        if not base.startswith("https://"):
            # Telegram faqat HTTPS qabul qiladi. Buni oldin aytmasak,
            # xato Telegram tomonidan keladi va tushunarsiz bo'ladi.
            raise CommandError("--base-url `https://` bilan boshlanishi kerak.")

        url = f"{base}/api/v1/public/telegram/webhook/{secret}"
        if options.get("dry_run"):
            self.stdout.write(f"Webhook URL: {url}")
            self.stdout.write("DRY-RUN — Telegramga hech narsa yuborilmadi.")
            return

        response = requests.post(
            f"{api}/setWebhook",
            json={
                "url": url,
                # Telegram har so'rovda shu sarlavhani qo'shadi —
                # ikkinchi qatlam: maxfiy yo'l loglarda ko'rinib
                # qolsa ham, sarlavha bilan tekshiruv qoladi.
                "secret_token": secret,
                "allowed_updates": ["message"],
                "drop_pending_updates": True,
            },
            timeout=20,
        )
        self.stdout.write(response.text)
        if response.status_code >= 400 or not response.json().get("ok"):
            raise CommandError("Webhook o'rnatilmadi — javobga qarang.")
        self.stdout.write(self.style.SUCCESS("Webhook o'rnatildi."))
