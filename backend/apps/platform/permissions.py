"""Platforma ruxsatlari (ADR-10)."""

from __future__ import annotations

from typing import Any

from rest_framework import permissions

from apps.platform.models import PlatformRole, PlatformUser

__all__ = ["IsPlatformStaff", "IsPlatformAdmin"]


class IsPlatformStaff(permissions.BasePermission):
    """Faqat vendor xodimi. Mijoz foydalanuvchisi bu yerga kira olmaydi."""

    def has_permission(self, request: Any, view: Any) -> bool:
        return isinstance(getattr(request, "user", None), PlatformUser)


class IsPlatformAdmin(IsPlatformStaff):
    """
    Buzuvchi amallar — faqat administrator.

    Qo'llab-quvvatlash xodimi ko'radi va ruxsat so'raydi, lekin
    mijozning obunasini to'xtata olmaydi: to'xtatish tijorat qarori,
    texnik yordam emas.
    """

    def has_permission(self, request: Any, view: Any) -> bool:
        return super().has_permission(request, view) and request.user.role == PlatformRole.ADMIN
