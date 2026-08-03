"""
Audit jurnali endpointi (docs/04 §17).

Faqat o'qish, va faqat o'z tashkiloti. `AuditLog` `TenantScopedModel`
dan meros olmaydi (u append-only va `organization` platforma
harakatlarida `NULL` bo'lishi mumkin), shuning uchun tashkilot filtri bu
yerda QO'LDA yoziladi — va aynan shuning uchun unga alohida test bor.
"""

from __future__ import annotations

from typing import Any

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets

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
