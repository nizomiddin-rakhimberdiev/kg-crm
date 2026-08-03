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
    """

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        checks: dict[str, Any] = {"database": self._check_database()}
        healthy = all(v == "ok" for v in checks.values())
        return Response(
            {"status": "ok" if healthy else "degraded", "checks": checks},
            status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    @staticmethod
    def _check_database() -> str:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:  # noqa: BLE001 — sabab mijozga chiqmaydi
            return "error"
        return "ok"
