"""Kassa serializerlari (docs/04 §9.4)."""

from __future__ import annotations

from typing import Any

from django.utils.translation import gettext
from rest_framework import serializers

from apps.cash.models import (
    OPERATION_SUBTYPES,
    CashAccount,
    CashCount,
    CashHandover,
    MoneyOperation,
    OperationKind,
)
from apps.core.fields import TenantPrimaryKeyRelatedField

__all__ = [
    "CashAccountSerializer",
    "CashAdjustSerializer",
    "CashCountSerializer",
    "CashCountWriteSerializer",
    "CashHandoverSerializer",
    "CashHandoverWriteSerializer",
    "CashTransferSerializer",
    "MoneyOperationSerializer",
    "MoneyOperationWriteSerializer",
]


class CashAccountSerializer(serializers.ModelSerializer):
    """
    Qop — pul HAQIQATAN turgan joy: naqd yoki bank hisobi (egasining
    qoidasi, 2026-10-15).

    Terminal, o'tkazma, Click, Payme — to'lov USULI, qop emas: hammasi
    bitta bank hisob raqamiga tushadi va o'sha yerdan chiqadi. Usul
    to'lovning o'zida qoladi va hisobotda "qayerdan keldi" deb ko'rinadi.
    Shuning uchun yangi qop faqat `cash` yoki `bank` bo'ladi.
    """

    branch_name = serializers.CharField(source="branch.name", read_only=True)

    #: Usul → qop: naqd — kassaga, qolgan hammasi — bankka.
    _METHOD_FOR_KIND = {"cash": ("", "cash"), "bank": ("", "bank_transfer")}

    class Meta:
        model = CashAccount
        fields = ["id", "name", "kind", "handles_method", "branch", "branch_name", "is_active"]
        # Filial so'rovchidan (`perform_create`), mijozdan emas — ilgari
        # bu maydon majburiy edi va yangi qop umuman ochilmasdi.
        read_only_fields = ["id", "branch", "branch_name"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        kind = attrs.get("kind", getattr(self.instance, "kind", ""))
        if kind not in self._METHOD_FOR_KIND:
            raise serializers.ValidationError(
                {
                    "kind": gettext(
                        "Qop — naqd kassa yoki bank hisobi. Terminal, oʻtkazma, Click va Payme — "
                        "toʻlov usuli: pul bank hisobiga tushadi."
                    )
                }
            )
        method = attrs.get("handles_method", getattr(self.instance, "handles_method", ""))
        if method not in self._METHOD_FOR_KIND[kind]:
            raise serializers.ValidationError(
                {"handles_method": gettext("Bu qop bunday toʻlovlarni qabul qilmaydi.")}
            )
        return attrs


class CashAdjustSerializer(serializers.Serializer):
    """
    Qoldiqni qoʻlda toʻgʻrilash (ADR-29).

    `amount` — manfiy ham boʻlishi mumkin (sanoqda kam chiqdi).
    `opening=True` — bogʻcha tizimga kelgan kundagi boshlangʻich
    qoldiq; aks holda oddiy tuzatish. Sabab MAJBURIY: qoldiq
    oʻzgarsa-yu, nega oʻzgargani yozilmasa, keyin uni hech kim
    tushuntira olmaydi.
    """

    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    reason = serializers.CharField(max_length=255)
    opening = serializers.BooleanField(required=False, default=False)
    occurred_on = serializers.DateField(required=False)


class CashTransferSerializer(serializers.Serializer):
    """
    Qoplar orasida o'tkazma — inkassa, bankdan naqd yechish (Bosqich 12.5).

    Tushum ham, xarajat ham emas: biridan chiqadi, ikkinchisiga kiradi.
    """

    from_account_id = TenantPrimaryKeyRelatedField(model=CashAccount, source="source")
    to_account_id = TenantPrimaryKeyRelatedField(model=CashAccount, source="target")
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=1)
    reason = serializers.CharField(max_length=255)
    occurred_on = serializers.DateField(required=False)
    allow_negative = serializers.BooleanField(required=False, default=False)


class CashHandoverSerializer(serializers.ModelSerializer):
    from_user_name = serializers.CharField(source="from_user.full_name", read_only=True)
    to_user_name = serializers.CharField(source="to_user.full_name", read_only=True)

    class Meta:
        model = CashHandover
        fields = [
            "id",
            "cash_account",
            "from_user",
            "from_user_name",
            "to_user",
            "to_user_name",
            "amount",
            "note",
            "status",
            "decided_at",
            "decision_note",
            "created_at",
        ]
        read_only_fields = fields


class CashHandoverWriteSerializer(serializers.Serializer):
    to_user_id = serializers.UUIDField()
    # Naqd yoki bank hisobi bo'yicha (sukut — naqd kassa).
    cash_account_id = TenantPrimaryKeyRelatedField(
        model=CashAccount, source="cash_account", required=False, allow_null=True
    )
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=1)
    note = serializers.CharField(max_length=255, required=False, allow_blank=True)


class CashCountSerializer(serializers.ModelSerializer):
    cash_account_name = serializers.CharField(source="cash_account.name", read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=None
    )

    class Meta:
        model = CashCount
        fields = [
            "id",
            "cash_account",
            "cash_account_name",
            "counted_on",
            "system_balance",
            "counted",
            "difference",
            "reason",
            "created_by_name",
            "created_at",
        ]
        read_only_fields = fields


class CashCountWriteSerializer(serializers.Serializer):
    cash_account_id = TenantPrimaryKeyRelatedField(model=CashAccount, source="cash_account")
    counted = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0)
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)


class MoneyOperationSerializer(serializers.ModelSerializer):
    """Xarajat bo'lmagan pul harakati (Bosqich 13.2b)."""

    cash_account_name = serializers.CharField(source="cash_account.name", read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=None
    )
    period = serializers.SerializerMethodField()

    class Meta:
        model = MoneyOperation
        fields = [
            "id",
            "kind",
            "subtype",
            "cash_account",
            "cash_account_name",
            "amount",
            "occurred_on",
            "period",
            "counterparty",
            "reason",
            "tax_amount",
            "created_by_name",
            "created_at",
        ]
        read_only_fields = fields

    def get_period(self, operation: MoneyOperation) -> str:
        return f"{operation.period_year}-{operation.period_month:02d}"


class MoneyOperationWriteSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=OperationKind.choices)
    subtype = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    cash_account_id = TenantPrimaryKeyRelatedField(model=CashAccount, source="cash_account")
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=1)
    occurred_on = serializers.DateField()
    reason = serializers.CharField(max_length=255)
    period = serializers.RegexField(r"^\d{4}-(0[1-9]|1[0-2])$", required=False, allow_blank=True)
    counterparty = serializers.CharField(max_length=120, required=False, allow_blank=True)
    allow_negative = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs.get("subtype", "") not in OPERATION_SUBTYPES[attrs["kind"]]:
            raise serializers.ValidationError({"subtype": gettext("Bu turda bunday aniqlik yoʻq.")})
        return attrs
