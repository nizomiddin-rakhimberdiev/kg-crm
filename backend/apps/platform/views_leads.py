"""Public landing va platform konsoli uchun lead endpointlari."""

from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.platform.serializers import LeadCreateSerializer
from apps.platform.services_leads import create_lead

__all__ = ["PublicLeadCreateView", "PublicPricingView", "LeadThrottle", "PublicPricingThrottle"]


class LeadThrottle(AnonRateThrottle):
    """Qimmat CAPTCHA o'rniga birinchi, server-side abuse chegarasi."""

    scope = "lead"


class PublicPricingThrottle(AnonRateThrottle):
    """Slider uchun yengil endpoint; lead form bilan bir xil qattiq limit emas."""

    scope = "public_pricing"


class PublicPricingView(APIView):
    """`GET /public/pricing?children=60` — marketing va billing uchun yagona formula."""

    permission_classes = [AllowAny]
    authentication_classes: list[Any] = []
    throttle_classes = [PublicPricingThrottle]

    def get(self, request: Request) -> Response:
        try:
            children = int(request.query_params.get("children", "50"))
        except ValueError:
            children = 0
        if not 1 <= children <= 10_000:
            return Response({"detail": "children 1 va 10000 orasida bo'lishi kerak."}, status=400)

        from decimal import Decimal

        from apps.subscriptions import pricing
        from apps.subscriptions.services import current_plan

        plan = current_plan()
        monthly = pricing.quote(plan=plan, peak_children=children)
        annual = pricing.quote(
            plan=plan,
            peak_children=children,
            months=12,
            discount_percent=Decimal("25"),
        )
        return Response(
            {
                "children": children,
                "currency": plan.currency,
                "monthly": monthly.as_dict(),
                "annual": annual.as_dict(),
                "annual_before_discount": f"{annual.base_amount + annual.overage_amount:.2f}",
                "annual_saving": f"{annual.discount_amount:.2f}",
                "plan": {
                    "included_children": plan.included_children,
                    "overage_step_children": plan.overage_step_children,
                    "overage_step_price": f"{plan.overage_step_price:.2f}",
                },
            }
        )


class PublicLeadCreateView(APIView):
    """`POST /public/leads` — faqat zayavka qabul qiladi, tenant yaratmaydi."""

    permission_classes = [AllowAny]
    authentication_classes: list[Any] = []
    throttle_classes = [LeadThrottle]

    def post(self, request: Request) -> Response:
        serializer = LeadCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        payload.pop("consent", None)
        payload.pop("website", None)
        lead, created = create_lead(data=payload)
        # PII log qilinmaydi. Response ham form uchun kerakli eng kichik
        # ma'lumot: id va "qabul qilindi" holati.
        return Response(
            {"id": str(lead.id), "status": lead.status},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
