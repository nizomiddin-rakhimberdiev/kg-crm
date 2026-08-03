"""DRF I/O shakllantirish va validatsiya (docs/04 §5–6)."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.accounts.models import Permission, Role, User
from apps.branches.models import Branch
from apps.core.fields import TenantPrimaryKeyRelatedField
from apps.core.typing import request_user

__all__ = [
    "SignupSerializer",
    "LoginSerializer",
    "SelectOrganizationSerializer",
    "PasswordChangeSerializer",
    "UserSerializer",
    "UserWriteSerializer",
    "RoleSerializer",
    "PermissionSerializer",
    "BranchSerializer",
]


def _validate_password_strength(value: str) -> None:
    """DRF validatori — qiymat qaytarmaydi, faqat xato ko'taradi."""
    try:
        validate_password(value)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages)) from exc


# --- Auth ---


class SignupSerializer(serializers.Serializer):
    organization_name = serializers.CharField(max_length=200)
    contact_email = serializers.EmailField()
    contact_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    full_name = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, validators=[_validate_password_strength])


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class SelectOrganizationSerializer(serializers.Serializer):
    pending_token = serializers.CharField()
    organization_id = serializers.UUIDField()


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[_validate_password_strength])


# --- Reference ---


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "code", "module", "action", "label"]
        read_only_fields = fields


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ["id", "name", "code", "description", "is_system", "branch", "permissions"]
        read_only_fields = ["id", "is_system", "permissions"]

    def get_permissions(self, obj: Role) -> list[str]:
        return sorted(
            Permission.objects.filter(role_permissions__role=obj).values_list("code", flat=True)
        )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if self.instance and self.instance.is_system:
            # Tizim rollarini o'zgartirish RBAC matritsasini hujjatdan
            # ajratib yuborardi (docs/03 §10.3).
            raise serializers.ValidationError("Tizim rollarini o'zgartirib bo'lmaydi.")
        return attrs


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = [
            "id",
            "name",
            "code",
            "address",
            "phone",
            "currency",
            "timezone",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


# --- Users ---


class UserSerializer(serializers.ModelSerializer):
    role = RoleSerializer(read_only=True)
    branch = BranchSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "full_name",
            "email",
            "phone",
            "role",
            "branch",
            "is_active",
            "last_login_at",
            "created_at",
        ]
        read_only_fields = fields


class UserWriteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=False, validators=[_validate_password_strength]
    )
    # Queryset so'rov paytida hisoblanadi va joriy tashkilot bilan cheklanadi
    # (apps/core/fields.py) — begona rol/filial ID'si "mavjud emas" beradi.
    role_id = TenantPrimaryKeyRelatedField(model=Role, source="role")
    branch_id = TenantPrimaryKeyRelatedField(
        model=Branch, source="branch", required=False, allow_null=True
    )

    class Meta:
        model = User
        fields = [
            "id",
            "full_name",
            "email",
            "phone",
            "password",
            "role_id",
            "branch_id",
            "is_active",
        ]
        read_only_fields = ["id"]

    # `Role.objects` va `Branch.objects` — TenantManager, ya'ni bu queryset'lar
    # allaqachon joriy tashkilot bilan cheklangan. Boshqa tashkilotning rol
    # ID'si "mavjud emas" validatsiya xatosini beradi, `403` emas —
    # boshqa tenant'da o'sha qator borligi oshkor bo'lmaydi (docs/04 §2).

    def validate_email(self, value: str) -> str:
        organization = request_user(self.context["request"]).organization
        qs = User.objects.filter(organization=organization, email__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Bu email tashkilotda allaqachon mavjud.")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        role = attrs.get("role") or getattr(self.instance, "role", None)
        branch = attrs.get("branch", getattr(self.instance, "branch", None))
        if role and role.code != "org_owner" and branch is None:
            raise serializers.ValidationError(
                {"branch_id": "Org Owner'dan boshqa rollar uchun filial majburiy."}
            )
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "Parol majburiy."})
        return attrs
