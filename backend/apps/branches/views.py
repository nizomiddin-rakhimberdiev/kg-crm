"""Filial endpointlari (docs/04 §16)."""

from __future__ import annotations

from django.utils.translation import gettext

from apps.accounts.serializers import BranchSerializer
from apps.audit import services as audit
from apps.branches.models import Branch
from apps.cash import services as cash
from apps.core.exceptions import BusinessRuleViolation
from apps.core.viewsets import TenantViewSet

__all__ = ["BranchViewSet"]


class BranchViewSet(TenantViewSet):
    """
    Filiallar soni **hech qachon cheklanmaydi** va tarifga bog'liq emas
    (docs/01 §4.5) — yangi filial bu biz xohlagan o'sish.
    """

    permission_module = "branches"
    model = Branch
    serializer_class = BranchSerializer
    search_fields = ["name", "code"]
    ordering_fields = ["name", "created_at"]

    def perform_create(self, serializer: object) -> None:
        super().perform_create(serializer)
        # Filial o'z pul qoplari bilan tug'iladi (ADR-17): naqd,
        # terminal, bank, Payme/Click. Ularsiz birinchi to'lov qayerga
        # tushishini tizim bilmasdi.
        cash.ensure_branch_accounts(branch=serializer.instance)  # type: ignore[attr-defined]
        audit.record(
            action="create",
            request=self.request._request,
            actor=self.request.user,
            entity_type="branch",
            entity_id=serializer.instance.id,  # type: ignore[attr-defined]
        )

    def perform_destroy(self, instance: Branch) -> None:
        if instance.users.filter(is_active=True).exists():
            raise BusinessRuleViolation(
                gettext("Filialda faol xodimlar bor — avval ularni koʻchiring yoki oʻchiring.")
            )
        instance.is_active = False
        instance.save(update_fields=["is_active"])
        audit.record(
            action="delete",
            request=self.request._request,
            actor=self.request.user,
            entity_type="branch",
            entity_id=instance.id,
        )
