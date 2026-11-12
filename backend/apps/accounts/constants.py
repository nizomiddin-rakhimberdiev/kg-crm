"""
RBAC katalogi — permission'lar va tizim rollari **ma'lumot sifatida**.

docs/02 §11.1–11.2 dagi matritsaning yagona mashina o'qiy oladigan nusxasi.
Yangi rol yoki permission qo'shish — kod emas, konfiguratsiya o'zgarishi.
"""

from __future__ import annotations

from typing import Final

__all__ = [
    "MODULES",
    "ACTIONS",
    "EXTRA_ACTIONS",
    "PERMISSION_LABELS",
    "SYSTEM_ROLES",
    "ROLE_MATRIX",
    "OWN_PAYMENTS_ROLES",
]

# --- Modullar (docs/01 §6.1) ---
MODULES: Final[tuple[str, ...]] = (
    "dashboard",
    "children",
    "payments",
    # Tarif va imtiyoz — bolaning oylik summasini belgilaydi. `payments`
    # da turganda to'lov qabul qiladigan kassir ularni ham yaratardi
    # (audit 2026-11-12).
    "tariffs",
    "discounts",
    "debtors",
    "attendance",
    "payroll",
    "inventory",
    "expenses",
    "reports",
    "notifications",
    "settings",
    "branches",
    "billing",
    "users",
    "audit",
)

ACTIONS: Final[tuple[str, ...]] = ("read", "create", "update", "delete", "export", "approve")

# Faqat ayrim modullarda ma'noga ega amallar (PLAN 2.6).
#
# `read_all` — "butun bog'chani ko'rish". Usiz foydalanuvchi faqat
# O'ZI tarbiyachisi bo'lgan guruhlar bilan cheklanadi. Uni `ACTIONS`
# ga qo'shish har bir modulda keraksiz ruxsat yaratardi (`billing.
# read_all` nimani anglatadi?), shuning uchun u modul bo'yicha
# beriladi.
#
# `reports.finance` — Moliya markazi: foyda-zarar, pul oqimi, holat va oylik
# hisobot paketi, faqat JAMI summalar bilan (Bosqich 13.6, ADR-42). Xodimlar
# kesimidagi ish haqi `payroll.read` da qoladi — boshqaruvchi hisobotni
# tayyorlab topshiradi, lekin kim qancha olishini ko'rmaydi.
EXTRA_ACTIONS: Final[dict[str, tuple[str, ...]]] = {
    "children": ("read_all",),
    "attendance": ("read_all",),
    "reports": ("finance",),
}

PERMISSION_LABELS: Final[dict[str, str]] = {
    "dashboard": "Boshqaruv paneli",
    "children": "Bolalar",
    "payments": "Toʻlovlar",
    "tariffs": "Tariflar",
    "discounts": "Imtiyozlar",
    "debtors": "Qarzdorlar",
    "attendance": "Davomat",
    "payroll": "Oylik maoshlar",
    "inventory": "Ombor",
    "expenses": "Chiqimlar",
    "reports": "Hisobotlar",
    "notifications": "Bildirishnomalar",
    "settings": "Sozlamalar",
    "branches": "Filiallar",
    "billing": "Obuna va toʻlov",
    "users": "Foydalanuvchilar va rollar",
    "audit": "Audit jurnali",
}

# --- Tizim rollari (docs/02 §11.1) ---
OWNER_ROLE_CODE: Final[str] = "org_owner"

#: Yangi tashkilotda `payments_own_only` bayrog'i bilan tug'iladigan
#: tizim rollari (ADR-30). Mavjud tashkilotlarga bu o'z-o'zidan
#: yetmaydi — `manage.py restrict_cashier_role` (dry-run sukut).
OWN_PAYMENTS_ROLES: Final[frozenset[str]] = frozenset({"cashier"})

SYSTEM_ROLES: Final[dict[str, str]] = {
    OWNER_ROLE_CODE: "Tashkilot egasi",
    "director": "Direktor",
    "manager": "Menejer",
    "cashier": "Kassir",
    "attendance_manager": "Davomat menejeri",
}

# Tashkilot egasi rolidan bu ruxsatlarni olib tashlab bo'lmaydi.
#
# Rollarni faqat shu ruxsatga ega odam sozlaydi — ya'ni ularsiz tashkilot
# o'zini o'zi qulflab qo'yadi va rollarni hech kim qayta sozlay olmaydi.
# Bunday holatdan chiqish faqat vendor support orqali bo'lardi (ADR-10),
# shuning uchun uni umuman yuzaga kelmaydigan qilamiz.
OWNER_LOCKED_PERMISSIONS: Final[frozenset[str]] = frozenset({"users.read", "users.update"})

