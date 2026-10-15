"""
What the parent bot says (PLAN 6.2) — uz / ru / en.

Plain text, no `parse_mode`: a `<` or `_` in a child's name would break
an HTML or Markdown message (the provider's note). Button labels are
matched back exactly, in every language, because a parent may switch
Telegram's language without telling us.
"""

from __future__ import annotations

from typing import Final

LANGUAGES: Final = ("uz", "ru", "en")

# --- Buttons (reply keyboard) ---

BALANCE: Final = {"uz": "💰 Balans", "ru": "💰 Баланс", "en": "💰 Balance"}
INVOICES: Final = {"uz": "🧾 Hisob-fakturalar", "ru": "🧾 Счета", "en": "🧾 Invoices"}
PAY: Final = {"uz": "💳 Toʻlash", "ru": "💳 Оплатить", "en": "💳 Pay"}
RECEIPTS: Final = {"uz": "📄 Kvitansiyalar", "ru": "📄 Квитанции", "en": "📄 Receipts"}
SHARE_PHONE: Final = {
    "uz": "📱 Telefon raqamni yuborish",
    "ru": "📱 Отправить номер телефона",
    "en": "📱 Share my phone number",
}

# --- Replies ---

MENU: Final = {
    "uz": "Quyidagi tugmalardan birini tanlang.",
    "ru": "Выберите одну из кнопок ниже.",
    "en": "Choose one of the buttons below.",
}

START_UNLINKED: Final = {
    "uz": (
        "Assalomu alaykum! Bu bogʻchaning boti: balans, hisob-fakturalar, "
        "onlayn toʻlov va kvitansiyalar.\n\n"
        "Ulanish uchun bogʻchadan olgan havolani bosing yoki pastdagi tugma "
        "bilan telefon raqamingizni yuboring — u bogʻchada yozilgan raqam "
        "bilan bir xil boʻlishi kerak."
    ),
    "ru": (
        "Здравствуйте! Это бот детского сада: баланс, счета, онлайн-оплата "
        "и квитанции.\n\n"
        "Чтобы подключиться, откройте ссылку из садика или отправьте свой "
        "номер кнопкой ниже — он должен совпадать с номером, записанным в садике."
    ),
    "en": (
        "Hello! This is the kindergarten's bot: balance, invoices, online "
        "payment and receipts.\n\n"
        "To connect, open the link from the kindergarten or share your phone "
        "number with the button below — it must match the number the "
        "kindergarten has on file."
    ),
}

PHONE_LINKED: Final = {
    "uz": "Rahmat, {name}! Siz ulandingiz. Bogʻcha xabarlari endi shu yerga keladi.",
    "ru": "Спасибо, {name}! Вы подключены. Уведомления садика теперь будут приходить сюда.",
    "en": "Thank you, {name}! You are connected. The kindergarten's messages will come here.",
}

PHONE_UNKNOWN: Final = {
    "uz": (
        "Bu raqam hech bir bogʻchada topilmadi.\n\n"
        "Bogʻchada qaysi raqamingiz yozilganini soʻrang yoki ulanish havolasini oling."
    ),
    "ru": (
        "Этот номер не найден ни в одном садике.\n\n"
        "Уточните в садике, какой номер у них записан, или попросите ссылку для подключения."
    ),
    "en": (
        "This number is not on file at any kindergarten.\n\n"
        "Ask the kindergarten which number they have, or ask for a connection link."
    ),
}

NOT_OWN_PHONE: Final = {
    "uz": "Faqat oʻzingizning raqamingizni tugma orqali yuboring.",
    "ru": "Отправьте, пожалуйста, свой собственный номер кнопкой.",
    "en": "Please share your own number using the button.",
}

NO_CHILDREN: Final = {
    "uz": "Sizga bogʻlangan bola topilmadi. Bogʻcha bilan bogʻlaning.",
    "ru": "Не найдено детей, привязанных к вам. Свяжитесь с садиком.",
    "en": "No children are linked to you. Please contact the kindergarten.",
}

DEBT: Final = {"uz": "Qarz: {money}", "ru": "Долг: {money}", "en": "Owed: {money}"}
ADVANCE: Final = {"uz": "Avans: {money}", "ru": "Аванс: {money}", "en": "Prepaid: {money}"}
NO_DEBT: Final = {"uz": "Qarz yoʻq ✅", "ru": "Долга нет ✅", "en": "Nothing owed ✅"}
OVERDUE: Final = {
    "uz": "Muddati oʻtgan: {money} ({date} dan)",
    "ru": "Просрочено: {money} (с {date})",
    "en": "Overdue: {money} (since {date})",
}
NEXT_DUE: Final = {
    "uz": "Toʻlov muddati: {date}",
    "ru": "Срок оплаты: {date}",
    "en": "Due date: {date}",
}

