"""
Qidiruv kaliti — Q11, PLAN 2.7.

Bog'chada bitta bola uch xil yoziladi. Mudira qaysi birini yozsa ham
topishi kerak: topa olmasa, u "bu bola tizimda yoʻq" deb xulosa qiladi
va ikkinchi marta kiritadi — natijada bitta bola ikkita balansda.
"""

from __future__ import annotations

import pytest

from apps.core.translit import search_key


class TestApostrophes:
    @pytest.mark.parametrize(
        "spelling",
        [
            "Ulugʻbek",
            "Ulugʻbek",
            "Ulugʻbek",
            "Ulugʻbek",
            "ULUGʻBEK",
            "ulugbek",
        ],
    )
    def test_every_apostrophe_gives_the_same_key(self, spelling):
        assert search_key(spelling) == "ulugbek"

    def test_an_apostrophe_is_removed_not_replaced(self):
        """ "o'g'li" va "ogli" bir xil kalit berishi kerak."""
        assert search_key("oʻgʻli") == search_key("ogli") == "ogli"


class TestCyrillic:
    @pytest.mark.parametrize(
        ("cyrillic", "latin"),
        [
            ("Улугбек", "Ulugbek"),
            ("Дилноза", "Dilnoza"),
            ("Шахзода", "Shahzoda"),
            ("Чориев", "Choriev"),
            ("Ғанишер", "Ganisher"),
            ("Қодир", "Qodir"),
        ],
    )
    def test_both_alphabets_meet_in_one_key(self, cyrillic, latin):
        assert search_key(cyrillic) == search_key(latin)


class TestPhones:
    def test_a_phone_becomes_digits(self):
        """Mudira raqamni qanday yozsa ham topadi."""
        assert search_key("+998 90 123 45 67") == "998901234567"
        assert search_key("(90) 123-45-67") == "901234567"


class TestEdges:
    def test_an_empty_value_is_safe(self):
        assert search_key("") == ""
        assert search_key("   ") == ""

    def test_spaces_and_punctuation_vanish(self):
        # `x` → `h`: "Xonim" va "Honim" bitta so'z.
        assert search_key("Ibragimova  Robiya-Xonim") == "ibragimovarobiyahonim"
