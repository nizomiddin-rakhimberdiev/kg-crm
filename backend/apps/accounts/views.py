"""Foydalanuvchi, rol va ruxsat endpointlari (docs/04 §6)."""

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet
from django.utils.translation import gettext
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts import delegation, services
from apps.accounts.constants import OWNER_LOCKED_PERMISSIONS, OWNER_ROLE_CODE
from apps.accounts.models import Permission, Role, RolePermission, User
from apps.accounts.serializers import (
    PermissionSerializer,
    RoleSerializer,
    UserSerializer,
    UserWriteSerializer,
)
from apps.audit import services as audit
from apps.core.permissions import has_permission_code
from apps.core.typing import request_user
from apps.core.viewsets import BranchScopedMixin, TenantReadOnlyViewSet, TenantViewSet

__all__ = ["UserViewSet", "RoleViewSet", "PermissionViewSet"]


def _link_employee(user: Any, employee_id: Any) -> None:
    """
    Hisobni xodimga bogʻlaydi yoki bogʻlanishni uzadi (PLAN 9.1b).

    Bogʻlanish `Employee.user` da qoladi — model oʻzgarmadi, faqat uni
    KIM toʻldirishi oʻzgardi. Avvalgi bogʻlanish uziladi: bitta hisob
    ikki xodimga tegishli boʻla olmaydi (`OneToOne`), va eski qator
    jimgina qolib ketsa, tarbiyachi hamon birovning guruhini koʻrardi.
    """
    from apps.hr.models import Employee

    Employee.objects.filter(user=user).exclude(pk=employee_id).update(user=None)
    if employee_id:
        Employee.objects.filter(pk=employee_id).update(user=user)


