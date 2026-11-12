"""
Boshlang'ich o'zbekcha shablonlar to'g'ri apostrof bilan (audit 2026-11-12, E3).

Ota-onaga boradigan Telegram xabari "to'lov" emas, "toʻlov" yozadi
(U+02BB). SMS esa teskari yo'ldan o'tadi — `sms_safe` uni yuborishda
ASCII ga aylantiradi, shuning uchun manbada bitta to'g'ri shakl turadi.
"""

from __future__ import annotations

import re

from apps.notifications import services

ASCII_IN_WORD = re.compile(r"[A-Za-z]['’‘`][A-Za-z]")


def test_uzbek_templates_use_the_uzbek_apostrophe():
    for table in (services.DEFAULT_TEMPLATES, services.TELEGRAM_TEMPLATES):
        for code, body in table.items():
            assert not ASCII_IN_WORD.search(body), (code, body)
