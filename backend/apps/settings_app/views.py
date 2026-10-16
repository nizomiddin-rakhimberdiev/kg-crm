"""Sozlama endpointlari (docs/04 §16)."""

from __future__ import annotations

from django.utils.translation import gettext
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.audit import services as audit
from apps.branches.models import Branch
from apps.core.exceptions import BusinessRuleViolation
from apps.core.permissions import HasModulePermission
from apps.core.typing import request_user
from apps.settings_app import services
from apps.settings_app.serializers import SetSettingSerializer
from apps.subscriptions.permissions import SubscriptionWriteGate

__all__ = ["SettingsViewSet"]


class SettingsViewSet(viewsets.ViewSet):
    """
    Sozlamalar — kalit bo'yicha, jadval qatorlari bo'yicha emas.

    `ViewSet` (model emas): mijoz uchun sozlama bu "kalit → qiymat", va
    uning ortida yozuv bor-yo'qligi ahamiyatsiz. Koddagi default ham,
    bazadagi qiymat ham bir xil ko'rinadi.
    """

    permission_classes = [HasModulePermission, SubscriptionWriteGate]
    permission_module = "settings"
    permission_action_map = {"tax_presets": "read", "apply_tax_preset": "update"}
    lookup_value_regex = r"[^/]+"

    @action(detail=False, methods=["get"], url_path="tax-presets")
    def tax_presets(self, request: Request) -> Response:
        """`GET /settings/tax-presets` — soliq rejimlari va ularning qiymatlari (13.8)."""
        from apps.settings_app import legal

        return Response(legal.presets())

    @action(detail=False, methods=["post"], url_path="tax-presets/apply")
    def apply_tax_preset(self, request: Request) -> Response:
        """`POST /settings/tax-presets/apply {preset}` — stavkalarni birdan yozadi."""
        from apps.settings_app import legal

        user = request_user(request)
        preset = str(request.data.get("preset", ""))
        values = legal.apply_preset(organization=user.organization, preset=preset)
        audit.record(
            action="update",
            request=request._request,
            actor=user,
            entity_type="tax_preset",
            changes={"preset": preset, "values": values},
        )
        return Response({"preset": preset, "values": values})

    def list(self, request: Request) -> Response:
        user = request_user(request)
        return Response(services.effective_settings(branch=user.branch))

    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        user = request_user(request)
        value = services.get_setting(key=pk or "", branch=user.branch)
        if value is None and pk not in services.DEFAULTS:
            raise BusinessRuleViolation(gettext("'{pk}' sozlamasi mavjud emas.").format(pk=pk))
        return Response({"key": pk, "value": value})

    def update(self, request: Request, pk: str | None = None) -> Response:
        """`PUT /settings/{key}` — qiymat o'rnatish."""
        serializer = SetSettingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = request_user(request)
        branch = None
        if data.get("branch_id"):
            # `Branch.objects` tenant bilan cheklangan.
            branch = Branch.objects.filter(pk=data["branch_id"]).first()
            if branch is None:
                raise BusinessRuleViolation(gettext("Filial topilmadi."))

        previous = services.get_setting(key=pk or "", branch=branch)
        setting = services.set_setting(
            organization=user.organization, key=pk or "", value=data["value"], branch=branch
        )
        # Oldingi qiymat ham yoziladi: "SMS nega yuborilmayapti?" degan
        # savolga javob ko'pincha "kimdir o'chirib qo'ygan" bo'ladi.
        audit.record(
            action="update",
            request=request._request,
            actor=user,
            entity_type="system_setting",
            entity_id=setting.id,
            changes={"key": setting.key, "from": previous, "to": data["value"]},
        )
        return Response(
            {
                "key": setting.key,
                "value": setting.value,
                "branch": str(branch.id) if branch else None,
            },
            status=status.HTTP_200_OK,
        )
