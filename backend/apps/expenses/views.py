"""Chiqim endpointlari (docs/04 §13)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from django.http import Http404
from django.utils.translation import gettext
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.audit import services as audit
from apps.branches.selectors import resolve_branch
from apps.cash.models import CashAccount
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


def _allow_negative(request: Request) -> bool:
    """Foydalanuvchi "qopda pul yetmaydi" ogohlantirishini tasdiqladimi (ADR-29)."""
    return str(request.data.get("allow_negative", "")).lower() in {"true", "1", "yes"}


class ExpenseCategoryViewSet(BranchScopedMixin, TenantViewSet):
    permission_module = "expenses"
    model = ExpenseCategory
    serializer_class = ExpenseCategorySerializer
    search_fields = ["name"]

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        Toifasi umuman yo'q filialga sukut ro'yxat ochiladi (Bosqich 13.2a).

        Ro'yxatdan o'tishda emas, shu yerda: mavjud bog'chalarning o'z
        toifalari bor va ularga tegilmaydi; bo'sh filial esa birinchi
        chiqimni kiritayotganda tayyor ro'yxatni ko'radi.
        """
        from apps.branches.models import Branch

        user = request_user(request)
        branches = Branch.objects.filter(is_active=True)
        if user.branch_id:
            branches = branches.filter(pk=user.branch_id)
        for branch in branches:
            services.ensure_default_categories(branch=branch)
        return super().list(request, *args, **kwargs)

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
        """
        Chiqim DARHOL tasdiqlanadi (PLAN 7.2, egasining qarori 2026-10-06).

        Ilgari u `pending` bo'lib turar va kimdir "Tasdiqlash" tugmasini
        bosishini kutardi. Bog'chada esa chiqimni kiritadigan odam bilan
        tasdiqlaydigan odam bir xil — ya'ni bu bosqich hech narsani
        tekshirmaydi, faqat kiritilgan chiqim hisobotda ham, kassada ham
        ko'rinmay turishiga olib keladi.

        Pul harakati o'z joyida qoladi: uni avvalgidek `approve_expense`
        yozadi (ADR-17), endi u yaratish bilan bir tranzaksiyada.
        """
        user = request_user(self.request)
        data = serializer.validated_data
        category = data["category"]
        items = data.pop("items", None)
        if items:
            # Qatorlar berilgan — summa ULARDAN hisoblanadi (PLAN 7.5).
            serializer.instance = services.create_expense_with_items(
                organization=category.organization,
                branch=category.branch,
                category=category,
                expense_date=data["expense_date"],
                items=items,
                description=data.get("description", ""),
                cash_account=data.get("cash_account"),
                allow_negative=_allow_negative(self.request),
                created_by=user,
                **{
                    key: data[key]
                    for key in (
                        "period_year",
                        "period_month",
                        "is_capex",
                        "amortize_months",
                        "on_credit",
                        "supplier",
                        "due_date",
                    )
                    if key in data
                },
            )
        else:
            serializer.save(organization=category.organization, branch=category.branch)
            services.approve_expense(
                expense=serializer.instance,
                approved_by=user,
                allow_negative=_allow_negative(self.request),
            )
        audit.record(
            action="create",
            request=self.request._request,
            actor=user,
            entity_type="expense",
            entity_id=serializer.instance.id,
            changes={"amount": str(serializer.instance.amount), "status": "approved"},
        )

    def perform_update(self, serializer: Any) -> None:
        """
        Chiqimni tahrirlash (mijoz so'rovi, 2026-10-14).

        Ilgari faqat `pending` chiqim tahrirlanardi — lekin PLAN 7.2 dan
        beri chiqim yaratilishi bilan tasdiqlanadi, ya'ni tahrirlash amalda
        yo'q edi. Pul izi `services.update_expense` da qarshi yozuv bilan
        to'g'rilanadi; bu yerda faqat chaqiriladi va auditga yoziladi.
        """
        user = request_user(self.request)
        data = serializer.validated_data
        before = serializer.instance
        was = {
            "amount": str(before.amount),
            "cash_account": str(before.cash_account_id) if before.cash_account_id else None,
            "expense_date": before.expense_date.isoformat(),
        }
        serializer.instance = services.update_expense(
            expense=before,
            category=data.get("category"),
            expense_date=data.get("expense_date"),
            description=data.get("description"),
            items=data.get("items"),
            amount=data.get("amount"),
            cash_account=data.get("cash_account"),
            allow_negative=_allow_negative(self.request),
            updated_by=user,
        )
        after = serializer.instance
        audit.record(
            action="update",
            request=self.request._request,
            actor=user,
            entity_type="expense",
            entity_id=after.id,
            changes={
                "before": was,
                "after": {
                    "amount": str(after.amount),
                    "cash_account": str(after.cash_account_id) if after.cash_account_id else None,
                    "expense_date": after.expense_date.isoformat(),
                },
            },
        )

    @staticmethod
    def _cash_account(request: Request, user: Any) -> Any:
        """
        So'rovdagi `cash_account_id` — yo'q bo'lsa `None`.

        Begona tashkilotning qopi `404` beradi, `403` emas: bu yerda ham
        tenant chegarasi qolgan hamma joydagi kabi ishlaydi
        (2-invariant, docs/04 §2).
        """
        account_id = request.data.get("cash_account_id")
        if not account_id:
            return None
        account = CashAccount.objects.filter(
            pk=account_id, organization_id=user.organization_id, is_active=True
        ).first()
        if account is None:
            raise Http404
        return account

    @action(detail=True, methods=["post"])
    def approve(self, request: Request, pk: str | None = None) -> Response:
        """
        `POST /expenses/{id}/approve` — ixtiyoriy `{"cash_account_id": …}`.

        Pul aynan shu yerda kassadan chiqadi (ADR-17).
        """
        expense = self.get_object()
        user = request_user(request)
        account = self._cash_account(request, user)
        services.approve_expense(
            expense=expense,
            approved_by=user,
            note=request.data.get("note", ""),
            cash_account=account,
            allow_negative=_allow_negative(request),
        )
        audit.record(
            action="update",
            request=request._request,
            actor=user,
            entity_type="expense",
            entity_id=expense.id,
            changes={
                "status": "approved",
                "cash_account": str(account.id) if account else None,
            },
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
        """
        `POST /expenses/{id}/mark-paid` — ixtiyoriy `{"cash_account_id": …}`.

        Qop ko'rsatilmasa filialning naqd kassasi olinadi (ADR-17).
        """
        expense = self.get_object()
        user = request_user(request)
        account = self._cash_account(request, user)
        raw_day = request.data.get("paid_on")
        try:
            paid_on = datetime.strptime(str(raw_day), "%Y-%m-%d").date() if raw_day else None
        except ValueError as exc:
            raise BusinessRuleViolation(gettext("Sana YYYY-MM-DD koʻrinishida boʻlsin.")) from exc
        services.mark_expense_paid(
            expense=expense,
            cash_account=account,
            allow_negative=_allow_negative(request),
            created_by=user,
            paid_on=paid_on,
        )
        audit.record(
            action="update",
            request=request._request,
            actor=user,
            entity_type="expense",
            entity_id=expense.id,
            changes={"status": "paid", "cash_account": str(account.id) if account else None},
        )
        expense.refresh_from_db()
        return Response(ExpenseSerializer(expense).data)

    @action(detail=False, methods=["get"])
    def summary(self, request: Request) -> Response:
        """`GET /expenses/summary?from=&to=` — kategoriya kesimida yig'ma."""

        def parse(key: str) -> Any:
            raw = request.query_params.get(key)
            if not raw:
                raise BusinessRuleViolation(
                    gettext("`{key}` parametri majburiy (2026-07-01).").format(key=key)
                )
            try:
                return datetime.strptime(raw, "%Y-%m-%d").date()
            except ValueError as exc:
                raise BusinessRuleViolation(
                    gettext("`{key}` formati: 2026-07-01").format(key=key)
                ) from exc

        user = request_user(request)
        return Response(
            services.expense_summary(
                organization_id=user.organization_id,
                date_from=parse("from"),
                date_to=parse("to"),
                branch_id=user.branch_id,
            )
        )