class UserViewSet(BranchScopedMixin, TenantViewSet):
    """
    Xodimlar ro'yxati filial bo'yicha ham cheklanadi (docs/02 §11.2:
    Direktorda `users` — "R (branch)").

    Org Owner'da `branch` NULL bo'lgani uchun u filial ro'yxatlarida
    ko'rinmaydi — bu to'g'ri: u hech bir filialga tegishli emas, butun
    tashkilotga tegishli.
    """

    permission_module = "users"
    permission_action_map = {"reset_password": "update"}
    model = User
    select_related_fields = ("role", "branch")
    search_fields = ["full_name", "email", "phone"]
    ordering_fields = ["full_name", "created_at"]

    def get_serializer_class(self) -> Any:
        return UserSerializer if self.request.method in ("GET", "HEAD") else UserWriteSerializer

    def perform_create(self, serializer: Any) -> None:
        data = serializer.validated_data
        actor = request_user(self.request)
        organization = actor.organization
        assert organization is not None  # IsAuthenticated + tenant scoping kafolati
        # Delegatsiya (ADR-25): o'zida yo'q huquqli rolni bera olmaydi va
        # filialga bog'langan bo'lsa — faqat o'z filialiga.
        delegation.assert_can_assign_role(actor, data["role"])
        delegation.assert_can_assign_branch(actor, data.get("branch"))
        employee_id = data.pop("employee_id", None)
        user = services.create_user(
            organization=organization,
            email=data["email"],
            password=data.pop("password"),
            full_name=data["full_name"],
            role=data["role"],
            branch=data.get("branch"),
            phone=data.get("phone", ""),
        )
        _link_employee(user, employee_id)
        serializer.instance = user
        audit.record(
            action="create",
            request=self.request._request,
            actor=self.request.user,
            entity_type="user",
            entity_id=user.id,
            changes={"email": user.email, "role": user.role.code if user.role else None},
        )

    def update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        # Avtorizatsiya validatsiyadan OLDIN: ruxsati yo'q odam `400` bilan
        # maydonlar haqida ma'lumot olmasin, aniq `403` olsin.
        delegation.assert_can_manage_user(request_user(request), self.get_object())
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer: Any) -> None:
        actor = request_user(self.request)
        data = serializer.validated_data
        if "role" in data:
            delegation.assert_can_assign_role(actor, data["role"])
        if "branch" in data:
            delegation.assert_can_assign_branch(actor, data["branch"])
        password = data.pop("password", None)
        employee_id = data.pop("employee_id", "keep")
        user = serializer.save()
        if employee_id != "keep":
            _link_employee(user, employee_id)
        if password:
            user.set_password(password)
            user.save(update_fields=["password"])
            services.revoke_all_refresh_tokens(user)
        audit.record(
            action="update",
            request=self.request._request,
            actor=self.request.user,
            entity_type="user",
            entity_id=user.id,
            # Qiymatlar emas, faqat o'zgargan maydon nomlari yoziladi:
            # audit jurnaliga parol yoki boshqa maxfiy qiymat tushmasin.
            changes={"fields": sorted(serializer.validated_data)},
        )

    def perform_destroy(self, instance: User) -> None:
        delegation.assert_can_manage_user(request_user(self.request), instance)
        # Yumshoq o'chirish (D5) + barcha sessiyalarni yopish.
        instance.is_active = False
        instance.save(update_fields=["is_active"])
        services.revoke_all_refresh_tokens(instance)
        audit.record(
            action="delete",
            request=self.request._request,
            actor=self.request.user,
            entity_type="user",
            entity_id=instance.id,
        )

    @action(detail=True, methods=["post"], url_path="reset-password")
    def reset_password(self, request: Request, pk: str | None = None) -> Response:
        user = self.get_object()
        delegation.assert_can_manage_user(request_user(request), user)
        new_password = request.data.get("password")
        if not new_password:
            return Response(
                {
                    "success": False,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": gettext("Yangi parol koʻrsatilmagan."),
                        "details": {"password": [gettext("Bu maydon majburiy.")]},
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(new_password)
        user.save(update_fields=["password"])
        services.revoke_all_refresh_tokens(user)
        audit.record(
            action="update",
            request=request._request,
            actor=request.user,
            entity_type="user",
            entity_id=user.id,
            changes={"password_reset": True},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class RoleViewSet(TenantViewSet):
    permission_module = "users"
    permission_action_map = {
        "permissions": "read",
        "set_permissions": "update",
        "templates": "read",
    }
    model = Role
    serializer_class = RoleSerializer
    search_fields = ["name", "code"]

    def update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        delegation.assert_can_edit_role(request_user(request), self.get_object())
        return super().update(request, *args, **kwargs)

    def perform_destroy(self, instance: Role) -> None:
        delegation.assert_can_edit_role(request_user(self.request), instance)
        if instance.is_system:
            from apps.core.exceptions import BusinessRuleViolation

            raise BusinessRuleViolation(gettext("Tizim rolini oʻchirib boʻlmaydi."))
        instance.is_active = False
        instance.save(update_fields=["is_active"])

    @action(detail=False, methods=["get"], url_path="templates")
    def templates(self, request: Request) -> Response:
        """
        Tayyor rol shablonlari (audit, 2026-10-21).

        Rollar ekranida 15 modul × 6 amal ≈ 100 belgi bor va yangi rol
        uchun ularni qo'lda bosish — amalda qilinmaydigan ish. Tizim
        rollarining shakli allaqachon kodda (`ROLE_MATRIX`), ya'ni
        shablon yangi ma'lumot emas: u o'sha matritsani ochib beradi.
        Egasining roli shablon EMAS — uni tarqatib bo'lmaydi.

        **ADR-25 shu yerda ham**: javob chaqiruvchining o'z ruxsatlari
        bilan kesishtiriladi va tushib qolganlari `dropped` da
        AYTILADI. Jim qisqartirish eng yomoni bo'lardi: menejer
        shablonni bosib, keyin saqlashda tushunarsiz xato olardi.
        """
        from apps.accounts.constants import OWN_PAYMENTS_ROLES, ROLE_MATRIX, SYSTEM_ROLES

        user = request_user(request)
        catalog = set(Permission.objects.values_list("code", flat=True))
        own = (
            catalog
            if user.is_org_owner
            else {code for code in catalog if has_permission_code(user, code)}
        )

        rows = []
        for code, modules in ROLE_MATRIX.items():
            if code == OWNER_ROLE_CODE:
                continue
            wanted = {
                f"{module}.{action}"
                for module, actions in modules.items()
                for action in actions
                if f"{module}.{action}" in catalog
            }
            rows.append(
                {
                    "code": code,
                    "title": str(SYSTEM_ROLES.get(code, code)),
                    "permissions": sorted(wanted & own),
                    "dropped": sorted(wanted - own),
                    "payments_own_only": code in OWN_PAYMENTS_ROLES,
                }
            )
        return Response(rows)

    @action(detail=True, methods=["get", "put"], url_path="permissions")
    def permissions(self, request: Request, pk: str | None = None) -> Response:
        role = self.get_object()

        if request.method == "GET":
            codes = Permission.objects.filter(role_permissions__role=role).values_list(
                "code", flat=True
            )
            return Response({"permissions": sorted(codes)})

        wanted = set(request.data.get("permissions", []))
        delegation.assert_can_edit_role(request_user(request), role, wanted)

        # Matritsa (docs/02 §11.2) — boshlang'ich holat, abadiy cheklov emas:
        # tashkilot egasi har bir rolni o'z ish jarayoniga moslashtira oladi.
        # Yagona istisno — egasining o'zini qulflab qo'yishi.
        if role.code == OWNER_ROLE_CODE and not wanted >= OWNER_LOCKED_PERMISSIONS:
            from apps.core.exceptions import BusinessRuleViolation

            missing = sorted(OWNER_LOCKED_PERMISSIONS - wanted)
            raise BusinessRuleViolation(
                gettext(
                    "Tashkilot egasi rolidan quyidagi ruxsatlarni olib tashlab boʻlmaydi "
                    "(aks holda rollarni hech kim sozlay olmay qoladi): {join}."
                ).format(join=", ".join(missing))
            )

        permissions = list(Permission.objects.filter(code__in=wanted))
        RolePermission.objects.filter(role=role).delete()
        RolePermission.objects.bulk_create(
            [RolePermission(role=role, permission=p) for p in permissions]
        )
        audit.record(
            action="update",
            request=request._request,
            actor=request.user,
            entity_type="role",
            entity_id=role.id,
            changes={"permissions": sorted(p.code for p in permissions)},
        )
        return Response({"permissions": sorted(p.code for p in permissions)})


class PermissionViewSet(TenantReadOnlyViewSet):
    """
    Global ruxsatlar katalogi — faqat o'qish.

    `Permission` da `organization_id` yo'q (docs/03 §6.2), shuning uchun
    oddiy queryset ishlatiladi. Bu tenant sizib chiqishi emas: katalog
    barcha mijozlar uchun bir xil va hech qanday mijoz ma'lumotini
    o'z ichiga olmaydi.
    """

    permission_module = "users"
    serializer_class = PermissionSerializer
    pagination_class = None

    def get_queryset(self) -> QuerySet[Permission]:
        return Permission.objects.all()
