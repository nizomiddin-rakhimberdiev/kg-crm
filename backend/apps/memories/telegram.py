"""
Telegram Bot API klienti (adapter) — docs/08 §5.

Token faqat sozlamadan o'qiladi va hech qachon log'ga yozilmaydi (URL ham,
chunki Telegram tokenni URL ichida talab qiladi).
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar, Protocol

import requests
from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)

__all__ = ["TelegramClient", "HttpTelegramClient", "RecordingTelegramClient", "get_client"]

TIMEOUT = 15
MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024  # Telegram Bot API limiti ham 20 MB


class TelegramError(RuntimeError):
    pass


class TelegramClient(Protocol):
    def send_message(self, chat_id: int, text: str) -> None: ...
    def send_photo(self, chat_id: int, data: bytes, caption: str = "") -> None: ...
    def download_file(self, file_id: str) -> bytes: ...


class HttpTelegramClient:
    def __init__(self) -> None:
        if not settings.TELEGRAM_BOT_TOKEN:
            raise TelegramError("TELEGRAM_BOT_TOKEN sozlanmagan")
        self._base = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"
        self._file_base = f"https://api.telegram.org/file/bot{settings.TELEGRAM_BOT_TOKEN}"

    def _call(self, method: str, **kwargs: Any) -> dict[str, Any]:
        try:
            resp = requests.post(f"{self._base}/{method}", timeout=TIMEOUT, **kwargs)
            payload = resp.json()
        except (requests.RequestException, ValueError) as exc:
            # Istisno matni URL (ya'ni token) ni o'z ichiga olishi mumkin — faqat tur.
            raise TelegramError(f"{method}: {type(exc).__name__}") from None
        if not payload.get("ok"):
            raise TelegramError(f"{method}: {payload.get('error_code')}")
        return payload

    def send_message(self, chat_id: int, text: str) -> None:
        self._call("sendMessage", json={"chat_id": chat_id, "text": text[:4000]})

    def send_photo(self, chat_id: int, data: bytes, caption: str = "") -> None:
        self._call(
            "sendPhoto",
            data={"chat_id": chat_id, "caption": caption[:1000]},
            files={"photo": ("photo.jpg", data, "image/jpeg")},
        )

    def delete_webhook(self) -> None:
        """Polling rejimi uchun: webhook bor bo'lsa getUpdates ishlamaydi."""
        self._call("deleteWebhook", json={"drop_pending_updates": False})

    def get_updates(self, offset: int | None, timeout: int = 25) -> list[dict[str, Any]]:
        """Long polling (faqat mahalliy ishlab chiqish; productionda webhook)."""
        body: dict[str, Any] = {"timeout": timeout, "allowed_updates": ["message"]}
        if offset is not None:
            body["offset"] = offset
        try:
            resp = requests.post(f"{self._base}/getUpdates", json=body, timeout=timeout + 10)
            payload = resp.json()
        except (requests.RequestException, ValueError) as exc:
            raise TelegramError(f"getUpdates: {type(exc).__name__}") from None
        if not payload.get("ok"):
            raise TelegramError(f"getUpdates: {payload.get('error_code')}")
        return list(payload.get("result") or [])

    def download_file(self, file_id: str) -> bytes:
        info = self._call("getFile", json={"file_id": file_id})["result"]
        if int(info.get("file_size") or 0) > MAX_DOWNLOAD_BYTES:
            raise TelegramError("file_too_large")
        try:
            resp = requests.get(
                f"{self._file_base}/{info['file_path']}", timeout=TIMEOUT, stream=True
            )
            data = resp.raw.read(MAX_DOWNLOAD_BYTES + 1, decode_content=True)
        except requests.RequestException as exc:
            raise TelegramError(f"download: {type(exc).__name__}") from None
        if len(data) > MAX_DOWNLOAD_BYTES:
            raise TelegramError("file_too_large")
        return data


class RecordingTelegramClient:
    """Testlar uchun: tarmoqsiz, yuborilganlarni yig'adi."""

    messages: ClassVar[list[tuple[int, str]]] = []
    photos: ClassVar[list[tuple[int, bytes, str]]] = []
    files: ClassVar[dict[str, bytes]] = {}

    @classmethod
    def reset(cls) -> None:
        cls.messages, cls.photos, cls.files = [], [], {}

    def send_message(self, chat_id: int, text: str) -> None:
        self.messages.append((chat_id, text))

    def send_photo(self, chat_id: int, data: bytes, caption: str = "") -> None:
        self.photos.append((chat_id, data, caption))

    def download_file(self, file_id: str) -> bytes:
        return self.files[file_id]


def get_client() -> TelegramClient:
    return import_string(settings.TELEGRAM_CLIENT)()
