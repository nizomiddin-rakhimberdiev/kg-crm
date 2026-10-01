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
from apps.core.params import parse_decimal, parse_int, parse_uuid
from apps.core.typing import request_user
from apps.core.viewsets import BranchScopedMixin, TenantReadOnlyViewSet, TenantViewSet
from apps.notifications import services
from apps.notifications.models import Notification, NotificationStatus, NotificationTemplate
from apps.notifications.serializers import (
    NotificationSerializer,
    NotificationTemplateSerializer,
    SendNotificationSerializer,
    TemplatePreviewSerializer,
)

__all__ = ["NotificationTemplateViewSet", "NotificationViewSet"]


def _reminder_filters(request: Request) -> dict[str, Any]:
    """
    Eslatma filtrlari — ko'rib chiqish va yuborish uchun BIR joydan.

    Ikki joyda alohida o'qilsa, ko'rib chiqish "48 ta" deb ko'rsatib,
    yuborish 51 tasiga ketishi mumkin edi.
    """
    params = request.query_params if request.method == "GET" else request.data
    child_ids = params.get("child_ids") or None
    if isinstance(child_ids, str):
        child_ids = [value for value in child_ids.split(",") if value]

    return {
        "min_amount": parse_decimal(params.get("min_amount"), field=gettext("Summa")),
        "min_days": parse_int(params.get("min_days"), field=gettext("Kunlar")),
        # Buzuq UUID `500` bermasin: filtr qiymati foydalanuvchidan
        # keladi va `filter(id="abc")` ichkarida `ValidationError`
        # ko'taradi (docs/04 §2 — kutilmagan javob o'zi ma'lumot).
        "group_id": parse_uuid(params.get("group_id")),
        "child_ids": [value for value in (parse_uuid(item) for item in (child_ids or [])) if value]
        or None,
    }


class NotificationTemplateViewSet(TenantViewSet):
    permission_module = "notifications"
    permission_action_map = {"preview": "read"}
    model = NotificationTemplate
    serializer_class = NotificationTemplateSerializer
    filterset_fields = ["code", "channel", "language"]

    def perform_create(self, serializer: Any) -> None:
        serializer.save(organization=request_user(self.request).organization)

    @action(detail=False, methods=["post"])
    def preview(self, request: Request) -> Response:
        """
        `POST /notification-templates/preview` — matn qanday ko'rinadi.

        Hech narsa yuborilmaydi va saqlanmaydi. Nega server tomonida:
        uzunlik va bo'laklar hisobi narxni belgilaydi, va ikkinchi
        hisobni frontendda yozish ikkita haqiqat manbai yaratardi
        (PLAN 3.4).
        """
        from apps.notifications.segments import measure, sms_safe

        serializer = TemplatePreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rendered = sms_safe(
            services.render_template(
                serializer.validated_data["body"], serializer.validated_data.get("variables") or {}
            )
        )
        measured = measure(rendered)
        return Response(
            {
                "rendered": rendered,
                "encoding": measured.encoding,
                "characters": measured.characters,
                "parts": measured.parts,
                "limit": measured.limit,
            }
        )


class NotificationViewSet(BranchScopedMixin, TenantReadOnlyViewSet):
    """
    Yuborish jurnali — faqat o'qish + yuborish amallari.

    Jurnal tahrirlanmaydi: yuborilgan xabar yozuvi "men bunday xabar
    olmaganman" degan bahsga yagona javob.
    """

    permission_module = "notifications"
    permission_action_map = {
        "send": "create",
        "retry": "create",
        "remind_debtors": "create",
        "sms_status": "read",
        "reminder_preview": "read",
    }
    model = Notification
    serializer_class = NotificationSerializer
    select_related_fields = ("guardian", "template")
    filterset_fields = ["channel", "status", "guardian"]
    ordering_fields = ["created_at", "sent_at"]

    @action(detail=False, methods=["get"], url_path="status")
    def sms_status(self, request: Request) -> Response:
        """
        `GET /notifications/status` — ekranning bosh holati.

        Eng muhim maydoni `test_mode`: haqiqiy provayder ulanmaguncha
        hech bir xabar ota-onaga bormaydi va ekran buni ochiq aytishi
        kerak (PLAN 3.2). Auditda aynan shu yo'q edi — jurnal
        "Yuborildi" deb turardi.
        """
        from apps.notifications import selectors

        user = request_user(request)
        return Response(selectors.sms_status(branch=user.branch))

    @action(detail=False, methods=["get"], url_path="reminder-preview")
    def reminder_preview(self, request: Request) -> Response:
        """
        `GET /notifications/reminder-preview` — yuborishdan oldingi son.

        Tugma 200 ta SMS yuborishi mumkin va uni qaytarib bo'lmaydi.
        """
        return Response(services.preview_debt_reminders(**_reminder_filters(request)))

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
        # Ekrandagi filtr yuborishda ham saqlanadi: "30+ kun" ni
        # tanlab tugmani bosgan mudira HAMMAGA yuborilishini kutmaydi
        # (PLAN 3.5).
        queued = services.queue_debt_reminders(
            organization=user.organization, **_reminder_filters(request)
        )
        for notification in queued:
            services.dispatch_notification(notification)
        return Response(
            {"queued": len(queued), "results": NotificationSerializer(queued, many=True).data}
        )
