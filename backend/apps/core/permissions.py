"""
RBAC — deny-by-default permission klasslari (docs/02 §11.3).

Foydalanish::

    class ChildViewSet(TenantViewSet):
        permission_module = "children"      # → children.read / .create / ...

Backend — yagona hokimiyat. Frontend faqat **yashiradi**, hech qachon
himoya qilmaydi.
"""

from __future__ import annotations

from typing import Any

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.core.typing import request_user

__all__ = ["HasModulePermission", "IsOrgOwner"]

# HTTP metodi → RBAC amali
_METHOD_ACTION: dict[str, str] = {
    "GET": "read",
    "HEAD": "read",
    "OPTIONS": "read",
    "POST": "create",
    "PUT": "update",
    "PATCH": "update",
    "DELETE": "delete",
}


class HasModulePermission(permissions.BasePermission):
    """
    View'ning `permission_module` atributiga qarab `<modul>.<amal>` tekshiradi.

    `permission_module` belgilanmagan bo'lsa — **rad etadi**. Bu ataylab:
    ruxsat modulini yozishni unutgan yangi endpoint ochiq qolgandan ko'ra
    ishlamagani yaxshi (P5).
    """

    message = "Bu amalga ruxsat yo'q."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False

        module = getattr(view, "permission_module", None)
        if not module:
            return False

        action = _METHOD_ACTION.get(request.method or "", None)
        if action is None:
            return False

        # Maxsus amallar o'z ruxsatini e'lon qilishi mumkin:
        #   permission_action_map = {"reset_password": "update"}
        overrides: dict[str, str] = getattr(view, "permission_action_map", {})
        view_action = getattr(view, "action", None)
        if view_action and view_action in overrides:
            action = overrides[view_action]

        return f"{module}.{action}" in _permission_codes(request)


class IsOrgOwner(permissions.BasePermission):
    """Faqat tashkilot egasi (masalan billing — docs/02 §11.2)."""

    message = "Bu amal faqat tashkilot egasiga ruxsat etilgan."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.is_org_owner)


def _permission_codes(request: Request) -> set[str]:
    """Ruxsatlarni so'rov davomida bir marta hisoblab, keshlaydi."""
    cached: set[str] | None = getattr(request, "_permission_codes", None)
    if cached is None:
        cached = request_user(request).permission_codes()
        request._permission_codes = cached  # type: ignore[attr-defined]
    return cached


def has_permission_code(user: Any, code: str) -> bool:
    """Servis qatlami uchun yordamchi."""
    return bool(user and user.is_authenticated and code in user.permission_codes())
