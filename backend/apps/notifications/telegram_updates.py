"""
Telegram update'ini qayta ishlash — YAGONA yo'l (PLAN 3.7).

Bot bizga ikki yo'l bilan yetib kelishi mumkin:

* **webhook** — Telegram bizga so'rov yuboradi (`views_webhook.py`);
* **uzun so'rov** — biz Telegramdan so'raymiz
  (`management/commands/run_telegram_polling.py`).

Mantiq esa BITTA. Ikki nusxa bo'lsa, ular ertami-kechmi ajralib
ketadi: biri `/stop` ni biladi, ikkinchisi bilmaydi — va qaysi
rejimda ishlab turganiga qarab bot boshqacha javob beradi.

Qaysi rejim kerak:

* webhook — ommaviy HTTPS manzili bor o'rnatma (hosted SaaS);
* uzun so'rov — lokal ishlab chiqish va ommaviy manzili yo'q
  standalone o'rnatma. Telegram ikkalasini BIR VAQTDA qabul
  qilmaydi: webhook o'rnatilgan bo'lsa `getUpdates` `409` beradi.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["handle_update", "reply", "START_HELP", "LINKED", "UNKNOWN_CODE", "STOPPED"]

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


def reply(chat_id: str, text: str, markup: dict[str, Any] | None = None) -> None:
    """
    Botning javobi. Yuborilmasa ham bog'lanish SAQLANADI.

    Javob — xushmuomalalik, bog'lanish esa ish. Ikkinchisi birinchisiga
    bog'liq bo'lmasligi kerak.
    """
    from apps.notifications.providers import TelegramProvider

    try:
        TelegramProvider().send(address=chat_id, body=text, reply_markup=markup)
    except Exception:  # noqa: BLE001 — javob bermaslik bog'lanishni buzmaydi
        logger.exception("Telegram javobi yuborilmadi")


def _handle_staff(chat_id: str, text: str, caption: str, photos: list[Any]) -> str | None:
    """
    Xodimning xabari: `/start s_…` yoki chiqim (rasm yoki summa bilan
    boshlanadigan matn). `None` — bu xodim xabari emas, ota-ona botiga.
    """
    from apps.accounts import telegram as staff

    if not chat_id:
        return None
    if text.startswith(f"/start {staff.PREFIX}"):
        user = staff.link_staff(code=text[len("/start") :].strip(), chat_id=chat_id)
        if user is None:
            reply(chat_id, UNKNOWN_CODE["uz"])
            return "unknown_code"
        reply(
            chat_id,
            f"Salom, {user.full_name}! Chiqim uchun summani (va chek rasmini) yuboring: "
            "masalan, 150 000 kartoshka.",
        )
        return "staff_linked"

    body = caption if photos else text
    if not photos and not re.match(r"^\d", body):
        return None
    found = staff.staff_for_chat(chat_id)
    if found is None:
        return None
    organization_id, user = found
    from apps.core.tenancy import organization_context
    from apps.expenses import telegram as expenses

    with organization_context(organization_id):
        outcome, answer, markup = expenses.start_draft(
            user=user,
            text=body,
            photo_file_id=str((photos[-1] or {}).get("file_id") or "") if photos else "",
        )
    reply(chat_id, answer, markup)
    return outcome


def _handle_callback(callback: dict[str, Any]) -> str:
    """Inline tugma — hozircha faqat chiqim toifasi (`x:…`)."""
    from apps.accounts import telegram as staff

    chat_id = str((((callback.get("message") or {}).get("chat") or {}).get("id")) or "").strip()
    data = str(callback.get("data") or "")
    if not chat_id or not data.startswith("x:"):
        return "ignored"
    found = staff.staff_for_chat(chat_id)
    if found is None:
        return "ignored"
    organization_id, user = found
    from apps.core.tenancy import organization_context
    from apps.expenses import telegram as expenses

    with organization_context(organization_id):
        outcome, answer = expenses.choose_category(user=user, data=data)
    if answer:
        reply(chat_id, answer)
    return outcome


def handle_update(update: dict[str, Any]) -> str:
    """
    Bitta update. Javob — nima bo'lgani (log va test uchun).

    Buyruqlar: `/start <kod>`, `/stop`, telefon raqamini ulashish
    (PLAN 6.3) va ota-ona menyusining to'rt tugmasi (PLAN 6.2,
    `apps/parent_bot/bot.py`). Ulanmagan suhbatning yozgan matni
    jimgina tashlab yuboriladi: bot suhbat quradigan joy emas va
    ota-onaning yozgan matni bizda saqlanmaydi.
    """
    callback = update.get("callback_query")
    if isinstance(callback, dict):
        return _handle_callback(callback)

    message = update.get("message") or update.get("edited_message") or {}
    chat_id = str(((message.get("chat") or {}).get("id")) or "").strip()
    text = str(message.get("text") or "").strip()
    contact = message.get("contact") if isinstance(message.get("contact"), dict) else None
    sender = message.get("from") or {}
    language_hint = str(sender.get("language_code") or "")
    raw_photos = message.get("photo")
    photos: list[Any] = raw_photos if isinstance(raw_photos, list) else []

    # Xodim (Bosqich 13.3c): ulanish havolasi va chiqim — ota-ona botidan oldin.
    staff_outcome = _handle_staff(chat_id, text, str(message.get("caption") or ""), photos)
    if staff_outcome is not None:
        return staff_outcome

    if not chat_id or not (text or contact):
        return "ignored"

    from apps.children import telegram as links
    from apps.parent_bot import bot

    if contact is not None:
        answer = bot.link_contact(
            chat_id=chat_id,
            contact=contact,
            sender_id=sender.get("id"),
            fallback_language=language_hint,
        )
        reply(chat_id, answer.body, answer.markup)
        return answer.outcome

    if text.startswith("/start"):
        code = text[len("/start") :].strip()
        if not code:
            answer = bot.menu(chat_id, language_hint)
            reply(chat_id, answer.body, answer.markup)
            return answer.outcome
        guardian = links.link_from_start(code=code, chat_id=chat_id)
        if guardian is None:
            reply(chat_id, UNKNOWN_CODE["uz"])
            return "unknown_code"
        language = (guardian.language or "uz") if guardian.language in LINKED else "uz"
        reply(
            chat_id,
            LINKED[language].format(name=guardian.first_name or ""),
            bot.menu(chat_id).markup,
        )
        logger.info("Telegram bog'landi: vasiy=%s", guardian.id)
        return "linked"

    if text.startswith("/stop"):
        from apps.parent_bot.index import chat_digest, forget_chat, organizations_for
        from apps.parent_bot.models import ContactKind

        organization_ids = organizations_for(ContactKind.CHAT, chat_digest(chat_id))
        removed = links.unlink_chat(chat_id)
        forget_chat(chat_id, organization_ids=organization_ids)
        reply(chat_id, STOPPED["uz"], {"remove_keyboard": True})
        logger.info("Telegram uzildi: %s qator", removed)
        return "stopped"

    response = bot.answer(chat_id, text)
    if response is None:
        return "ignored"
    reply(chat_id, response.body, response.markup)
    return response.outcome
