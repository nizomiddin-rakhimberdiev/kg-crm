"""Tug'ilgan kunlar: yaqin sanalar, yil almashuvi va 29-fevral (DB'siz)."""

from datetime import date
from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.children.services import upcoming_birthdays


def child(born: date) -> SimpleNamespace:
    return SimpleNamespace(date_of_birth=born, full_name="Test Bola")


class UpcomingBirthdaysTests(SimpleTestCase):
    def test_bugun_tugilgan_kuni_birinchi_chiqadi(self) -> None:
        rows = upcoming_birthdays([child(date(2020, 10, 10))], today=date(2026, 10, 10), days=7)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["days_until"], 0)
        self.assertEqual(rows[0]["turning"], 6)

    def test_oynadan_keyin_otganlar_chiqmaydi(self) -> None:
        # Tug'ilgan kun 9-oktabr o'tib ketgan, keyingisi 2027 da 9 oktabr (365 kun).
        rows = upcoming_birthdays([child(date(2020, 10, 9))], today=date(2026, 10, 10), days=30)
        self.assertEqual(rows, [])

    def test_yil_almashuvi(self) -> None:
        rows = upcoming_birthdays([child(date(2021, 1, 2))], today=date(2026, 12, 30), days=7)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["birthday"], date(2027, 1, 2))
        self.assertEqual(rows[0]["days_until"], 3)
        self.assertEqual(rows[0]["turning"], 6)

    def test_29_fevral_oddiy_yilda_1_martda(self) -> None:
        # 2027 oddiy yil: 29-fevral yo'q, nishonlash 1-martga o'tadi.
        rows = upcoming_birthdays([child(date(2024, 2, 29))], today=date(2027, 2, 26), days=7)
        self.assertEqual(rows[0]["birthday"], date(2027, 3, 1))
        self.assertEqual(rows[0]["days_until"], 3)

    def test_eng_yaqin_birinchi_tartib(self) -> None:
        kids = [child(date(2020, 10, 15)), child(date(2020, 10, 11)), child(date(2020, 10, 10))]
        rows = upcoming_birthdays(kids, today=date(2026, 10, 10), days=10)
        self.assertEqual([r["days_until"] for r in rows], [0, 1, 5])

    def test_days_chegarasi(self) -> None:
        rows = upcoming_birthdays([child(date(2020, 10, 20))], today=date(2026, 10, 10), days=7)
        self.assertEqual(rows, [])
