"""
`finance.0006` cheklov qo'yishdan OLDIN ma'lumotni tekshiradi.

Nega kerak: cheklov buzilgan qatorga urilganda Postgres faqat
"check constraint ... is violated by some row" deydi — qaysi qiymat,
qancha qator, qaysi tashkilot ekani aytilmaydi. RLS ostida esa oddiy
`SELECT` ham hech narsa ko'rsatmaydi (siyosat kontekstsiz bo'sh natija
beradi), ya'ni deploy paytida sababni topish uchun hech qanday ip yo'q.

Noma'lum qiymat JIMGINA qayta yozilmaydi: pul yozuvini taxmin bilan
o'zgartirish mumkin emas (brief, 5-qoida).
"""

from __future__ import annotations

import importlib

import pytest

migration = importlib.import_module("apps.finance.migrations.0006_rename_card_to_terminal")


def test_known_values_pass():
    assert migration.unmappable({"cash": 10, "terminal": 3, "bank_transfer": 1, "online": 2}) == {}


def test_card_is_mapped_not_reported():
    """`card` → `terminal` migratsiyaning o'z ishi, xato emas."""
    assert migration.unmappable({"cash": 5, "card": 7}) == {}


def test_an_unknown_value_is_reported_with_its_count():
    assert migration.unmappable({"cash": 5, "transfer": 51}) == {"transfer": 51}


def test_the_message_names_the_value_and_the_fix():
    message = migration.guard_message({"transfer": 51, "qwe": 1})
    assert "transfer" in message and "51" in message
    assert "payment.method" in message
    # Xabar nima qilish kerakligini aytadi — "yiqildi" deb qoldirmaydi.
    assert "bank_transfer" in message


def test_the_guard_raises_on_unknown_data():
    with pytest.raises(RuntimeError, match="transfer"):
        migration.assert_methods_mappable({"transfer": 51})
