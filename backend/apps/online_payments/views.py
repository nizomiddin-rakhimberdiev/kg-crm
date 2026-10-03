"""
HTTP endpoints for online payments (PLAN 6.1, ADR-26).

Public (no login):
  POST /public/pay/payme/{organization_id}   — Payme Merchant API (JSON-RPC)
  POST /public/pay/click/{organization_id}   — Click SHOP-API (prepare/complete)
  GET  /public/pay/link/{token}              — what the parent's payment page shows

Staff:
  POST /online-payments/links                — link for one invoice (payments.create)
  GET  /online-payments/credentials          — which providers are set up (settings.read)
  PUT  /online-payments/credentials/{prov}   — save keys (settings.update)
  DELETE /online-payments/credentials/{prov} — switch a provider off (settings.delete)

The two webhooks answer in the PROVIDER's exact format (`JsonResponse`),
not in our API envelope, and always with HTTP 200 — that is what the
providers expect. The tenant comes from the URL; everything runs inside
that organization's context, so another kindergarten's invoice is simply
"not found" (RLS), never reachable.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from django.conf import settings
from django.http import Http404, JsonResponse
from django.utils import timezone
from django.utils.translation import gettext
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.audit import services as audit
from apps.core.exceptions import BusinessRuleViolation
from apps.core.permissions import HasModulePermission
from apps.core.tenancy import organization_context, platform_context
from apps.core.typing import request_user
from apps.online_payments import click, payme, services
from apps.online_payments.models import MerchantCredential, PaymentLink, Provider
from apps.online_payments.serializers import CreateLinkSerializer, CredentialSerializer
from apps.subscriptions.permissions import SubscriptionWriteGate

logger = logging.getLogger(__name__)

__all__ = [
    "PaymeWebhookView",
    "ClickWebhookView",
    "PublicPayLinkView",
    "PaymentLinkCreateView",
    "MerchantCredentialListView",
    "MerchantCredentialView",
]


def _organization(organization_id: Any) -> Any:
    from apps.organizations.models import Organization

    with platform_context():
        return Organization.objects.filter(pk=organization_id, is_active=True).first()


def _credential(provider: str) -> MerchantCredential | None:
    return MerchantCredential.objects.filter(provider=provider, is_active=True).first()


def _webhook_url(organization_id: Any, provider: str) -> str:
    base = str(getattr(settings, "FRONTEND_URL", "")).rstrip("/")
    return f"{base}/api/v1/public/pay/{provider}/{organization_id}"


# --- Provider webhooks ---


class PaymeWebhookView(APIView):
    authentication_classes: list[Any] = []
    permission_classes = [AllowAny]

    def post(self, request: Request, organization_id: uuid.UUID) -> JsonResponse:
        body = request.data if isinstance(request.data, dict) else {}
        organization = _organization(organization_id)
        if organization is None:
            return JsonResponse(payme.auth_error(body.get("id")))
        with organization_context(organization.id):
            credential = _credential(Provider.PAYME)
            header = request.headers.get("Authorization", "")
            if credential is None or not payme.authorised(header, credential):
                return JsonResponse(payme.auth_error(body.get("id")))
            try:
                return JsonResponse(payme.handle(body))
            except Exception:  # noqa: BLE001 — Payme gets a JSON-RPC error, we get the log
                logger.exception("Payme call failed: org=%s", organization.id)
                return JsonResponse(
                    {
                        "id": body.get("id"),
                        "error": {"code": -32400, "message": {"en": "System error"}},
                    }
                )


class ClickWebhookView(APIView):
    authentication_classes: list[Any] = []
    permission_classes = [AllowAny]

    def post(self, request: Request, organization_id: uuid.UUID) -> JsonResponse:
        data = {key: str(value) for key, value in request.data.items()}
        organization = _organization(organization_id)
        if organization is None:
            return JsonResponse(click._reply(data, click.SIGN_FAILED))
        with organization_context(organization.id):
            credential = _credential(Provider.CLICK)
            if credential is None:
                return JsonResponse(click._reply(data, click.SIGN_FAILED))
            try:
                return JsonResponse(click.handle(data, credential))
            except Exception:  # noqa: BLE001 — Click gets an error code, we get the log
                logger.exception("Click call failed: org=%s", organization.id)
                return JsonResponse(click._reply(data, click.BAD_REQUEST))


# --- Parent's payment page ---


class PublicPayLinkView(APIView):
    """
    What the parent sees: kindergarten, child's first name, invoice and
    the provider buttons. Deliberately little personal data — the link
    may be forwarded into a family chat.
    """

    authentication_classes: list[Any] = []
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def get(self, request: Request, token: str) -> Response:
        organization_id = services.organization_from_token(token)
        if organization_id is None:
            raise Http404
        organization = _organization(organization_id)
        if organization is None:
            raise Http404
        with organization_context(organization.id):
            link = (
                PaymentLink.objects.select_related("invoice__child")
                .filter(token=token, is_active=True)
                .first()
            )
            if link is None or link.expires_at < timezone.now():
                raise Http404
            invoice = link.invoice
            payable = services.payable_amount(invoice)
            providers = (
                services.checkout_urls(
                    invoice=invoice, amount=payable, return_url=services.public_return_url(link)
                )
                if payable is not None
                else {}
            )
            child = invoice.child
            return Response(
                {
                    "kindergarten": organization.name,
                    "logo_url": organization.logo.url if organization.logo else None,
                    "child": f"{child.first_name} {child.last_name[:1]}.".strip(),
                    "invoice": invoice.number,
                    "period": f"{invoice.period_month:02d}.{invoice.period_year}",
                    "amount_due": f"{invoice.amount_due:.2f}",
                    "payable": f"{payable:.2f}" if payable is not None else "0.00",
                    "is_paid": payable is None and invoice.amount_paid >= invoice.amount_due,
                    "providers": providers,
                }
            )


# --- Staff ---


class PaymentLinkCreateView(APIView):
    permission_classes = [HasModulePermission, SubscriptionWriteGate]
    permission_module = "payments"

    def post(self, request: Request) -> Response:
        from apps.finance.models import Invoice

        serializer = CreateLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invoice = (
            Invoice.objects.select_related("child")
            .filter(pk=serializer.validated_data["invoice_id"])
            .first()
        )
        if invoice is None:
            raise NotFound(gettext("Hisob-faktura topilmadi."))
        if services.payable_amount(invoice) is None:
            raise BusinessRuleViolation(gettext("Bu hisob-fakturada toʻlanadigan qoldiq yoʻq."))
        if not services.active_credentials():
            raise BusinessRuleViolation(
                gettext("Onlayn toʻlov ulanmagan: Sozlamalarda Payme yoki Click kalitini kiriting.")
            )
        link = services.create_link(invoice=invoice, created_by=request_user(request))
        return Response(
            {"url": services.public_url(link), "expires_at": link.expires_at.isoformat()},
            status=201,
        )


class MerchantCredentialListView(APIView):
    permission_classes = [HasModulePermission]
    permission_module = "settings"

    def get(self, request: Request) -> Response:
        organization = request_user(request).organization
        credentials = services.active_credentials()
        return Response(
            [
                _describe(provider, credentials.get(provider), getattr(organization, "id", ""))
                for provider in Provider.values
            ]
        )


def _describe(provider: str, credential: MerchantCredential | None, organization_id: Any) -> dict:
    """A provider's state for the settings screen — the secret only as its last 4 characters."""
    return {
        "provider": provider,
        "configured": credential is not None,
        "merchant_id": credential.merchant_id if credential else "",
        "service_id": credential.service_id if credential else "",
        "secret_hint": credential.secret_hint if credential else "",
        "sandbox": credential.sandbox if credential else False,
        # Pasted into the provider's merchant cabinet.
        "webhook_url": _webhook_url(organization_id, provider),
    }


