"""Moliya serializerlari (docs/04 §9)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.utils.translation import gettext
from rest_framework import serializers

from apps.children.models import Child, Guardian
from apps.core.fields import TenantPrimaryKeyRelatedField
from apps.finance.models import (
    NEW_PAYMENT_METHODS,
    BenefitKind,
    Discount,
    DiscountType,
    Invoice,
    InvoiceLine,
    InvoiceWriteOff,
    Payment,
    TariffPlan,
)
from apps.hr.models import Employee

__all__ = [
    "TariffPlanSerializer",
    "DiscountSerializer",
    "InvoiceSerializer",
    "InvoiceLineSerializer",
    "GenerateInvoicesSerializer",
    "LedgerEntrySerializer",
    "PaymentSerializer",
    "PaymentWriteSerializer",
]


class TariffPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = TariffPlan
        fields = ["id", "name", "amount", "billing_period", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class DiscountSerializer(serializers.ModelSerializer):
    """
    Imtiyoz (Bosqich 12.2): turi, MAJBURIY sababi, muddati va kim kiritgani.

    `custom` dan boshqa turlarda `discount_type`/`value` mijozdan olinmaydi —
    qiymat sozlamadan (`benefits.*`) keladi va `terms` da ko'rinadi.
    `sibling` qo'lda kiritilmaydi: hisoblagich uni oiladan o'zi chiqaradi.
    """

    child_id = TenantPrimaryKeyRelatedField(model=Child, source="child")
    child_name = serializers.CharField(source="child.full_name", read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=None
    )
    discount_type = serializers.ChoiceField(
        choices=DiscountType.choices, required=False, allow_null=True
    )
    value = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    terms = serializers.SerializerMethodField()

    class Meta:
        model = Discount
        fields = [
            "id",
            "child_id",
            "child_name",
            "kind",
            "discount_type",
            "value",
            "terms",
            "reason",
            "valid_from",
            "valid_to",
            "created_by_name",
            "created_at",
            "is_active",
        ]
        read_only_fields = ["id", "child_name", "terms", "created_by_name", "created_at"]

    def get_terms(self, obj: Discount) -> str:
        """Amaldagi shart — "50%" yoki "100 000" — ko'rsatish uchun."""
        from apps.finance.charges import som
        from apps.finance.services import benefit_terms

        if obj.kind and obj.kind != BenefitKind.CUSTOM:
            discount_type, value = benefit_terms(obj.kind, obj.branch)
        else:
            discount_type, value = obj.discount_type, obj.value
        return f"{value:g}%" if discount_type == DiscountType.PERCENT else som(value)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        reason = (attrs.get("reason") or "").strip()
        if not reason:
            raise serializers.ValidationError({"reason": gettext("Imtiyoz sababini yozing.")})
        attrs["reason"] = reason

        kind = attrs.get("kind") or BenefitKind.CUSTOM
        if kind == BenefitKind.SIBLING:
            raise serializers.ValidationError(
                {
                    "kind": gettext(
                        "Aka-uka chegirmasi qoʻlda kiritilmaydi — u umumiy vasiy orqali oʻzi "
                        "qoʻllanadi."
                    )
                }
            )
        if kind == BenefitKind.CUSTOM:
            if not attrs.get("discount_type") or attrs.get("value") is None:
                raise serializers.ValidationError(
                    {"value": gettext("Boshqa turdagi imtiyoz uchun turi va qiymatini kiriting.")}
                )
            if attrs["discount_type"] == DiscountType.PERCENT and attrs["value"] > 100:
                raise serializers.ValidationError(
                    {"value": gettext("Foizli chegirma 100 dan oshmasligi kerak.")}
                )
        else:
            # Qiymat sozlamadan — yozuvda saqlanmaydi, ikki manba bo'lmasin.
            attrs["discount_type"] = DiscountType.PERCENT
            attrs["value"] = Decimal("0")
        valid_to = attrs.get("valid_to")
        if valid_to is not None and valid_to < attrs["valid_from"]:
            raise serializers.ValidationError(
                {"valid_to": gettext("Tugash sanasi boshlanishdan oldin boʻlishi mumkin emas.")}
            )
        return attrs


class InvoiceWriteOffSerializer(serializers.ModelSerializer):
    """Qarzni kechirish hujjati — o'qish uchun (Bosqich 12.3)."""

    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=None
    )

    class Meta:
        model = InvoiceWriteOff
        fields = ["id", "invoice", "amount", "reason", "created_by_name", "created_at"]
        read_only_fields = fields


class InvoiceLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        fields = [
            "id",
            "kind",
            "benefit_kind",
            "description",
            "formula",
            "quantity",
            "unit_amount",
            "line_total",
        ]
        read_only_fields = fields


