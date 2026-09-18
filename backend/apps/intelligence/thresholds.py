"""
Radix Intelligence chegaralari — BITTA joyda (docs/07 §4).

Qoidalar (`rules.py`) bu qiymatlarni parametr sifatida oladi; ular
qoidalar ichiga yozilmaydi. Shunda ertaga tashkilot darajasidagi sozlama
(`settings_app`) shu yerga ulanadi va qoidalarga tegilmaydi.

Har bir qiymatning SABABI docs/07 §4 da — bu yerda faqat raqam.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

# --- I-1 · payment_delay (hard rule) ---
OVERDUE_DAYS = 15
CRITICAL_DAYS = 45
CRITICAL_SHARE = 0.10  # faol bolalarning ulushi
CRITICAL_MIN_SUBJECTS = 3  # pol: 12 bolali bog'cha bitta bola uchun critical bo'lmasin

# --- I-2 · attendance_drop (pattern) ---
RECENT_DAYS = 7  # ish kuni
BASELINE_DAYS = 30  # ish kuni
MIN_BASELINE_DAYS = 15  # yozuvli ish kunlari
MIN_GROUP_SIZE = 5
DROP_WARNING = 10.0  # foiz punkti
DROP_CRITICAL = 20.0

# --- Hayot sikli ---
DISMISS_SUPPRESSION = timedelta(days=7)

# --- Ish kunlari ---
#
# Hozirgi sukut — seed_demo va davomat UI'siga mos (Dushanba–Juma).
# Bu mahsulot qoidasi EMAS: shanba ishlaydigan bog'chalar bor. Tashkilot
# darajasidagi sozlama shu qiymatning o'rniga keladi (docs/07 §4).
WORKING_DAYS: frozenset[int] = frozenset({0, 1, 2, 3, 4})  # date.weekday()


@dataclass(frozen=True)
class PaymentDelayThresholds:
    overdue_days: int = OVERDUE_DAYS
    critical_days: int = CRITICAL_DAYS
    critical_share: float = CRITICAL_SHARE
    critical_min_subjects: int = CRITICAL_MIN_SUBJECTS


@dataclass(frozen=True)
class AttendanceDropThresholds:
    recent_days: int = RECENT_DAYS
    baseline_days: int = BASELINE_DAYS
    min_baseline_days: int = MIN_BASELINE_DAYS
    min_group_size: int = MIN_GROUP_SIZE
    drop_warning: float = DROP_WARNING
    drop_critical: float = DROP_CRITICAL
