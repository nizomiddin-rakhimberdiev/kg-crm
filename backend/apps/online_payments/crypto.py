"""
Encryption of merchant secrets at rest (PLAN 6.1).

A database dump (`pg_dump`, a backup copy, an SQL injection) must not
hand out the keys that move a kindergarten's money. The secret is stored
as a Fernet token; the key comes from `MERCHANT_SECRET_KEY` in `.env`.

Development fallback: when the variable is empty the key is derived from
`SECRET_KEY`. Production refuses that (`MERCHANT_KEY_REQUIRED`), because rotating
`SECRET_KEY` would then silently make every stored merchant key unreadable.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

__all__ = ["encrypt", "decrypt", "InvalidToken"]


def _fernet() -> Fernet:
    key = str(getattr(settings, "MERCHANT_SECRET_KEY", "") or "")
    if not key and getattr(settings, "MERCHANT_KEY_REQUIRED", False):
        raise ImproperlyConfigured("MERCHANT_SECRET_KEY is not set (see .env.example).")
    if not key:
        digest = hashlib.sha256(f"merchant:{settings.SECRET_KEY}".encode()).digest()
        key = base64.urlsafe_b64encode(digest).decode()
    return Fernet(key.encode())


def encrypt(secret: str) -> str:
    return _fernet().encrypt(secret.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()
