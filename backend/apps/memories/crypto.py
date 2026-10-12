"""Biometrik vektor va kamera manzillarini shifrlash (Fernet, AES-128-CBC + HMAC)."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

__all__ = ["encrypt_bytes", "decrypt_bytes", "encrypt_text", "decrypt_text"]


def _fernet() -> Fernet:
    key = settings.MEMORIES_ENCRYPTION_KEY
    if not key:
        # Faqat dev/test: production sozlamasi kalitsiz ishga tushmaydi.
        key = base64.urlsafe_b64encode(
            hashlib.sha256(f"memories:{settings.SECRET_KEY}".encode()).digest()
        ).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_bytes(raw: bytes) -> bytes:
    return _fernet().encrypt(raw)


def decrypt_bytes(token: bytes) -> bytes:
    try:
        return _fernet().decrypt(bytes(token))
    except InvalidToken as exc:  # kalit almashgan yoki ma'lumot buzilgan
        raise ValueError("decrypt_failed") from exc


def encrypt_text(value: str) -> str:
    return encrypt_bytes(value.encode()).decode() if value else ""


def decrypt_text(value: str) -> str:
    return decrypt_bytes(value.encode()).decode() if value else ""
