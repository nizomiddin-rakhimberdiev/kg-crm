"""HR serializerlari (docs/04 §11.1)."""

from __future__ import annotations

from rest_framework import serializers

from apps.core.fields import TenantPrimaryKeyRelatedField
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
            "is_active",
            "created_at",
        ]
        read_only_fields = fields


class EmployeeWriteSerializer(serializers.ModelSerializer):
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
        ]
        read_only_fields = ["id"]
