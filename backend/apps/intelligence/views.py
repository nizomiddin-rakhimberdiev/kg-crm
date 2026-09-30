"""
Insight endpointlari (docs/07 §11).

  GET  /insights                — ro'yxat; `?status=open` (sukut) | all
  GET  /insights/briefing       — ochiq insight'lar + jonli tekshiruvlar
  POST /insights/{id}/seen      — birinchi ochilish (idempotent)
  POST /insights/{id}/resolve
  POST /insights/{id}/dismiss

Ruxsat moduli — `dashboard`: o'qish uchun `dashboard.read`, holat
o'zgartirish uchun `dashboard.update`. Yangi permission kodi YO'Q.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db.models import Case, DecimalField, IntegerField, Sum, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.typing import request_user
from apps.core.viewsets import BranchScopedMixin, TenantReadOnlyViewSet
from apps.intelligence import selectors, services
from apps.intelligence.models import OPEN_STATUSES, Insight
from apps.intelligence.serializers import InsightSerializer
from apps.intelligence.thresholds import OVERDUE_DAYS

MONEY: DecimalField = DecimalField(max_digits=14, decimal_places=2)


def _ranked(queryset: Any) -> Any:
    """`critical` avval — alifbo bo'yicha emas ("warning" > "critical")."""
    return queryset.annotate(
        severity_rank=Case(
            When(severity="critical", then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        )
    )


class InsightViewSet(BranchScopedMixin, TenantReadOnlyViewSet):
    permission_module = "dashboard"
    permission_action_map = {"seen": "update", "resolve": "update", "dismiss": "update"}
    model = Insight
    serializer_class = InsightSerializer
    # `status` ataylab yo'q — uni `get_queryset` o'zi o'qiydi (`open` | `all`
    # | aniq holat); django-filter esa `all` ni rad etardi.
    filterset_fields = ["type", "severity"]
    ordering_fields = ["generated_at", "severity_rank"]
    ordering = ["severity_rank", "-generated_at"]

    def get_queryset(self) -> Any:
        queryset = _ranked(super().get_queryset())
        if self.action != "list":
            # Detail/amallar yopiq qatorni ham ko'radi — "allaqachon
            # yopilgan" 422 bo'lishi uchun, 404 emas.
            return queryset
        # Ro'yxatda sukut — faqat ochiqlar: dashboard shuni so'raydi.
        # `?status=all` tarixni ochadi.
        requested = self.request.query_params.get("status")
        if requested in (None, "", "open"):
            return queryset.filter(status__in=OPEN_STATUSES)
        if requested == "all":
            return queryset
        return queryset.filter(status=requested)

    @action(detail=False, methods=["get"])
    def briefing(self, request: Request) -> Response:
        """Kunlik brifing: ochiq insight'lar + bugungi jonli tekshiruvlar."""
        user = request_user(request)
        branch_id = request.query_params.get("branch") or (
            user.branch_id if not user.is_org_owner else None
        )
        open_rows = _ranked(
            self.filter_queryset_by_branch(Insight.objects.filter(status__in=OPEN_STATUSES))
        ).order_by("severity_rank", "-generated_at")
        today = timezone.localdate()

        checks: dict[str, Any] = {"working_day": selectors.is_working_day(today)}
        if branch_id:
            checks["attendance"] = selectors.attendance_completeness(branch_id=branch_id, day=today)
        else:
            # Org Owner, filial tanlanmagan: har bir filial alohida.
            checks["attendance_by_branch"] = {
                str(b): selectors.attendance_completeness(branch_id=b, day=today)
                for b in selectors.branch_ids_for(user.organization_id)
            }

        # Insight'lar kechasi 03:30 da hisoblanadi, dashboard esa jonli
        # raqam ko'rsatadi — auditda bitta ekranda ikkita raqam turgan
        # edi (27,9 mln va 26,5 mln) va qaysi biri to'g'riligi
        # ko'rinmasdi. Endi ikkalasi ham beriladi va HAR BIRI qachongi
        # holat ekani aytiladi.
        from apps.finance.selectors import debtor_queryset

        debtors = debtor_queryset()
        if branch_id:
            debtors = debtors.filter(branch_id=branch_id)
        live = debtors.aggregate(
            total=Coalesce(Sum("ledger_balance"), Value(Decimal("0"), output_field=MONEY)),
            overdue=Coalesce(Sum("overdue_amount"), Value(Decimal("0"), output_field=MONEY)),
        )

        newest = open_rows.values_list("generated_at", flat=True).first()

        return Response(
            {
                "date": today.isoformat(),
                "open_count": open_rows.count(),
                "insights": InsightSerializer(open_rows[:20], many=True).data,
                "checks": checks,
                # Insight'lar qachon hisoblangani — kartada "holat: HH:MM".
                "generated_at": newest.isoformat() if newest else None,
                # Jonli raqamlar — dashboard bilan BIR XIL manbadan
                # (`finance/balance.py`).
                "totals": {
                    "total_debt": f"{live['total']:.2f}",
                    "overdue_debt": f"{live['overdue']:.2f}",
                    "overdue_days": OVERDUE_DAYS,
                },
            }
        )

    @action(detail=True, methods=["post"])
    def seen(self, request: Request, pk: str | None = None) -> Response:
        insight = services.mark_seen(insight=self.get_object())
        return Response(InsightSerializer(insight).data)

    @action(detail=True, methods=["post"])
    def resolve(self, request: Request, pk: str | None = None) -> Response:
        insight = services.resolve(
            insight=self.get_object(), actor=request_user(request), request=request._request
        )
        return Response(InsightSerializer(insight).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def dismiss(self, request: Request, pk: str | None = None) -> Response:
        insight = services.dismiss(
            insight=self.get_object(), actor=request_user(request), request=request._request
        )
        return Response(InsightSerializer(insight).data, status=status.HTTP_200_OK)
