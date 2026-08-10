"""
Tashkilot profili endpointi (docs/04 §16).

Bu **singleton** resurs, kolleksiya emas: mijozda faqat bitta tashkilot bor —
o'ziniki. Shuning uchun `APIView` (ViewSet emas) va URL'da ID yo'q. Obyekt
ID'dan emas, tokendan olinadi — ya'ni noto'g'ri ID yozib boshqa tashkilotga
tegish imkoniyati umuman yo'q.
"""

from __future__ import annotations

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit import services as audit
from apps.core.permissions import HasModulePermission
from apps.core.tenancy import platform_context
from apps.core.typing import request_user
from apps.organizations.models import Organization
from apps.organizations.serializers import OrganizationSerializer
from apps.subscriptions.permissions import SubscriptionWriteGate

__all__ = ["OrganizationView"]


class OrganizationView(APIView):
    """
    `GET/PATCH /organization` — bog'chaning o'z ma'lumotlari.

    Ruxsat `settings` moduli bo'yicha (docs/02 §11.2): tashkilot egasida
    to'liq, direktorda faqat o'qish. Joylashuvi to'g'ri — bog'cha nomi va
    rekvizitlari kundalik operatsiya emas, sozlama.
    """

    permission_classes = [HasModulePermission, SubscriptionWriteGate]
    permission_module = "settings"

    def _organization(self, request: Request) -> Organization:
        organization = request_user(request).organization
        assert organization is not None  # IsAuthenticated + tenant scoping kafolati
        return organization

    def get(self, request: Request) -> Response:
        return Response(OrganizationSerializer(self._organization(request)).data)

    def patch(self, request: Request) -> Response:
        organization = self._organization(request)
        serializer = OrganizationSerializer(organization, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # `organization` — RLS'da metama'lumot jadvali, unga yozish uchun
        # platforma rejimi kerak (docs/03 §6.3). Doira shu bitta saqlash
        # bilan cheklangan, obyekt esa allaqachon tokendan olingan.
        with platform_context():
            serializer.save()

        audit.record(
            action="update",
            request=request._request,
            actor=request.user,
            entity_type="organization",
            entity_id=organization.id,
            changes={"fields": sorted(serializer.validated_data)},
        )
        return Response(serializer.data)
