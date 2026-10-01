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
]

# --- Modullar (docs/01 §6.1) ---
MODULES: Final[tuple[str, ...]] = (
    "dashboard",
    "children",
    "payments",
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
EXTRA_ACTIONS: Final[dict[str, tuple[str, ...]]] = {
    "children": ("read_all",),
    "attendance": ("read_all",),
}

PERMISSION_LABELS: Final[dict[str, str]] = {
    "dashboard": "Boshqaruv paneli",
    "children": "Bolalar",
    "payments": "To'lovlar",
    "debtors": "Qarzdorlar",
    "attendance": "Davomat",
    "payroll": "Oylik maoshlar",
    "inventory": "Ombor",
    "expenses": "Chiqimlar",
    "reports": "Hisobotlar",
    "notifications": "Bildirishnomalar",
    "settings": "Sozlamalar",
    "branches": "Filiallar",
    "billing": "Obuna va to'lov",
    "users": "Foydalanuvchilar va rollar",
    "audit": "Audit jurnali",
}

# --- Tizim rollari (docs/02 §11.1) ---
OWNER_ROLE_CODE: Final[str] = "org_owner"

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

ROLE_MATRIX: Final[dict[str, dict[str, tuple[str, ...]]]] = {
    "org_owner": {
        "dashboard": _F,
        "children": _FA,
        "payments": _F,
        "debtors": _F,
        "attendance": _FA,
        "payroll": _F,
        "inventory": _F,
        "expenses": _F,
        "reports": _F,
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
        "debtors": _F,
        "attendance": _FA,
        "payroll": _F,
        "inventory": _F,
        "expenses": _F,
        "reports": _F,
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
    "cashier": {
        "dashboard": _R,
        "children": _RA,
        "payments": _F,
        "debtors": _W,
        "attendance": _N,
        "payroll": _N,
        "inventory": _N,
        "expenses": _R,
        "reports": _R,
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
