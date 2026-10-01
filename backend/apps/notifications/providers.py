"""
Yuborish provayderlari — adapter namunasi (docs/02 §17, P2).

Nega adapter: SMS provayderi almashishi deyarli aniq (narx, ishonchlilik,
qamrov), va Telegram/Email keyin qo'shiladi. Provayder chaqiruvi kod
bo'ylab sochilgan bo'lsa, almashtirish butun tizimga tegadigan ish
bo'lardi. Bu yerda esa u bitta sinf.

MVP'da haqiqiy provayder ulanmagan: `ConsoleProvider` xabarni log'ga
yozadi. Bu ongli qaror — real SMS shlyuzi shartnoma va to'lov talab
qiladi, va uni birinchi mijozgacha kechiktirish mumkin. Muhimi, qolgan
hamma narsa (navbat, qayta urinish, yetkazish jurnali) allaqachon
ishlaydi va provayder ulanganda faqat bitta sinf qo'shiladi.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

__all__ = [
    "SendResult",
    "NotificationProvider",
    "ConsoleProvider",
    "EskizProvider",
    "get_provider",
    "is_test_mode",
    "mask_phone",
]


@dataclass(frozen=True)
class SendResult:
    """Provayder javobi — muvaffaqiyat yoki sabab bilan xato."""

    success: bool
    provider_message_id: str = ""
    error: str = ""
    #: Xabar HAQIQATAN yuborilmadi — provayder ulanmagan (PLAN 3.2).
    #:
    #: `success=True` bilan birga keladi, chunki oqim nuqtai nazaridan
    #: hech narsa buzilmagan. Lekin jurnalda u "Yuborildi" emas,
    #: "Test rejimi" bo'lib turishi SHART: aks holda mudira xabar
    #: yetib borgan deb o'ylaydi.
    test_mode: bool = False


class NotificationProvider(Protocol):
    """Har qanday kanal shu shartnomani bajaradi."""

    channel: str

    def send(self, *, address: str, body: str, subject: str = "") -> SendResult: ...


def mask_phone(address: str) -> str:
    """
    `+998901234567` → `+9989****4567`.

    Log'da raqamni butunlay yashirish ham mumkin edi, lekin "qaysi
    raqamga ketdi?" degan savolga javob berish uchun oxirgi to'rt raqam
    kerak. Bu muvozanat: yozuv diagnostika uchun yetarli, lekin log
    fayli o'g'irlansa undan mijozlar bazasi chiqmaydi.
    """
    clean = address.strip()
    if len(clean) <= 8:
        return "*" * len(clean)
    return f"{clean[:5]}{'*' * (len(clean) - 9)}{clean[-4:]}"


class ConsoleProvider:
    """
    Log'ga yozadigan provayder — ishlab chiqish va testlar uchun.

    Haqiqiy provayder ulanmaganda ham butun oqim (navbat → yuborish →
    jurnal) ishlaydi va sinaladi.

    **Log'ga shaxsiy ma'lumot TUSHMAYDI.** Avval bu yerda to'liq telefon
    raqami va xabar matni yozilardi — matn esa ichida bolaning ismini,
    summani va bog'cha nomini olib yuradi. Bu provayder hozircha
    PRODUCTION defaulti (`NOTIFICATION_PROVIDER=console`), ya'ni har bir
    qarz eslatmasi log'ga bola ismi bilan tushardi. Loglar esa
    zaxiradan ham, monitoringdan ham, xato kuzatuvidan ham oson
    chiqadigan joy.

    Matnni to'liq ko'rish kerak bo'lsa — `NOTIFICATION_LOG_BODY=True`.
    U ATAYLAB sozlama: buni yoqish ongli qaror bo'lsin, sukut emas.
    """

    channel = "sms"

    def send(self, *, address: str, body: str, subject: str = "") -> SendResult:
        if getattr(settings, "NOTIFICATION_LOG_BODY", False):
            logger.info("[SMS→%s] %s", address, body)
        else:
            logger.info("[SMS→%s] %s belgi", mask_phone(address), len(body))
        return SendResult(
            success=True,
            provider_message_id=f"console-{abs(hash(body)) % 10**10}",
            test_mode=True,
        )


class EskizProvider:
    """
    Eskiz.uz — O'zbekistondagi SMS shlyuzi (Q8, PLAN 3.1).

    **Token.** Eskiz JWT beradi va u ~30 kun yashaydi. Uni har
    yuborishda qayta olish shlyuzni ortiqcha so'rov bilan yuklaydi va
    sekinlashtiradi, shuning uchun token keshda saqlanadi va faqat
    `401` kelganda yangilanadi. Kesh Redis'da: bir necha worker bir
    xil tokendan foydalanadi.

    **Nega `from` majburiy.** Eskiz tasdiqlanmagan jo'natuvchi nomi
    bilan xabarni qabul qiladi, lekin yetkazmaydi — va bu eng yomon
    holat: jurnal "yuborildi" deydi, ota-ona esa hech narsa olmaydi.
    Shuning uchun `ESKIZ_FROM` bo'sh bo'lsa provayder umuman
    ishga tushmaydi.

    **Xato matni saqlanadi.** "SMS kelmadi" degan shikoyatga javob
    jurnalda bo'lishi kerak, va u "xato" emas, sabab bo'lishi kerak.
    """

    channel = "sms"

    BASE_URL = "https://notify.eskiz.uz/api"
    TOKEN_CACHE_KEY = "eskiz:token"  # noqa: S105 — kesh kaliti, parol emas
    TOKEN_TTL = 60 * 60 * 24 * 20  # 20 kun — 30 kunlik muddatdan xavfsiz ichkarida

    def __init__(self) -> None:
        self.email = getattr(settings, "ESKIZ_EMAIL", "")
        self.password = getattr(settings, "ESKIZ_PASSWORD", "")
        self.sender = getattr(settings, "ESKIZ_FROM", "")
        if not (self.email and self.password and self.sender):
            raise ImproperlyConfigured(
                "Eskiz uchun ESKIZ_EMAIL, ESKIZ_PASSWORD va ESKIZ_FROM kerak."
            )

    # --- Token ---

    def _login(self) -> str:
        import requests

        response = requests.post(
            f"{self.BASE_URL}/auth/login",
            data={"email": self.email, "password": self.password},
            timeout=15,
        )
        response.raise_for_status()
        token = str(response.json()["data"]["token"])
        cache.set(self.TOKEN_CACHE_KEY, token, self.TOKEN_TTL)
        return token

    def _token(self, *, refresh: bool = False) -> str:
        if not refresh:
            cached = cache.get(self.TOKEN_CACHE_KEY)
            if cached:
                return str(cached)
        return self._login()

    # --- Yuborish ---

    def send(self, *, address: str, body: str, subject: str = "") -> SendResult:
        import requests

        # Eskiz mamlakat kodisiz, `+` siz raqam kutadi.
        number = address.lstrip("+")

        for attempt in (0, 1):
            token = self._token(refresh=attempt == 1)
            try:
                response = requests.post(
                    f"{self.BASE_URL}/message/sms/send",
                    headers={"Authorization": f"Bearer {token}"},
                    data={"mobile_phone": number, "message": body, "from": self.sender},
                    timeout=20,
                )
            except requests.RequestException as exc:
                return SendResult(success=False, error=f"Tarmoq xatosi: {exc}"[:500])

            # Token eskirgan — BIR marta yangilab, qayta urinamiz.
            if response.status_code == 401 and attempt == 0:
                continue

            if response.status_code >= 400:
                return SendResult(
                    success=False,
                    error=f"Eskiz {response.status_code}: {response.text}"[:500],
                )

            payload = response.json()
            message_id = str(payload.get("id") or payload.get("message_id") or "")
            if payload.get("status") == "waiting" or message_id:
                return SendResult(success=True, provider_message_id=message_id)
            return SendResult(success=False, error=str(payload)[:500])

        return SendResult(success=False, error="Eskiz: autentifikatsiya muvaffaqiyatsiz")


class FailingProvider:
    """Testlar uchun: har doim xato qaytaradi."""

    channel = "sms"

    def send(self, *, address: str, body: str, subject: str = "") -> SendResult:
        return SendResult(success=False, error="Provayder mavjud emas (test)")


_REGISTRY: dict[str, type] = {
    "console": ConsoleProvider,
    "failing": FailingProvider,
    "eskiz": EskizProvider,
}

#: Haqiqatan xabar yuboradigan provayderlar. Qolganlari test rejimi.
_LIVE_PROVIDERS = frozenset({"eskiz"})


def is_test_mode() -> bool:
    """
    Haqiqiy provayder ulanganmi?

    Ekran shu savolga qarab sariq banner ko'rsatadi: "SMS test
    rejimida — xabarlar haqiqatda yuborilmayapti" (PLAN 3.2).
    """
    name = getattr(settings, "NOTIFICATION_PROVIDER", "console")
    return name not in _LIVE_PROVIDERS


def get_provider(channel: str = "sms") -> NotificationProvider:
    """
    Sozlamadagi provayderni qaytaradi.

    Yangi provayder qo'shish: sinf yozib, `_REGISTRY` ga qo'shish va
    `.env` da `NOTIFICATION_PROVIDER` ni o'zgartirish. Boshqa hech qayerda
    o'zgarish kerak emas — bu adapterning butun maqsadi.
    """
    name = getattr(settings, "NOTIFICATION_PROVIDER", "console")
    provider_class = _REGISTRY.get(name, ConsoleProvider)
    return provider_class()  # type: ignore[return-value]
