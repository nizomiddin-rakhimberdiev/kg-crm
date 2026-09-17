"""
Obuna holatiga qarab yozishni to'xtatuvchi darvoza (docs/03 §20.6).

To'lamagan mijozning ma'lumoti **o'chirilmaydi va yashirilmaydi**. U
o'z moliyaviy tarixini ko'rib turadi, eksport qila oladi va istalgan
payt to'lab qaytishi mumkin. To'xtaydigan yagona narsa — yangi yozuv
qo'shish.

Nega `402` va `403` emas: `403` "sizga ruxsat yo'q" degani, ya'ni
foydalanuvchi rolining muammosi. Bu yerda esa rol joyida — hisob
to'lanmagan. `402 Payment Required` aynan shu holat uchun mavjud va u
frontendga to'g'ri xabar ko'rsatish imkonini beradi.
"""

from __future__ import annotations

from typing import Any

from rest_framework import permissions

from apps.core.deployment import is_standalone
from apps.core.typing import request_user

__all__ = ["SubscriptionWriteGate", "SAFE_WRITE_PATHS"]

# Obuna to'xtatilgan bo'lsa ham ISHLAYDIGAN yozish amallari.
#
# Eksport shu ro'yxatda, chunki mijozning o'z operatsion ma'lumoti
# hech qachon hisob-kitob bahsining garovi bo'lmasligi kerak
# (docs/04 §18). Chiqish (`logout`) ham — odamni tizim ichida
# qamab qo'yish mantiqsiz.
SAFE_WRITE_PATHS: tuple[str, ...] = (
    "/api/v1/billing/",
    "/api/v1/auth/logout",
    "/api/v1/auth/refresh",
    "/api/v1/reports/",
)


class SubscriptionWriteGate(permissions.BasePermission):
    """
    `suspended`/`cancelled` holatida yozish amallarini `402` bilan rad etadi.

    O'qish har doim ochiq: mijoz o'z ma'lumotini ko'ra olmasa, u qarzini
    to'lash uchun ham asos ko'rmaydi.
    """

    message = "Obuna to'xtatilgan. Ma'lumotlaringiz saqlanib turibdi — hisobni to'lang."

    def has_permission(self, request: Any, view: Any) -> bool:
        # Standalone nusxada obuna tushunchasi umuman yo'q: mijoz
        # tizimni bir marta sotib olgan (ADR-13). Darvoza viewset'larda
        # QOLADI — `test_write_gate_is_everywhere` uni talab qiladi va
        # bir xil kod ikkala rejimda ishlaydi — lekin bu yerda darhol
        # ochiladi.
        if is_standalone():
            return True

        if request.method in permissions.SAFE_METHODS:
            return True

        path = request.path
        if any(path.startswith(prefix) for prefix in SAFE_WRITE_PATHS):
            return True

        user = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            return True  # autentifikatsiya alohida qatlamning ishi

        subscription = _subscription_for(request_user(request).organization_id)
        if subscription is None:
            # Obunasiz tashkilot — eski ma'lumot yoki migratsiya holati.
            # Bloklash mavjud mijozni ishdan to'xtatardi; bu qaror
            # bilib turib "ochiq" tomonga.
            return True

        if subscription.is_read_only:
            # `False` qaytarish `403` berardi — "sizga ruxsat yo'q",
            # ya'ni ROL muammosi. Bu yerda rol joyida, hisob to'lanmagan.
            # `SubscriptionInactive` Sprint 0 da aynan shu kun uchun
            # yozilgan edi.
            # Kechiktirilgan import: bu modulni DRF sozlamalarni
            # yuklayotganda import qiladi va o'sha payt
            # `rest_framework.views` hali to'liq yuklanmagan bo'ladi.
            from apps.core.exceptions import SubscriptionInactive

            raise SubscriptionInactive(self.message)
        return True


def _subscription_for(organization_id: Any) -> Any:
    from apps.subscriptions.models import Subscription, SubscriptionStatus

    return (
        Subscription.objects.filter(organization_id=organization_id)
        .exclude(status=SubscriptionStatus.CANCELLED)
        .only("status")
        .first()
    )