class MerchantCredentialView(APIView):
    permission_classes = [HasModulePermission, SubscriptionWriteGate]
    permission_module = "settings"

    def _provider(self, provider: str) -> str:
        if provider not in Provider.values:
            raise NotFound
        return provider

    def put(self, request: Request, provider: str) -> Response:
        from django.core.exceptions import ImproperlyConfigured

        provider = self._provider(provider)
        serializer = CredentialSerializer(data=request.data, context={"provider": provider})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request_user(request)
        try:
            credential = services.save_credential(
                organization=user.organization,
                provider=provider,
                merchant_id=data["merchant_id"],
                secret=data["secret"],
                service_id=data.get("service_id", ""),
                sandbox=data.get("sandbox", False),
            )
        except ImproperlyConfigured as exc:
            logger.error("Merchant key storage is not configured: %s", exc)
            raise BusinessRuleViolation(
                gettext(
                    "Server sozlanmagan: kalitni saqlab boʻlmaydi. Administratorga murojaat qiling."
                )
            ) from exc
        audit.record(
            action="update",
            request=request._request,
            actor=user,
            entity_type="merchant_credential",
            entity_id=credential.id,
            # The secret itself never reaches the audit log.
            changes={"provider": provider, "merchant_id": credential.merchant_id},
        )
        return Response({"provider": provider, "secret_hint": credential.secret_hint})

    def delete(self, request: Request, provider: str) -> Response:
        provider = self._provider(provider)
        MerchantCredential.objects.filter(provider=provider, is_active=True).update(is_active=False)
        audit.record(
            action="delete",
            request=request._request,
            actor=request_user(request),
            entity_type="merchant_credential",
            changes={"provider": provider},
        )
        return Response(status=204)