NO_INVOICES: Final = {
    "uz": "Hisob-faktura hali yoʻq.",
    "ru": "Счетов пока нет.",
    "en": "No invoices yet.",
}
INVOICE_STATUS: Final = {
    "draft": {"uz": "qoralama", "ru": "черновик", "en": "draft"},
    "issued": {"uz": "toʻlanmagan", "ru": "не оплачен", "en": "unpaid"},
    "partially_paid": {"uz": "qisman toʻlangan", "ru": "оплачен частично", "en": "part-paid"},
    "paid": {"uz": "toʻlangan ✅", "ru": "оплачен ✅", "en": "paid ✅"},
    "overdue": {"uz": "muddati oʻtgan ⚠️", "ru": "просрочен ⚠️", "en": "overdue ⚠️"},
    "cancelled": {"uz": "bekor qilingan", "ru": "отменён", "en": "cancelled"},
}

PAY_INTRO: Final = {
    "uz": "Toʻlov uchun tugmani bosing — Payme yoki Click sahifasi ochiladi.",
    "ru": "Нажмите кнопку для оплаты — откроется страница Payme или Click.",
    "en": "Tap the button to pay — the Payme or Click page will open.",
}
PAY_BUTTON: Final = {
    "uz": "{child} — {money}",
    "ru": "{child} — {money}",
    "en": "{child} — {money}",
}
NOTHING_TO_PAY: Final = {
    "uz": "Toʻlanadigan hisob-faktura yoʻq ✅",
    "ru": "Нет счетов к оплате ✅",
    "en": "Nothing to pay ✅",
}
PAY_OFFLINE: Final = {
    "uz": "Bu bogʻchada onlayn toʻlov ulanmagan — toʻlovni bogʻcha kassasida qiling.",
    "ru": "В этом садике онлайн-оплата не подключена — оплатите в кассе садика.",
    "en": "Online payment is not set up at this kindergarten — please pay at its office.",
}

NO_RECEIPTS: Final = {
    "uz": "Toʻlovlar hali yoʻq.",
    "ru": "Оплат пока нет.",
    "en": "No payments yet.",
}
REVERSED: Final = {"uz": "qaytarilgan", "ru": "возвращён", "en": "reversed"}

METHODS: Final = {
    "cash": {"uz": "naqd", "ru": "наличные", "en": "cash"},
    "terminal": {"uz": "terminal", "ru": "терминал", "en": "card terminal"},
    "bank_transfer": {"uz": "oʻtkazma", "ru": "перевод", "en": "bank transfer"},
    "online": {"uz": "Payme / Click", "ru": "Payme / Click", "en": "Payme / Click"},
    "click": {"uz": "Click", "ru": "Click", "en": "Click"},
    "payme": {"uz": "Payme", "ru": "Payme", "en": "Payme"},
    "payroll": {"uz": "oylikdan ushlash", "ru": "удержание из зарплаты", "en": "salary deduction"},
}

CURRENCY: Final = {"uz": "soʻm", "ru": "сум", "en": "UZS"}


def pick(table: dict[str, str], language: str) -> str:
    return table.get(language) or table["uz"]


def menu_keyboard(language: str) -> dict:
    """The four buttons, always visible under the message field."""
    return {
        "keyboard": [
            [{"text": pick(BALANCE, language)}, {"text": pick(INVOICES, language)}],
            [{"text": pick(PAY, language)}, {"text": pick(RECEIPTS, language)}],
        ],
        "resize_keyboard": True,
        "is_persistent": True,
    }


def share_phone_keyboard(language: str) -> dict:
    return {
        "keyboard": [[{"text": pick(SHARE_PHONE, language), "request_contact": True}]],
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }


def action_for(text: str) -> str | None:
    """Which button was pressed — in any language."""
    cleaned = (text or "").strip()
    for action, table in (
        ("balance", BALANCE),
        ("invoices", INVOICES),
        ("pay", PAY),
        ("receipts", RECEIPTS),
    ):
        if cleaned in table.values():
            return action
    return None
