"""Bildirishnoma endpointlari (docs/04 §15)."""

from __future__ import annotations

from typing import Any

from django.utils.translation import gettext
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.children.models import Guardian
from apps.core.exceptions import BusinessRuleViolation
from apps.core.typing import request_user
from apps.core.viewsets import BranchScopedMixin, TenantReadOnlyViewSet, TenantViewSet
from apps.notifications import services
from apps.notifications.models import Notification, NotificationStatus, NotificationTemplate
from apps.notifications.serializers import (
    NotificationSerializer,
    NotificationTemplateSerializer,
    SendNotificationSerializer,
)

__all__ = ["NotificationTemplateViewSet", "NotificationViewSet"]


class NotificationTemplateViewSet(TenantViewSet):
    permission_module = "notifications"
    model = NotificationTemplate
    serializer_class = NotificationTemplateSerializer
    filterset_fields = ["code", "channel"]

    def perform_create(self, serializer: Any) -> None:
        serializer.save(organization=request_user(self.request).organization)


class NotificationViewSet(BranchScopedMixin, TenantReadOnlyViewSet):
    """
    Yuborish jurnali — faqat o'qish + yuborish amallari.

    Jurnal tahrirlanmaydi: yuborilgan xabar yozuvi "men bunday xabar
    olmaganman" degan bahsga yagona javob.
    """

    permission_module = "notifications"
    permission_action_map = {"send": "create", "retry": "create", "remind_debtors": "create"}
    model = Notification
    serializer_class = NotificationSerializer
    select_related_fields = ("guardian", "template")
    filterset_fields = ["channel", "status", "guardian"]
    ordering_fields = ["created_at", "sent_at"]

    @action(detail=False, methods=["post"])
    def send(self, request: Request) -> Response:
        """`POST /notifications/send` — bir nechta vasiyga xabar."""
        serializer = SendNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request_user(request)

        # `Guardian.objects` tenant bilan cheklangan — begona vasiy
        # ro'yxatga umuman tushmaydi.
        guardians = list(Guardian.objects.filter(id__in=data["guardian_ids"]))
        if not guardians:
            raise BusinessRuleViolation(gettext("Vasiylar topilmadi."))

        queued: list[Notification] = []
        for guardian in guardians:
            notification = services.queue_notification(
                organization=user.organization,
                branch=guardian.branch,
                guardian=guardian,
                code=data["template_code"],
                channel=data["channel"],
                variables=data.get("variables", {}),
                body_override=data.get("body_override") or None,
            )
            if notification:
                services.dispatch_notification(notification)
                queued.append(notification)

        return Response(
            {
                "queued": len(queued),
                "skipped_no_phone": len(guardians) - len(queued),
                "results": NotificationSerializer(queued, many=True).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def retry(self, request: Request, pk: str | None = None) -> Response:
        """Muvaffaqiyatsiz xabarni qayta yuboradi."""
        notification = self.get_object()
        if notification.status != NotificationStatus.FAILED:
            raise BusinessRuleViolation(
                gettext("Faqat muvaffaqiyatsiz xabarni qayta yuborish mumkin.")
            )
        services.dispatch_notification(notification)
        notification.refresh_from_db()
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=["post"], url_path="remind-debtors")
    def remind_debtors(self, request: Request) -> Response:
        """
        Barcha qarzdorlarga eslatma (docs/04 §10).

        Ro'yxat ledger'dan hisoblanadi, shuning uchun eslatma allaqachon
        to'lagan ota-onaga hech qachon ketmaydi.
        """
        user = request_user(request)
        queued = services.queue_debt_reminders(organization=user.organization)
        for notification in queued:
            services.dispatch_notification(notification)
        return Response(
            {"queued": len(queued), "results": NotificationSerializer(queued, many=True).data}
        )
