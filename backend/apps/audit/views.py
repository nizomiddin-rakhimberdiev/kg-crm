"""
Audit jurnali endpointi (docs/04 §17).

Faqat o'qish, va faqat o'z tashkiloti. `AuditLog` `TenantScopedModel`
dan meros olmaydi (u append-only va `organization` platforma
harakatlarida `NULL` bo'lishi mumkin), shuning uchun tashkilot filtri bu
yerda QO'LDA yoziladi — va aynan shuning uchun unga alohida test bor.
"""

from __future__ import annotations

from typing import Any

from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.audit import labels
from apps.audit.models import AuditLog
from apps.audit.serializers import AuditLogSerializer
from apps.core.permissions import HasModulePermission
from apps.core.typing import request_user
from apps.subscriptions.permissions import SubscriptionWriteGate

__all__ = ["AuditLogViewSet"]


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [HasModulePermission, SubscriptionWriteGate]
    permission_module = "audit"
    serializer_class = AuditLogSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["action", "entity_type", "entity_id", "actor"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_serializer(self, *args: Any, **kwargs: Any) -> Any:
        """
        Nomlarni BIR MARTA yig'adi — ko'rsatilayotgan qatorlar uchun
        (PLAN 4.4).

        Serializer'ning o'zida qilinsa, har bir qator uchun alohida
        so'rov ketardi: 50 qatorli sahifa 50 ta so'rovga aylanadi va
        jurnal sekinlashadi — aynan shu sahifa esa ko'p qator bilan
        ishlatiladi.

        `get_serializer` da (va `get_serializer_context` da emas),
        chunki qatorlar ro'yxati shu yerda — sahifalash yoqilgan
        yoki yo'qligidan qat'i nazar.
        """
        rows = args[0] if args else kwargs.get("instance")
        batch = list(rows) if isinstance(rows, (list, tuple)) else ([rows] if rows else [])
        kwargs.setdefault("context", self.get_serializer_context())
        kwargs["context"]["labels"] = labels.resolve_labels(batch)
        return super().get_serializer(*args, **kwargs)

    def get_queryset(self) -> Any:
        # `organization_id` — YAGONA chegara. `AuditLog.objects` oddiy
        # menejer, ya'ni uni yozishni unutish butun platformaning
        # jurnalini ochib qo'yardi.
        organization_id = request_user(self.request).organization_id
        if organization_id is None:
            # Tashkilotsiz foydalanuvchi bo'lishi mumkin emas (auth
            # buni ta'minlaydi), lekin agar bo'lsa — bo'sh natija,
            # butun platformaning jurnali emas.
            return AuditLog.objects.none()
        return AuditLog.objects.filter(organization_id=organization_id).select_related("actor")

    @action(detail=False, methods=["get"], url_path="platform-access")
    def platform_access(self, request: Request) -> Response:
        """
        `GET /audit-logs/platform-access` — vendor SIZNING tashkilotingizga
        qanday tegganini ko'rsatadi (docs/04 §17, ADR-10).

        Bu endpoint mahsulot qarori, texnik zarurat emas. Vendor
        kirishini ko'rinmas qilish ishonchni texnik jihatdan emas,
        ijtimoiy jihatdan buzadi: "bizning ma'lumotimizga kim qaraydi?"
        degan savolga javob mijozning o'zida bo'lishi kerak.

        Yozuvlar oddiy audit jurnalining bir qismi — alohida jadval ham,
        alohida yo'l ham yo'q. Ya'ni bu ro'yxatni "to'ldirishni unutish"
        mumkin emas.
        """
        queryset = self.get_queryset().filter(
            Q(entity_type="support_grant") | Q(changes__has_key="platform_user")
        )
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page if page is not None else queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)
