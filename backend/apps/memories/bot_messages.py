"""
Bot xabarlari — uch tilda (ADR-16). Har biri `gettext_lazy`: ildiz ro'yxat
`test_i18n` tomonidan ru/en lug'atida borligi tekshiriladi.
Til chatga biriktirilgan (`TelegramChat.language`), so'rovdan emas.
"""

from __future__ import annotations

from django.utils import translation
from django.utils.translation import gettext_lazy

__all__ = ["say", "SUPPORTED_LANGUAGES"]

SUPPORTED_LANGUAGES = ("uz", "ru", "en")

MESSAGES = {
    "welcome_parent": gettext_lazy(
        "Salom, {name}! Ulandingiz. Farzandingiz rasmlari, bugungi menyu va "
        "kun tartibi shu yerga keladi."
    ),
    "welcome_group": gettext_lazy(
        "Bu guruh ulandi. Rasm yuboring — men bolalarni taniyman va "
        "rasmlarni ota-onalarga yuboraman."
    ),
    "welcome_staff": gettext_lazy("Ulandingiz. Kamera ogohlantirishlari shu yerga keladi."),
    "pair_invalid": gettext_lazy("Havola yaroqsiz yoki muddati o'tgan. Dasturdan yangisini oling."),
    "pair_wrong_chat": gettext_lazy("Bu havola boshqa turdagi chat uchun mo'ljallangan."),
    "not_linked": gettext_lazy("Bu chat ulanmagan. Bog'cha bergan havola orqali ulaning."),
    "help_parent": gettext_lazy(
        "Buyruqlar:\n/photos — bugungi rasmlar\n/photos week — oxirgi 7 kun\n"
        "/photos 2026-10-01 — shu kun rasmlari\n/menu — bugungi menyu va kun tartibi\n"
        "/language uz|ru|en — tilni almashtirish"
    ),
    "no_photos": gettext_lazy("Bu davr uchun rasm topilmadi."),
    "photos_found": gettext_lazy("{count} ta rasm topildi."),
    "photos_more": gettext_lazy("Yana rasmlar bor — sanani aniqroq ko'rsating."),
    "schedule_title": gettext_lazy("Bugungi kun tartibi"),
    "schedule_empty": gettext_lazy("Bugun uchun kun tartibi hali kiritilmagan."),
    "kind_menu": gettext_lazy("Menyu"),
    "kind_meal": gettext_lazy("Ovqat"),
    "kind_activity": gettext_lazy("Mashg'ulot"),
    "group_report": gettext_lazy(
        "Rasm qayta ishlandi: {matched} ta bola aniqlandi, {unknown} ta yuz noma'lum."
    ),
    "group_no_faces": gettext_lazy("Rasmda yuz topilmadi."),
    "group_engine_down": gettext_lazy("Yuz tanish xizmati hozir ishlamayapti. Rasm saqlandi."),
    "photo_caption": gettext_lazy("{child} — {time}"),
    "language_changed": gettext_lazy("Til o'zgartirildi."),
    "unknown_command": gettext_lazy("Tushunmadim. /help ni yuboring."),
    "alert_title": gettext_lazy("Radix AI ogohlantirishi"),
    "alert_line": gettext_lazy("{kind} ({severity}): {note}"),
}


def say(language: str, key: str, **kwargs: object) -> str:
    lang = language if language in SUPPORTED_LANGUAGES else "uz"
    with translation.override(lang):
        return str(MESSAGES[key]).format(**kwargs)
