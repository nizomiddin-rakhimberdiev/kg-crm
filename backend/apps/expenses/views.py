"""Chiqim endpointlari (docs/04 §13)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.audit import services as audit
from apps.branches.selectors import resolve_branch
from apps.core.exceptions import BusinessRuleViolation
from apps.core.typing import request_user
from apps.core.viewsets import BranchScopedMixin, TenantViewSet
from apps.expenses import services
from apps.expenses.models import Expense, ExpenseCategory
from apps.expenses.serializers import (
    ExpenseCategorySerializer,
    ExpenseSerializer,
    ExpenseWriteSerializer,
)

__all__ = ["ExpenseCategoryViewSet", "ExpenseViewSet"]


class ExpenseCategoryViewSet(BranchScopedMixin, TenantViewSet):
    permission_module = "expenses"
    model = ExpenseCategory
    serializer_class = ExpenseCategorySerializer
    search_fields = ["name"]

    def perform_create(self, serializer: Any) -> None:
        user = request_user(self.request)
        branch = resolve_branch(user, self.request.data.get("branch_id"))
        serializer.save(organization=user.organization, branch=branch)


class ExpenseViewSet(BranchScopedMixin, TenantViewSet):
    permission_module = "expenses"
    permission_action_map = {
        "approve": "approve",
        "reject": "approve",
        "mark_paid": "update",
        "summary": "read",
    }
    model = Expense
    select_related_fields = ("category", "approved_by")
    filterset_fields = ["status", "category", "expense_date"]
    ordering_fields = ["expense_date", "amount"]
    search_fields = ["description"]

    def get_serializer_class(self) -> Any:
        return (
            ExpenseSerializer if self.request.method in ("GET", "HEAD") else ExpenseWriteSerializer
        )

    def perform_create(self, serializer: Any) -> None:
        user = request_user(self.request)
        category = serializer.validated_data["category"]
        serializer.save(organization=category.organization, branch=category.branch)
        audit.record(
            action="create",
            request=self.request._request,
            actor=user,
            entity_type="expense",
            entity_id=serializer.instance.id,
            changes={"amount": str(serializer.instance.amount)},
        )

    def perform_update(self, serializer: Any) -> None:
        """Tasdiqlangan chiqim tahrirlanmaydi — summani keyin o'zgartirish
        tasdiqni ma'nosiz qilardi."""
        if serializer.instance.status != "pending":
            raise BusinessRuleViolation("Faqat kutilayotgan chiqimni tahrirlash mumkin.")
        serializer.save()

    @action(detail=True, methods=["post"])
    def approve(self, request: Request, pk: str | None = None) -> Response:
        expense = self.get_object()
        user = request_user(request)
        services.approve_expense(
            expense=expense, approved_by=user, note=request.data.get("note", "")
        )
        audit.record(
            action="update",
            request=request._request,
            actor=user,
            entity_type="expense",
            entity_id=expense.id,
            changes={"status": "approved"},
        )
        expense.refresh_from_db()
        return Response(ExpenseSerializer(expense).data)

    @action(detail=True, methods=["post"])
    def reject(self, request: Request, pk: str | None = None) -> Response:
        expense = self.get_object()
        user = request_user(request)
        services.reject_expense(
            expense=expense, approved_by=user, note=request.data.get("note", "")
        )
        audit.record(
            action="update",
            request=request._request,
            actor=user,
            entity_type="expense",
            entity_id=expense.id,
            changes={"status": "rejected"},
        )
        expense.refresh_from_db()
        return Response(ExpenseSerializer(expense).data)

    @action(detail=True, methods=["post"], url_path="mark-paid")
    def mark_paid(self, request: Request, pk: str | None = None) -> Response:
        expense = self.get_object()
        services.mark_expense_paid(expense=expense)
        expense.refresh_from_db()
        return Response(ExpenseSerializer(expense).data)

    @action(detail=False, methods=["get"])
    def summary(self, request: Request) -> Response:
        """`GET /expenses/summary?from=&to=` — kategoriya kesimida yig'ma."""

        def parse(key: str) -> Any:
            raw = request.query_params.get(key)
            if not raw:
                raise BusinessRuleViolation(f"`{key}` parametri majburiy (2026-07-01).")
            try:
                return datetime.strptime(raw, "%Y-%m-%d").date()
            except ValueError as exc:
                raise BusinessRuleViolation(f"`{key}` formati: 2026-07-01") from exc

        user = request_user(request)
        return Response(
            services.expense_summary(
                organization_id=user.organization_id,
                date_from=parse("from"),
                date_to=parse("to"),
                branch_id=user.branch_id,
            )
        )
