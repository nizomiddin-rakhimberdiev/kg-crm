"""API ildizi va health check — ikkalasi ham ochiq (autentifikatsiyasiz)."""

from __future__ import annotations

from typing import Any

from django.db import connection
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

__all__ = ["ApiRootView", "HealthCheckView"]


class ApiRootView(APIView):
    """`GET /api/v1/` — bo'sh, lekin konvert bilan javob beradi."""

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response({"version": "v1", "modules": []})


class HealthCheckView(APIView):
    """
    `GET /api/v1/health` — deploy va konteyner uchun tiriklik tekshiruvi.

    Ma'lumotlar bazasiga haqiqiy so'rov yuboradi: faqat "jarayon ishlayapti"
    deydigan health check deploy paytida yolg'on yashil beradi.

    **Redis ham tekshiriladi.** Avval faqat baza tekshirilardi, va Redis
    yiqilganda health check "ok" deb turaverardi — holbuki login va
    signup `500` qaytarardi (throttle keshga murojaat qiladi). Yolg'on
    yashil bergan health check umuman yo'q health check'dan yomonroq:
    u nosozlikni ko'rsatish o'rniga uni yashiradi.
    """

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        checks: dict[str, Any] = {
            "database": self._check_database(),
            "cache": self._check_cache(),
            "worker": self._check_worker(),
        }
        # `degraded` — qisman ishlaydi, `error` — ishlamaydi. Faqat
        # ikkinchisi `503` beradi: ishchisiz tizim hamon o'qiladi va
        # to'lov qabul qiladi, ya'ni load balancer uni navbatdan
        # chiqarib tashlamasligi kerak.
        healthy = not any(v == "error" for v in checks.values())
        return Response(
            {
                "status": "ok" if all(v == "ok" for v in checks.values()) else "degraded",
                "checks": checks,
            },
            status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    @staticmethod
    def _check_worker() -> str:
        """
        Celery ishchisi javob beradimi.

        Nega kerak: baza va Redis sog'lom bo'lsa health "ok" derdi —
        ishchi o'lik bo'lsa ham. Va o'lik ishchi jimgina zarar qiladi:
        hisob-fakturalar chiqmaydi, eslatmalar ketmaydi, eksport
        abadiy "tayyorlanmoqda" holatida qoladi. Hech qanday xato
        ko'rinmaydi, chunki so'rovlar muvaffaqiyatli navbatga tushadi.

        `degraded` qaytaradi, `error` emas: ishchisiz ham tizim
        O'QILADI va to'lov qabul qilinadi — bu to'liq nosozlik emas.
        Shuning uchun u umumiy holatni `503` ga tushirmaydi, lekin
        javobda ko'rinib turadi.
        """
        from django.conf import settings

        # Eager rejimda (testlar) vazifalar so'rov ichida bajariladi —
        # alohida ishchi tushunchasi umuman yo'q. Broker'ga so'rov
        # yuborish bu yerda faqat testni sekinlashtirardi va uni
        # mashinada tasodifan ishlab turgan ishchiga bog'lab qo'yardi.
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            return "ok"

        try:
            from config.celery import app as celery_app

            replies = celery_app.control.ping(timeout=1.0)
            return "ok" if replies else "degraded"
        except Exception:  # noqa: BLE001 — sabab mijozga chiqmaydi
            return "degraded"

    @staticmethod
    def _check_cache() -> str:
        """
        Keshga yozib-o'qib ko'radi.

        Faqat `get` yetarli emas: yiqilgan Redis'da ham ba'zi klientlar
        `None` qaytarib, xato bermasligi mumkin. Yozish esa aloqa
        haqiqatan borligini tekshiradi.
        """
        from django.core.cache import cache

        try:
            cache.set("healthcheck", "ok", 10)
            return "ok" if cache.get("healthcheck") == "ok" else "error"
        except Exception:  # noqa: BLE001 — sabab mijozga chiqmaydi
            return "error"

    @staticmethod
    def _check_database() -> str:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:  # noqa: BLE001 — sabab mijozga chiqmaydi
            return "error"
        return "ok"
