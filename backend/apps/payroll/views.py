"""Oylik endpointlari (docs/04 §11.2)."""

from __future__ import annotations

from typing import Any

from django.utils.translation import gettext
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.audit import services as audit
from apps.branches.selectors import resolve_branch
from apps.core.exceptions import BusinessRuleViolation
from apps.core.params import require_reason
from apps.core.typing import request_user
from apps.core.viewsets import BranchScopedMixin, TenantViewSet
from apps.payroll import services
from apps.payroll.models import EmployeeAdvance, PayrollItem, PayrollRun
from apps.payroll.serializers import (
    CreateRunSerializer,
    EmployeeAdvanceSerializer,
    EmployeeAdvanceWriteSerializer,
    PayoutRequestSerializer,
    PayrollItemSerializer,
    PayrollRunSerializer,
    UpdateItemSerializer,
)

__all__ = ["PayrollRunViewSet"]


class PayrollRunViewSet(BranchScopedMixin, TenantViewSet):
    """
    Oylik hisoblashlar.

    `PATCH`/`DELETE` yo'q: hisoblash holat mashinasi orqali boshqariladi
    (`create → finalize → mark-paid`, orqaga `reopen`). To'g'ridan-to'g'ri
    tahrirlash yakunlangan hisoblashni jimgina o'zgartirishga yo'l
    ochardi — `reopen` esa sabab so'raydi va audit jurnaliga tushadi.
    """

    permission_module = "payroll"
    # `PATCH`/`DELETE` marshrutga umuman chiqmaydi — holat mashinasi
    # `finalize`/`mark-paid` orqali boshqariladi.
    http_method_names = ["get", "post", "patch", "head", "options"]
    permission_action_map = {
        "create": "create",
        "update_item": "update",
        "finalize": "update",
        "mark_paid": "update",
        # Qayta ochish yakunlangan hujjatni ORTGA qaytaradi, shuning uchun
        # u yakunlashdan qattiqroq qo'riqlanadi: `approve` — tizim
        # rollaridan faqat egasi va direktorda bor (docs/02 §11.2).
        "reopen": "approve",
        "planned_payouts": "read",
        "payslip": "read",
    }
    model = PayrollRun
    serializer_class = PayrollRunSerializer
    filterset_fields = ["status", "period_year", "period_month"]

    def get_base_queryset(self) -> Any:
        # `items__payouts__cash_account` — "oylik qaysi hisobdan
        # berildi?" degan savol har qatorda beriladi, ya'ni usiz
        # ellik xodimli roʻyxat ellik soʻrov boʻlardi.
        return (
            super()
            .get_base_queryset()
            .prefetch_related("items__employee", "items__payouts__cash_account")
        )

    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        Hisoblashni to'g'ridan-to'g'ri tahrirlash yo'q.

        Holatni `finalize`/`mark-paid`/`reopen` boshqaradi; `PATCH` orqali
        `status` ni qo'lda o'zgartirish yakunlangan hisoblashni SABABSIZ va
        izsiz ochib yuborardi.
        """
        # Avval tenant tekshiruvi (`get_object()` → begona qator uchun 404),
        # keyin biznes qoidasi. Teskari tartibda begona tashkilot 422 olardi
        # va bu "bunday narsa yo'q" javobidan farq qilib qolardi
        # (docs/02 §11.3 — tashkilot → ruxsat → biznes qoidasi).
        self.get_object()
        raise BusinessRuleViolation(
            gettext(
                "Hisoblash toʻgʻridan-toʻgʻri tahrirlanmaydi — `finalize`, "
                "`mark-paid` yoki `reopen` amallaridan foydalaning."
            )
        )

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """`POST /payroll/runs` — davr uchun qoralama hisoblash."""
        serializer = CreateRunSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = request_user(request)
        branch = resolve_branch(user, data.get("branch_id"))
        run = services.create_run(
            organization=user.organization,
            branch=branch,
            period_year=data["period_year"],
            period_month=data["period_month"],
        )
        audit.record(
            action="create",
            request=request._request,
            actor=user,
            entity_type="payroll_run",
            entity_id=run.id,
        )
        return Response(PayrollRunSerializer(run).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch"], url_path=r"items/(?P<item_id>[^/.]+)")
    def update_item(
        self, request: Request, pk: str | None = None, item_id: str | None = None
    ) -> Response:
        """Qoralama satrini tahrirlaydi (bonus / ushlab qolish)."""
        run = self.get_object()
        item = PayrollItem.objects.filter(payroll_run=run, pk=item_id).first()
        if item is None:
            raise BusinessRuleViolation(gettext("Satr topilmadi."))

        payload = UpdateItemSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        services.update_item(item=item, **payload.validated_data)
        item.refresh_from_db()
        return Response(PayrollItemSerializer(item).data)

    @action(detail=True, methods=["post"])
    def finalize(self, request: Request, pk: str | None = None) -> Response:
        """Hisoblashni yakunlaydi — shundan keyin o'zgarmas."""
        run = self.get_object()
        user = request_user(request)
        services.finalize_run(run=run, finalized_by=user)
        audit.record(
            action="update",
            request=request._request,
            actor=user,
            entity_type="payroll_run",
            entity_id=run.id,
            changes={"status": "finalized", "total_net": str(run.total_net)},
        )
        run.refresh_from_db()
        return Response(PayrollRunSerializer(run).data)

    @action(detail=True, methods=["post"])
    def recalculate(self, request: Request, pk: str | None = None) -> Response:
        """
        Qoralamani qayta hisoblaydi: yangi xodimlar, avanslar.

        Hisoblash oy oxirida yaratiladi, lekin xodim oyning o'rtasida
        ishga kirishi yoki avans keyinroq berilishi mumkin. Usiz yagona
        yo'l hisoblashni o'chirib qaytadan yaratish bo'lardi.
        """
        run = self.get_object()
        services.recalculate_run(run)
        audit.record(
            action="update",
            request=request._request,
            actor=request_user(request),
            entity_type="payroll_run",
            entity_id=run.id,
            changes={"recalculated": True},
        )
        run.refresh_from_db()
        return Response(PayrollRunSerializer(run).data)

    @action(detail=True, methods=["post"])
    def reopen(self, request: Request, pk: str | None = None) -> Response:
        """
        `POST /payroll/runs/{id}/reopen` — hisoblashni qoralamaga qaytaradi.

        Sabab majburiy: yakunlangan hujjatni ochish audit jurnalida
        izsiz qolmasligi kerak.
        """
        run = self.get_object()
        previous = run.status
        reason = str(request.data.get("reason", "")).strip()
        services.reopen_run(run=run, reason=reason)
        audit.record(
            action="update",
            request=request._request,
            actor=request_user(request),
            entity_type="payroll_run",
            entity_id=run.id,
            changes={"status": "draft", "reopened_from": previous, "reason": reason[:255]},
        )
        run.refresh_from_db()
        return Response(PayrollRunSerializer(run).data)

    @action(detail=True, methods=["post"], url_path="mark-paid")
    def mark_paid(self, request: Request, pk: str | None = None) -> Response:
        """
        `POST /payroll/runs/{id}/mark-paid` — ixtiyoriy `{"payouts": [...]}`.

        Berilmasa taklif qabul qilinadi: rasmiy sof maosh bank
        hisobiga, naqd qism kassaga (docs/03 §14.4a).
        """
        run = self.get_object()
        user = request_user(request)
        payload = PayoutRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        rows = payload.validated_data.get("payouts") or None

        services.pay_run(
            run=run,
            payouts=[dict(row) for row in rows] if rows else None,
            paid_on=payload.validated_data.get("paid_on"),
            allow_negative=payload.validated_data.get("allow_negative", False),
            created_by=user,
        )
        audit.record(
            action="update",
            request=request._request,
            actor=user,
            entity_type="payroll_run",
            entity_id=run.id,
            changes={"status": "paid", "payouts": len(rows) if rows else "auto"},
        )
        run.refresh_from_db()
        return Response(PayrollRunSerializer(run).data)

    @action(detail=True, methods=["get"], url_path="planned-payouts")
    def planned_payouts(self, request: Request, pk: str | None = None) -> Response:
        """`GET /payroll/runs/{id}/planned-payouts` — to'lov taklifi."""
        run = self.get_object()
        rows = services.planned_payouts(run)
        return Response(
            [
                {
                    **row,
                    "payroll_item_id": str(row["payroll_item_id"]),
                    "cash_account_id": str(row["cash_account_id"]),
                    "amount": f"{row['amount']:.2f}",
                }
                for row in rows
            ]
        )

    @action(detail=True, methods=["get"], url_path=r"payslips/(?P<employee_id>[^/.]+)")
    def payslip(
        self, request: Request, pk: str | None = None, employee_id: str | None = None
    ) -> Response:
        """Oylik varaqasi — o'sha oyning holatini ko'rsatadi."""
        run = self.get_object()
        item = PayrollItem.objects.filter(payroll_run=run, employee_id=employee_id).first()
        if item is None:
            raise BusinessRuleViolation(gettext("Bu xodim uchun satr topilmadi."))
        return Response(services.payslip(item=item))


