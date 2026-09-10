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
        }
        healthy = all(v == "ok" for v in checks.values())
        return Response(
            {"status": "ok" if healthy else "degraded", "checks": checks},
            status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        )

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