class InvoiceSerializer(serializers.ModelSerializer):
    child_name = serializers.CharField(source="child.full_name", read_only=True)
    lines = InvoiceLineSerializer(many=True, read_only=True)
    amount_outstanding = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "number",
            "child",
            "child_name",
            "period_year",
            "period_month",
            "amount_due",
            "amount_paid",
            "amount_outstanding",
            "status",
            "issued_date",
            "due_date",
            "lines",
            "created_at",
        ]
        # Hisob-faktura API orqali TAHRIRLANMAYDI: u ledger yozuvini
        # yaratgan hujjat. O'zgartirish kerak bo'lsa — bekor qilib,
        # yangisini chiqarish (D3).
        read_only_fields = fields


class GenerateInvoicesSerializer(serializers.Serializer):
    period_year = serializers.IntegerField(min_value=2020, max_value=2100)
    period_month = serializers.IntegerField(min_value=1, max_value=12)
    branch_id = serializers.UUIDField(required=False, allow_null=True)


class LedgerEntrySerializer(serializers.Serializer):
    """Ledger faqat o'qish uchun — yozish `post_ledger_entry()` orqali."""

    id = serializers.UUIDField(read_only=True)
    entry_type = serializers.CharField(read_only=True)
    direction = serializers.CharField(read_only=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    source_type = serializers.CharField(read_only=True)
    source_id = serializers.UUIDField(read_only=True, allow_null=True)
    occurred_at = serializers.DateTimeField(read_only=True)
    description = serializers.CharField(read_only=True)


class PaymentSerializer(serializers.ModelSerializer):
    child_name = serializers.CharField(source="child.full_name", read_only=True)
    invoice_number = serializers.CharField(source="invoice.number", read_only=True, default=None)
    # Pul HAQIQATAN qaysi hujjatni yopgani (audit, 2026-10-21). `invoice`
    # ustuni faqat kassir hujjatni QO'LDA tanlaganda to'ladi; ADR-20 dan
    # keyin asosiy yo'l — FIFO taqsimot, ya'ni bu ustun odatda bo'sh.
    # Jurnal uni o'qiganda to'langan fakturani "— avans —" deb ko'rsatardi.
    settled_invoices = serializers.SerializerMethodField()
    advance_amount = serializers.SerializerMethodField()
    is_reversed = serializers.BooleanField(read_only=True)
    employee_name = serializers.CharField(source="employee.full_name", read_only=True, default=None)
    received_by_name = serializers.CharField(
        source="received_by.full_name", read_only=True, default=None
    )

    class Meta:
        model = Payment
        fields = [
            "id",
            "child",
            "child_name",
            "invoice",
            "invoice_number",
            "settled_invoices",
            "advance_amount",
            "amount",
            "method",
            "method_corrected_from",
            "reference",
            "paid_at",
            "batch_id",
            "payer",
            "payer_name",
            "payer_kind",
            "payer_tin",
            "employee",
            "employee_name",
            "received_by",
            "received_by_name",
            "backdate_reason",
            "allocation_reason",
            "is_reversed",
            "reversed_at",
            "reversal_reason",
            "created_at",
        ]
        read_only_fields = fields

    def _settled(self, payment: Payment) -> list[Any]:
        """
        Faol taqsimotlar — bo'shatilganlari (qaytarilgan to'lov, bekor
        qilingan faktura) hisobga olinmaydi.

        `payment.allocations.all()` ataylab: ro'yxat `Prefetch` bilan
        keladi, ya'ni har qator uchun alohida so'rov ketmaydi.
        """
        return [row for row in payment.allocations.all() if row.released_at is None]

    def get_settled_invoices(self, payment: Payment) -> list[str]:
        rows = sorted(
            self._settled(payment),
            key=lambda row: (row.invoice.period_year, row.invoice.period_month),
        )
        return [row.invoice.number for row in rows]

    def get_advance_amount(self, payment: Payment) -> str:
        """Hech qaysi hujjatga tegishli bo'lmagan qism — bu AVANS."""
        if payment.is_reversed:
            return "0.00"
        rest = payment.amount - sum((row.amount for row in self._settled(payment)), Decimal("0.00"))
        return f"{max(rest, Decimal('0.00')):.2f}"


class PaymentDetailSerializer(PaymentSerializer):
    """Bitta to'lov — pul qaysi oylarga ketgani bilan (brif §4)."""

    allocations = serializers.SerializerMethodField()
    fiscal = serializers.SerializerMethodField()

    class Meta(PaymentSerializer.Meta):
        fields = [*PaymentSerializer.Meta.fields, "allocations", "fiscal"]
        read_only_fields = fields

    def get_fiscal(self, payment: Payment) -> dict[str, Any]:
        """Fiskal chek holati (13.8): yozilgan, to'lov tizimida yoki kerak emas."""
        from apps.finance import fiscal as rules
        from apps.finance.models import PaymentFiscal

        row = PaymentFiscal.objects.filter(payment=payment).first()
        if row is not None:
            return fiscal_data(row)
        if payment.method in rules.PROVIDER_METHODS:
            status = "provider"
        elif payment.method in rules.REQUIRED_METHODS:
            status = "missing"
        else:
            status = "not_required"
        return {"status": status, "kind": rules.receipt_kind(payment)}

    def get_allocations(self, payment: Payment) -> list[dict[str, Any]]:
        rows = (
            payment.allocations.filter(released_at__isnull=True)
            .select_related("invoice")
            .order_by("invoice__period_year", "invoice__period_month")
        )
        return [
            {
                "invoice_id": str(row.invoice_id),
                "number": row.invoice.number,
                "period": f"{row.invoice.period_year}-{row.invoice.period_month:02d}",
                "amount": f"{row.amount:.2f}",
            }
            for row in rows
        ]


class PaymentLineSerializer(serializers.Serializer):
    """Bitta to'lov usuli va undan kelgan summa (docs/03 §13.5a)."""

    method = serializers.ChoiceField(choices=NEW_PAYMENT_METHODS)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    reference = serializers.CharField(required=False, allow_blank=True, max_length=100)
    # `payroll` qatori uchun — kimning oyligidan.
    employee_id = TenantPrimaryKeyRelatedField(
        model=Employee, source="employee", required=False, allow_null=True
    )


class PaymentBatchSerializer(serializers.Serializer):
    """
    Bitta kassir harakati — bir nechta usul.

    Qatorlar tartibi MUHIM: taqsimlash shu tartibda boradi, ya'ni oxirgi
    qator avansga tushadi (`record_payment_batch`).
    """

    child_id = TenantPrimaryKeyRelatedField(model=Child, source="child")
    invoice_id = TenantPrimaryKeyRelatedField(
        model=Invoice, source="invoice", required=False, allow_null=True
    )
    lines = PaymentLineSerializer(many=True, allow_empty=False)
    paid_at = serializers.DateTimeField(required=False)
    payer_id = TenantPrimaryKeyRelatedField(
        model=Guardian, source="payer", required=False, allow_null=True
    )
    backdate_reason = serializers.CharField(required=False, allow_blank=True, max_length=255)
    allocation_reason = serializers.CharField(required=False, allow_blank=True, max_length=255)
    payer_kind = serializers.ChoiceField(
        choices=["guardian", "employer", "other"], required=False, default="guardian"
    )
    payer_org = serializers.CharField(required=False, allow_blank=True, max_length=255)
    payer_tin = serializers.CharField(required=False, allow_blank=True, max_length=20)


class PaymentWriteSerializer(serializers.Serializer):
    """
    To'lov yozish uchun — `ModelSerializer` EMAS.

    `.save()` modelni to'g'ridan-to'g'ri yozib qo'ymasligi kerak: to'lov
    ledger, hisob-faktura va kesh bilan birga, bitta tranzaksiyada
    yoziladi (docs/03 §13.5). Buning yagona yo'li — servis funksiyasi.
    """

    child_id = TenantPrimaryKeyRelatedField(model=Child, source="child")
    invoice_id = TenantPrimaryKeyRelatedField(
        model=Invoice, source="invoice", required=False, allow_null=True
    )
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    method = serializers.ChoiceField(choices=NEW_PAYMENT_METHODS)
    reference = serializers.CharField(required=False, allow_blank=True, max_length=100)
    paid_at = serializers.DateTimeField(required=False)
    payer_id = TenantPrimaryKeyRelatedField(
        model=Guardian, source="payer", required=False, allow_null=True
    )
    employee_id = TenantPrimaryKeyRelatedField(
        model=Employee, source="employee", required=False, allow_null=True
    )
    backdate_reason = serializers.CharField(required=False, allow_blank=True, max_length=255)
    allocation_reason = serializers.CharField(required=False, allow_blank=True, max_length=255)
    # Bosqich 13.8: ota-onaning ish beruvchisi to'lasa.
    payer_kind = serializers.ChoiceField(
        choices=["guardian", "employer", "other"], required=False, default="guardian"
    )
    payer_org = serializers.CharField(required=False, allow_blank=True, max_length=255)
    payer_tin = serializers.CharField(required=False, allow_blank=True, max_length=20)


def fiscal_data(row: Any) -> dict[str, Any]:
    return {
        "status": "issued",
        "number": row.number,
        "qr": row.qr,
        "issuer": row.issuer,
        "kind": row.kind,
        "recorded_at": row.created_at.isoformat(),
    }
