"""HR serializerlari (docs/04 §11.1)."""

from __future__ import annotations

from rest_framework import serializers

from apps.core.fields import TenantPrimaryKeyRelatedField, TenantUserRelatedField
from apps.core.serializer_fields import PhoneField
from apps.hr.models import Employee, Position

__all__ = ["PositionSerializer", "EmployeeSerializer", "EmployeeWriteSerializer"]


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ["id", "title", "department", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class EmployeeSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    position_title = serializers.CharField(source="position.title", read_only=True, default=None)
    # Tizim hisobi (PLAN 2.8) — usiz "men qaysi guruhning
    # tarbiyachisiman?" degan savolga javob yo'q.
    user_email = serializers.EmailField(source="user.email", read_only=True, default=None)

    class Meta:
        model = Employee
        fields = [
            "id",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "position",
            "position_title",
            "employment_status",
            "hire_date",
            "termination_date",
            "base_salary",
            "official_salary",
            "user",
            "user_email",
            "is_active",
            "created_at",
        ]
        read_only_fields = fields


class EmployeeWriteSerializer(serializers.ModelSerializer):
    # Xodim telefoni ham normalizatsiya qilinadi (Q7): oylik to'langanda
    # va smena almashinuvida unga SMS ketadi.
    phone = PhoneField(required=False, allow_blank=True)
    # Xodimni tizim hisobiga bog'lash (PLAN 2.8). Ikkisi ataylab
    # alohida: hamma xodim tizimga kirmaydi va hamma hisob xodim emas.
    user_id = TenantUserRelatedField(source="user")
    position_id = TenantPrimaryKeyRelatedField(
        model=Position, source="position", required=False, allow_null=True
    )

    class Meta:
        model = Employee
        fields = [
            "id",
            "first_name",
            "last_name",
            "phone",
            "position_id",
            "employment_status",
            "hire_date",
            "termination_date",
            "base_salary",
            "official_salary",
            "user_id",
        ]
        read_only_fields = ["id"]