# Qisqartmalar docs/02 §11.2 dagi jadval bilan bir xil:
#   F = to'liq (CRUD + export + approve)   W = yaratish/yangilash + o'qish
#   R = faqat o'qish                        — = kirish yo'q
#
# `approve` `_F` ga kiradi: "to'liq kirish" tasdiqlash huquqini ham
# o'z ichiga olishi kerak, aks holda chiqim tasdiqlash oqimi hech kimda
# ishlamasdi (bu kamchilikni Sprint 7 testi ushladi).
_F: Final[tuple[str, ...]] = ("read", "create", "update", "delete", "export", "approve")
_W: Final[tuple[str, ...]] = ("read", "create", "update")
_R: Final[tuple[str, ...]] = ("read",)
_N: Final[tuple[str, ...]] = ()

# `read_all` bilan — faqat `children` va `attendance` uchun (PLAN 2.6).
#
# Barcha TIZIM rollarida bor, ya'ni mavjud rollar hech narsa sezmaydi.
# Yo'q bo'lgani — guruhga biriktirilgan tarbiyachi: u faqat o'z
# guruhlarini ko'radi.
_FA: Final[tuple[str, ...]] = (*_F, "read_all")
_WA: Final[tuple[str, ...]] = (*_W, "read_all")
_RA: Final[tuple[str, ...]] = (*_R, "read_all")
_FF: Final[tuple[str, ...]] = (*_F, "finance")

ROLE_MATRIX: Final[dict[str, dict[str, tuple[str, ...]]]] = {
    "org_owner": {
        "dashboard": _F,
        "children": _FA,
        "payments": _F,
        "tariffs": _F,
        "discounts": _F,
        "debtors": _F,
        "attendance": _FA,
        "payroll": _F,
        "inventory": _F,
        "expenses": _F,
        "reports": _FF,
        "notifications": _F,
        "settings": _F,
        "branches": _F,
        "billing": _F,
        "users": _F,
        "audit": _F,
    },
    "director": {
        "dashboard": _F,
        "children": _FA,
        "payments": _F,
        "tariffs": _F,
        "discounts": _F,
        "debtors": _F,
        "attendance": _FA,
        "payroll": _F,
        "inventory": _F,
        "expenses": _F,
        "reports": _FF,
        "notifications": _F,
        "settings": _R,
        "branches": _R,
        "billing": _N,
        "users": _R,
        "audit": _R,
    },
    "manager": {
        "dashboard": _R,
        "children": _WA,
        "payments": _R,
        "tariffs": _R,
        "discounts": _R,
        "debtors": _R,
        "attendance": _WA,
        "payroll": _N,
        "inventory": _F,
        "expenses": _W,
        "reports": _R,
        "notifications": _W,
        "settings": _N,
        "branches": _N,
        "billing": _N,
        "users": _N,
        "audit": _N,
    },
    # Kassir pul qabul qiladi va faqat O'ZI qabul qilganini ko'radi
    # (mijoz so'rovi, 2026-10-14; ADR-30). Boshqaruv paneli, chiqimlar va
    # hisobotlar — bog'chaning umumiy tushumi, xarajati, oyligi va sof
    # natijasi — unga yopiq. `payments.read` qoladi: to'lov doskasi
    # aynan shu ruxsat bilan ochiladi va u kassirning asosiy ishi.
    # "Faqat o'ziniki" cheklovi `Role.payments_own_only` dan keladi.
    "cashier": {
        "dashboard": _N,
        "children": _RA,
        # Faktura bekor qilish — `approve`, o'chirish — `delete`: ikkalasi ham
        # kassirda yo'q (audit 2026-11-12).
        "payments": ("read", "create", "update", "export"),
        "tariffs": _R,
        "discounts": _R,
        "debtors": _W,
        "attendance": _N,
        "payroll": _N,
        "inventory": _N,
        "expenses": _N,
        "reports": _N,
        "notifications": _W,
        "settings": _N,
        "branches": _N,
        "billing": _N,
        "users": _N,
        "audit": _N,
    },
    "attendance_manager": {
        "dashboard": _R,
        "children": _RA,
        "payments": _N,
        "tariffs": _N,
        "discounts": _N,
        "debtors": _N,
        "attendance": _FA,
        "payroll": _N,
        "inventory": _N,
        "expenses": _N,
        "reports": _R,
        "notifications": _N,
        "settings": _N,
        "branches": _N,
        "billing": _N,
        "users": _N,
        "audit": _N,
    },
}
