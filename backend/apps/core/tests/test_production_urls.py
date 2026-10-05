"""
Productionda havolalar haqiqiy hostga ketishi (PLAN 6.1 / 6.2).

`FRONTEND_URL` sukut bo'yicha `http://localhost:5173`. Agar u productionda
o'rnatilmay qolsa, bot ham, to'lov sahifasi ham havolani YASAYDI — lekin
ota-ona uni ochganda hech qayerga bormaydi. Xato jimgina: serverda hech
narsa yiqilmaydi, jurnal toza, muammoni faqat ota-ona aytganda bilamiz.
"""

from __future__ import annotations

import importlib
import os
from unittest import mock

REQUIRED = {
    "DJANGO_SECRET_KEY": "x" * 48,
    "POSTGRES_DB": "kg_crm",
    "POSTGRES_USER": "kg_crm",
    "POSTGRES_PASSWORD": "parol",
    "POSTGRES_HOST": "db",
    "DJANGO_ALLOWED_HOSTS": "radix-crm.uz",
    "PUBLIC_BASE_URL": "https://radix-crm.uz",
}


def _production_settings(**extra):
    """
    Sozlamalarni Django kabi yuklaydi: avval `base`, keyin `production`.

    `base` ni ham qayta yuklash SHART — `production` undan qiymatni
    import paytida oladi, va eski qiymat qolib ketsa test o'zi yolg'on
    gapirardi (aynan shunday bo'ldi).
    """
    env = {**REQUIRED, **extra}
    # Berilmagan qiymat avvalgi testdan oqib o'tmasin.
    for key in ("FRONTEND_URL",):
        if key not in env:
            env[key] = ""
    with mock.patch.dict(os.environ, env, clear=False):
        base = importlib.import_module("config.settings.base")
        importlib.reload(base)
        module = importlib.import_module("config.settings.production")
        return importlib.reload(module)


def test_frontend_url_follows_the_public_host():
    settings = _production_settings()
    assert settings.FRONTEND_URL == "https://radix-crm.uz"
    assert "localhost" not in settings.FRONTEND_URL


def test_an_empty_line_in_env_also_falls_back():
    """`.env` dagi `FRONTEND_URL=` — namunalardagi eng tabiiy xato."""
    settings = _production_settings(FRONTEND_URL="")
    assert settings.FRONTEND_URL == "https://radix-crm.uz"


def test_an_explicit_value_still_wins():
    settings = _production_settings(FRONTEND_URL="https://app.radix-crm.uz")
    assert settings.FRONTEND_URL == "https://app.radix-crm.uz"


def test_merchant_key_is_required_in_production():
    assert _production_settings().MERCHANT_KEY_REQUIRED is True
