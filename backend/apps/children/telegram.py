"""
Vasiyni Telegram boti bilan bog'lash (PLAN 3.7, ADR-23).

Nega bu `children` app'ida: bog'lanish **vasiy qatorida** yashaydi, va
boshqa modul `Guardian` modelini import qilmaydi (CLAUDE.md, invariant
1). Bildirishnomalar moduli shu funksiyalarni chaqiradi.

Oqim:

1. Mudira bola kartasida "Telegram havolasi" ni oladi —
   `t.me/<bot>?start=<kod>`.
2. Havolani ota-onaga yuboradi (WhatsApp, SMS, qog'ozda QR — farqi
   yo'q).
3. Ota-ona botni ishga tushiradi; bot `/start <kod>` ni oladi va
   suhbatni vasiyga bog'laydi.

**Kod bir martalik.** Bog'langach u o'chiriladi. Havola oilaviy
guruhga tashlanishi mumkin, matn ichida esa bolaning ismi va qarz
summasi ketadi — ya'ni havola qolib qolsa, begona odam shu oilaning
moliyaviy xabarlarini olib turardi. Yangi havola bir bosishda
yaratiladi.

**`chat_id` ni biz bera olmaymiz.** U faqat ota-onaning o'zi botni
ishga tushirganda paydo bo'ladi, ya'ni bog'lanishning o'zi rozilik
dalili. Shu sababli "ulanmagan" holati xato emas — oddiy holat, va
ekran uni shunday ko'rsatishi kerak.
"""

from __future__ import annotations

import base64
import secrets
import uuid
from typing import Any

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.children.models import Guardian
from apps.core.tenancy import organization_context, platform_context

__all__ = [
    "RANDOM_BYTES",
    "bot_username",
    "build_code",
    "organization_from_code",
    "ensure_code",
    "link_url",
    "new_code",
    "link_from_start",
    "unlink_chat",
    "is_linked",
    "guardians_for_chat",
    "children_of",
    "link_by_phone",
]

#: Kodning tasodifiy qismi. 8 bayt = 64 bit: taxmin qilib bo'lmaydi.
RANDOM_BYTES = 8


def build_code(organization_id: Any) -> str:
    """
    `base64url(tashkilot UUID baytlari + 8 tasodifiy bayt)` — 32 belgi.

    **Nega tashkilot kodning ICHIDA.** Bot `/start` ni hech qanday
    tashkilot konteksti bo'lmagan holda oladi, ya'ni vasiyni topish
    uchun tenant chegarasidan chiqish kerak bo'lardi. RLS esa buni
    ataylab bermaydi: operatsion jadvallar uchun platforma rejimida
    ham chiqish yo'li YO'Q (ADR-10) — va shu torlik himoyaning o'zi.
    Kodga tashkilotni joylash shu savolni butunlay yo'q qiladi:
    webhook kodni ochadi, TO'G'RI tashkilot kontekstini o'rnatadi va
    qidiruvni shu chegara ichida bajaradi. Soxta kod faqat o'zi
    ko'rsatgan tashkilotga tegishi mumkin — va u yerda tasodifiy
    qismdan o'tolmaydi.

    Telegram `start` yuki 64 belgigacha va faqat `A-Za-z0-9_-` ni
    qabul qiladi; `base64url` aynan shu alifboda.
    """
    raw = uuid.UUID(str(organization_id)).bytes + secrets.token_bytes(RANDOM_BYTES)
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def organization_from_code(code: str) -> str | None:
    """Kodning birinchi 16 baytidan tashkilot; buzuq bo'lsa `None`."""
    cleaned = (code or "").strip()
    if not cleaned:
        return None
    padding = "=" * (-len(cleaned) % 4)
    try:
        raw = base64.urlsafe_b64decode(cleaned + padding)
    except (ValueError, TypeError):
        return None
    if len(raw) < 16:
        return None
    try:
        return str(uuid.UUID(bytes=raw[:16]))
    except ValueError:
        return None


def bot_username() -> str:
    return str(getattr(settings, "TELEGRAM_BOT_USERNAME", "") or "").lstrip("@")


def is_linked(guardian: Any) -> bool:
    return bool((getattr(guardian, "telegram_chat_id", "") or "").strip())


def ensure_code(guardian: Guardian) -> str:
    """Vasiyning amaldagi ulash kodini qaytaradi, yo'q bo'lsa yaratadi."""
    if guardian.telegram_code:
        return str(guardian.telegram_code)
    return new_code(guardian)


def new_code(guardian: Guardian) -> str:
    """Kodni ALMASHTIRADI — eski havola darhol ishlamay qoladi."""
    guardian.telegram_code = build_code(guardian.organization_id)
    guardian.save(update_fields=["telegram_code", "updated_at"])
    return str(guardian.telegram_code)


def link_url(guardian: Guardian, *, rotate: bool = False) -> str:
    """
    Ota-onaga yuboriladigan havola.

    Bot nomi sozlanmagan bo'lsa bo'sh satr qaytaradi: ekran o'shanda
    havola emas, "bot sozlanmagan" degan izoh ko'rsatadi — ishlamaydigan
    havolani berib qo'yish eng yomon variant.
    """
    username = bot_username()
    if not username:
        return ""
    code = new_code(guardian) if rotate else ensure_code(guardian)
    return f"https://t.me/{username}?start={code}"


