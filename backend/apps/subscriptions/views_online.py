"""
Radix's merchant callbacks for subscription invoices (PLAN 6.4).

`POST /public/pay/subscription/payme` and `/public/pay/subscription/click`
— one URL each, for every customer: the tenant is the invoice NUMBER,
looked up in the metadata plane (`platform_context()`), which is exactly
what that plane is for (ADR-10). Answers are in the provider's own format
with HTTP 200, like the tuition callbacks. SaaS only — a standalone
install has no subscription.
"""

from __future__ import annotations

import logging
from typing import Any

from django.http import JsonResponse
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.core.tenancy import platform_context
from apps.online_payments import click, payme
from apps.subscriptions.online import SUBSCRIPTION, radix_merchant

logger = logging.getLogger(__name__)

__all__ = ["SubscriptionPaymeWebhookView", "SubscriptionClickWebhookView"]


class SubscriptionPaymeWebhookView(APIView):
    authentication_classes: list[Any] = []
    permission_classes = [AllowAny]

    def post(self, request: Request) -> JsonResponse:
        body = request.data if isinstance(request.data, dict) else {}
        merchant = radix_merchant("payme")
        header = request.headers.get("Authorization", "")
        if merchant is None or not payme.authorised(header, merchant.secret):
            return JsonResponse(payme.auth_error(body.get("id")))
        try:
            with platform_context():
                return JsonResponse(payme.handle(body, SUBSCRIPTION))
        except Exception:  # noqa: BLE001 — Payme gets a JSON-RPC error, we get the log
            logger.exception("Subscription Payme call failed")
            return JsonResponse(
                {"id": body.get("id"), "error": {"code": -32400, "message": {"en": "System error"}}}
            )


class SubscriptionClickWebhookView(APIView):
    authentication_classes: list[Any] = []
    permission_classes = [AllowAny]

    def post(self, request: Request) -> JsonResponse:
        data = {key: str(value) for key, value in request.data.items()}
        merchant = radix_merchant("click")
        if merchant is None:
            return JsonResponse(click._reply(data, click.SIGN_FAILED))
        try:
            with platform_context():
                return JsonResponse(click.handle(data, merchant, SUBSCRIPTION))
        except Exception:  # noqa: BLE001 — Click gets an error code, we get the log
            logger.exception("Subscription Click call failed")
            return JsonResponse(click._reply(data, click.BAD_REQUEST))