class EmployeeAdvanceViewSet(BranchScopedMixin, TenantViewSet):
    """
    Oy davomida berilgan avanslar (`/payroll/advances`).

    Yozilgan avans o'sha davrning QORALAMA hisoblashiga darhol tushadi.
    Yakunlangan davr o'zgarmaydi — servis `_assert_editable` bilan
    qo'riqlaydi.
    """

    permission_module = "payroll"
    model = EmployeeAdvance
    serializer_class = EmployeeAdvanceSerializer
    select_related_fields = ("employee",)
    filterset_fields = ["employee"]
    ordering_fields = ["paid_on", "amount"]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = EmployeeAdvanceWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request_user(request)

        advance = services.record_advance(
            employee=data["employee"],
            amount=data["amount"],
            paid_on=data["paid_on"],
            note=data.get("note", ""),
            cash_account=data.get("cash_account"),
            allow_negative=data.get("allow_negative", False),
            created_by=user,
        )
        audit.record(
            action="create",
            request=request._request,
            actor=user,
            entity_type="employee_advance",
            entity_id=advance.id,
            changes={"employee": str(advance.employee_id), "amount": str(advance.amount)},
        )
        return Response(EmployeeAdvanceSerializer(advance).data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance: Any) -> None:
        reason = require_reason(self.request.data.get("reason"))
        amount = str(instance.amount)
        entity_id = instance.id
        services.delete_advance(
            advance=instance, reason=reason, created_by=request_user(self.request)
        )
        audit.record(
            action="delete",
            request=self.request._request,
            actor=request_user(self.request),
            entity_type="employee_advance",
            entity_id=entity_id,
            changes={"amount": amount, "reason": reason},
        )
