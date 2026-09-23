"""Oylik serializerlari (docs/04 §11.2)."""

from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from apps.core.fields import TenantPrimaryKeyRelatedField
from apps.hr.models import Employee
from apps.payroll.models import EmployeeAdvance, PayrollItem, PayrollRun

__all__ = [
    "CreateRunSerializer",
    "EmployeeAdvanceSerializer",
    "EmployeeAdvanceWriteSerializer",
    "PayrollItemSerializer",
    "PayrollRunSerializer",
    "UpdateItemSerializer",
]


class PayrollItemSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)

    class Meta:
        model = PayrollItem
        fields = [
            "id",
            "employee",
            "employee_name",
            "base_amount",
            "bonus",
            "deduction",
            "advance",
            "gross",
            "net",
            "note",
        ]
        # `gross`/`net` hisoblanadi, mijozdan qabul qilinmaydi — aks holda
        # ular satr qiymatlariga mos kelmay qolishi mumkin edi.
        read_only_fields = ["id", "employee", "employee_name", "base_amount", "gross", "net"]


class PayrollRunSerializer(serializers.ModelSerializer):
    items = PayrollItemSerializer(many=True, read_only=True)
    is_editable = serializers.BooleanField(read_only=True)

    class Meta:
        model = PayrollRun
        fields = [
            "id",
            "period_year",
            "period_month",
            "status",
            "is_editable",
            "total_gross",
            "total_deductions",
            "total_net",
            "finalized_at",
            "paid_at",
            "items",
            "created_at",
        ]
        read_only_fields = fields


class CreateRunSerializer(serializers.Serializer):
    period_year = serializers.IntegerField(min_value=2020, max_value=2100)
    period_month = serializers.IntegerField(min_value=1, max_value=12)
    branch_id = serializers.UUIDField(required=False, allow_null=True)


class UpdateItemSerializer(serializers.Serializer):
    """
    Satr tahriri — pul maydonlari `Decimal` ga o'giriladi.

    JSON'dan pul har doim SATR bo'lib keladi. Uni servisga xomligicha
    uzatish `TypeError` va 500 xatosi berardi; float'ga o'girish esa
    yaxlitlash xatolarini olib kirardi (docs/02 §12.1 — pul hech qachon
    float emas).
    """

    bonus = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, min_value=Decimal("0")
    )
    deduction = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, min_value=Decimal("0")
    )
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)


class EmployeeAdvanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)

    class Meta:
        model = EmployeeAdvance
        fields = ["id", "employee", "employee_name", "amount", "paid_on", "note", "created_at"]
        read_only_fields = ["id", "created_at"]


class EmployeeAdvanceWriteSerializer(serializers.Serializer):
    """
    Avans yozish.

    `.save()` YO'Q: avans yozilgach o'sha davrning qoralama hisoblashi
    ham yangilanishi kerak, ya'ni bu servis ishi (docs/02 §5).
    """

    employee_id = TenantPrimaryKeyRelatedField(model=Employee, source="employee")
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    paid_on = serializers.DateField()
    note = serializers.CharField(max_length=255, required=False, allow_blank=True)
