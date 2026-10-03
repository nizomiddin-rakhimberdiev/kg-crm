"""
`POST /public/signup` and `POST /public/signup/confirm` (PLAN 6.7, ADR-28).
SaaS only — a standalone install has no trials and no public sign-up.
"""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.platform.serializers import LeadCreateSerializer
from apps.platform.services_signup import confirm_signup, request_signup

__all__ = ["SignupRequestView", "SignupConfirmView", "SignupThrottle"]


class SignupThrottle(AnonRateThrottle):
    """Every request sends an e-mail — the same limit as the lead form."""

    scope = "signup"


class SignupSerializer(LeadCreateSerializer):
    email = serializers.EmailField()


class ConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=128)
    password = serializers.CharField(max_length=128, write_only=True)


class SignupRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list[Any] = []
    throttle_classes = [SignupThrottle]

    def post(self, request: Request) -> Response:
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        data.pop("consent", None)
        data.pop("website", None)
        request_signup(data=data)
        # The same answer whatever happened: no e-mail oracle.
        return Response({"sent": True}, status=status.HTTP_202_ACCEPTED)


class SignupConfirmView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list[Any] = []
    throttle_classes = [SignupThrottle]

    def post(self, request: Request) -> Response:
        serializer = ConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            organization = confirm_signup(**serializer.validated_data)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return Response({"slug": organization.slug}, status=status.HTTP_201_CREATED)
