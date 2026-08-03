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

logger = logging.getLogger(__name__)

__all__ = ["SendResult", "NotificationProvider", "ConsoleProvider", "get_provider"]


@dataclass(frozen=True)
class SendResult:
    """Provayder javobi — muvaffaqiyat yoki sabab bilan xato."""

    success: bool
    provider_message_id: str = ""
    error: str = ""


class NotificationProvider(Protocol):
    """Har qanday kanal shu shartnomani bajaradi."""

    channel: str

    def send(self, *, address: str, body: str, subject: str = "") -> SendResult: ...


class ConsoleProvider:
    """
    Log'ga yozadigan provayder — ishlab chiqish va testlar uchun.

    Haqiqiy provayder ulanmaganda ham butun oqim (navbat → yuborish →
    jurnal) ishlaydi va sinaladi.
    """

    channel = "sms"

    def send(self, *, address: str, body: str, subject: str = "") -> SendResult:
        logger.info("[SMS→%s] %s", address, body)
        return SendResult(success=True, provider_message_id=f"console-{abs(hash(body)) % 10**10}")


class FailingProvider:
    """Testlar uchun: har doim xato qaytaradi."""

    channel = "sms"

    def send(self, *, address: str, body: str, subject: str = "") -> SendResult:
        return SendResult(success=False, error="Provayder mavjud emas (test)")


_REGISTRY: dict[str, type] = {
    "console": ConsoleProvider,
    "failing": FailingProvider,
}


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