def link_from_start(*, code: str, chat_id: str) -> Guardian | None:
    """
    `/start <kod>` ni qayta ishlaydi: suhbatni vasiyga bog'laydi.

    Tashkilot KODDAN olinadi (`build_code` izohiga qarang) va qidiruv
    shu tashkilot konteksti ichida bajariladi — ya'ni bu yo'l tenant
    chegarasidan umuman chiqmaydi.

    Takroriy `/start` xavfsiz: kod bog'langach o'chiriladi, ya'ni
    ikkinchi marta hech narsa topilmaydi va bot "havola eskirgan" deb
    javob beradi.
    """
    cleaned = (code or "").strip()
    chat = (chat_id or "").strip()
    organization_id = organization_from_code(cleaned)
    if not cleaned or not chat or organization_id is None:
        return None

    with organization_context(organization_id):
        guardian = Guardian.objects.filter(telegram_code=cleaned, is_active=True).first()
        if guardian is None:
            return None

        # Bir xil suhbat shu tashkilotda boshqa vasiyga bog'langan
        # bo'lishi mumkin (bitta telefon, ikki yozuv). Unikal cheklov
        # buni rad etardi — shuning uchun eskisini bo'shatamiz:
        # ota-onaning oxirgi harakati ustun.
        Guardian.objects.filter(telegram_chat_id=chat).exclude(pk=guardian.pk).update(
            telegram_chat_id="", telegram_linked_at=None
        )

        guardian.telegram_chat_id = chat
        guardian.telegram_linked_at = timezone.now()
        guardian.telegram_code = ""
        guardian.save(
            update_fields=[
                "telegram_chat_id",
                "telegram_linked_at",
                "telegram_code",
                "updated_at",
            ]
        )
        return guardian


def unlink_chat(chat_id: str) -> int:
    """
    `/stop` — ota-ona xabarlardan voz kechdi.

    **Hamma tashkilot bo'yicha** o'chiriladi: odam shu suhbatda
    "to'xtat" dedi va uning nazarida bu bitta bot. Bir bog'chadan
    xabar kelib turishi va'dani buzish bo'lardi.

    Shu sababli bu yerda tashkilotlar bo'ylab AYLANILADI, lekin har
    biri O'Z konteksti ichida: platforma rejimi operatsion
    jadvallarni baribir ochmaydi (ADR-10) va uni ochish — eng
    noto'g'ri yechim bo'lardi. `/stop` kamdan-kam hodisa, narxi esa
    bir nechta kichik `UPDATE`.
    """
    from apps.organizations.models import Organization

    chat = (chat_id or "").strip()
    if not chat:
        return 0

    with platform_context():
        organization_ids = list(Organization.objects.values_list("id", flat=True))

    cleared = 0
    for organization_id in organization_ids:
        with organization_context(organization_id):
            cleared += int(
                Guardian.objects.filter(telegram_chat_id=chat).update(
                    telegram_chat_id="", telegram_linked_at=None
                )
            )
    return cleared


# --- Parent bot (PLAN 6.2 / 6.3) ---
#
# Everything below runs INSIDE one organization's context; the bot finds
# which organizations to visit through the contact index (ADR-27).


def guardians_for_chat(chat_id: str) -> list[Guardian]:
    """Active guardians of the current organization linked to this chat."""
    chat = (chat_id or "").strip()
    if not chat:
        return []
    return list(Guardian.objects.filter(telegram_chat_id=chat, is_active=True))


def children_of(guardian: Guardian) -> list[Any]:
    """The guardian's children that are still on the books (not archived)."""
    from apps.children.models import Child

    return list(
        Child.objects.filter(
            guardian_links__guardian=guardian,
            guardian_links__is_active=True,
            archived_at__isnull=True,
        )
        .distinct()
        .order_by("first_name")
    )


def link_by_phone(*, phone: str, chat_id: str) -> Guardian | None:
    """
    Links the chat to the guardian with this phone in the CURRENT organization.

    The phone comes from Telegram's own contact button, and the caller has
    already checked that it is the sender's own number — it is as strong a
    proof as the one-time code. A guardian can be registered in two branches
    with one number; the chat can belong to one guardian per organization
    (the database says so), so the most recently updated one wins, like
    "the parent's last action wins" in `link_from_start`.
    """
    from apps.core.phone import PhoneFormatError, normalise_phone

    chat = (chat_id or "").strip()
    try:
        normalised = normalise_phone(phone)
    except PhoneFormatError:
        return None
    if not chat or not normalised:
        return None

    guardian = (
        Guardian.objects.filter(is_active=True)
        .filter(models.Q(phone=normalised) | models.Q(phone_alt=normalised))
        .order_by("-updated_at")
        .first()
    )
    if guardian is None:
        # Rows saved before phones were normalised (Q7) may read "90 123 45 67".
        # A rare event on a small table: compare in canonical form.
        for candidate in Guardian.objects.filter(is_active=True).order_by("-updated_at"):
            for number in (candidate.phone, candidate.phone_alt):
                if not number:
                    continue
                try:
                    if normalise_phone(number) == normalised:
                        guardian = candidate
                        break
                except PhoneFormatError:
                    continue
            if guardian is not None:
                break
    if guardian is None:
        return None
    if guardian.telegram_chat_id == chat:
        return guardian

    Guardian.objects.filter(telegram_chat_id=chat).exclude(pk=guardian.pk).update(
        telegram_chat_id="", telegram_linked_at=None
    )
    guardian.telegram_chat_id = chat
    guardian.telegram_linked_at = timezone.now()
    guardian.telegram_code = ""
    guardian.save(
        update_fields=["telegram_chat_id", "telegram_linked_at", "telegram_code", "updated_at"]
    )
    return guardian
