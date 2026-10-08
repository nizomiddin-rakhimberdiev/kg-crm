"""
Contract templates (Settings) and contracts (child card) — PLAN 6.5.

Permissions reuse existing modules on purpose: templates are kindergarten
settings (`settings.*`), contracts are part of the child's file
(`children.*`). A new module would change every role in production for a
screen that fits the existing ones.

Row scope (ADR-21) applies: a group-restricted teacher sees and makes
contracts only for her own groups' children.
"""

from __future__ import annotations

from typing import Any

from django.utils.translation import gettext
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response

from apps.contracts import services
from apps.contracts.models import Contract, ContractTemplate
from apps.contracts.serializers import (
    ContractSerializer,
    ContractTemplateSerializer,
    CreateContractSerializer,
    SignSerializer,
    TerminateSerializer,
)
from apps.core.typing import request_user
from apps.core.viewsets import BranchScopedMixin, TenantViewSet

__all__ = ["ContractTemplateViewSet", "ContractViewSet"]


class ContractTemplateViewSet(TenantViewSet):
    permission_module = "settings"
    model = ContractTemplate
    serializer_class = ContractTemplateSerializer
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def get_base_queryset(self) -> Any:
        return ContractTemplate.objects.filter(is_active=True)

    def perform_create(self, serializer: Any) -> None:
        data = serializer.validated_data
        serializer.instance = services.save_template(
            organization=request_user(self.request).organization,
            template=None,
            name=data["name"],
            body=data["body"],
            language=data.get("language", "uz"),
        )

    def perform_update(self, serializer: Any) -> None:
        template = serializer.instance
        data = serializer.validated_data
        serializer.instance = services.save_template(
            organization=template.organization,
            template=template,
            name=data.get("name", template.name),
            body=data.get("body", template.body),
            language=data.get("language", template.language),
        )

    def perform_destroy(self, instance: ContractTemplate) -> None:
        # Contracts keep pointing at it (RESTRICT): switched off, never deleted.
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])

    @action(detail=False, methods=["get"])
    def placeholders(self, request: Request) -> Response:
        """The closed list the editor offers — the same one the server checks."""
        return Response(sorted(services.PLACEHOLDERS))

    @action(detail=False, methods=["get"])
    def sample(self, request: Request) -> Response:
        """
        Namunaviy matn (PLAN 9.3) — tahrirlagichning boshlangʻich nuqtasi.

        Bu yerda hech narsa saqlanmaydi: bogʻcha matnni koʻradi,
        oʻzgartiradi va oʻzi saqlaydi. Shuning uchun u mijoz maʼlumoti
        emas — har bir tashkilot saqlaganda oʻz nusxasini oladi.
        """
        from apps.contracts.sample import SAMPLE_CONTRACT, SAMPLE_NAME

        return Response({"name": SAMPLE_NAME, "body": SAMPLE_CONTRACT})


class ContractViewSet(BranchScopedMixin, TenantViewSet):
    permission_module = "children"
    permission_action_map = {"sign": "update", "terminate": "update"}
    model = Contract
    serializer_class = ContractSerializer
    select_related_fields = ("child", "guardian", "template")
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self) -> Any:
        from apps.children.scope import restrict_children
        from apps.children.selectors import children_queryset

        queryset = super().get_queryset()
        visible = restrict_children(children_queryset(), request_user(self.request))
        queryset = queryset.filter(child__in=visible)
        child_id = self.request.query_params.get("child")
        if child_id:
            queryset = queryset.filter(child_id=child_id)
        return queryset

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        from apps.children.scope import restrict_children
        from apps.children.selectors import children_queryset, guardian_queryset

        serializer = CreateContractSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request_user(request)

        child = (
            self.filter_queryset_by_branch(restrict_children(children_queryset(), user))
            .filter(pk=data["child_id"])
            .first()
        )
        if child is None:
            raise NotFound(gettext("Bola topilmadi."))
        template = ContractTemplate.objects.filter(pk=data["template_id"], is_active=True).first()
        if template is None:
            raise NotFound(gettext("Shablon topilmadi."))
        guardian = None
        if data.get("guardian_id"):
            guardian = guardian_queryset().filter(pk=data["guardian_id"]).first()
            if guardian is None:
                raise NotFound(gettext("Vasiy topilmadi."))

        contract = services.create_contract(
            child=child, template=template, guardian=guardian, created_by=user
        )
        return Response(ContractSerializer(contract).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def sign(self, request: Request, pk: str | None = None) -> Response:
        serializer = SignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contract = services.sign(self.get_object(), **serializer.validated_data)
        return Response(ContractSerializer(contract).data)

    @action(detail=True, methods=["post"])
    def terminate(self, request: Request, pk: str | None = None) -> Response:
        serializer = TerminateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contract = services.terminate(self.get_object(), **serializer.validated_data)
        return Response(ContractSerializer(contract).data)
