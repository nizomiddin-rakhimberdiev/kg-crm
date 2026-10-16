"""
`GET /public/reports/<token>` — ulashilgan hisobot, faqat o'qish (13.6).

Autentifikatsiyasiz: bank yoki investor tizimga kirmaydi. Javob —
o'zgarmas nusxaning suv belgili PDF'i; jonli ma'lumot, tahrir yoki boshqa
oy yo'q. Har ochilish havolada sanaladi va audit jurnaliga yoziladi.
"""

from __future__ import annotations

import io
from typing import Any

from django.db.models import F
from django.http import FileResponse, Http404
from django.utils import timezone
from django.utils.translation import gettext
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.core.tenancy import organization_context, platform_context

__all__ = ["PublicReportView"]


def _organization(organization_id: str) -> Any:
    from apps.organizations.models import Organization

    with platform_context():
        return Organization.objects.filter(pk=organization_id).first()


class PublicReportView(APIView):
    authentication_classes: list[Any] = []
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def get(self, request: Request, token: str) -> FileResponse:
        from apps.audit import services as audit
        from apps.children.telegram import organization_from_code
        from apps.reports import pack_render, share
        from apps.reports.models import ReportReview, ReportShareLink

        organization_id = organization_from_code(token)
        organization = _organization(organization_id) if organization_id else None
        if organization is None:
            raise Http404
        with organization_context(organization.id):
            link = share.find_link(token)
            if link is None:
                raise Http404
            ReportShareLink.objects.filter(pk=link.pk).update(
                opened_count=F("opened_count") + 1, last_opened_at=timezone.now()
            )
            snapshot = link.snapshot
            review = (
                ReportReview.objects.select_related("submitted_by")
                .filter(snapshot=snapshot)
                .first()
            )
            audit.record(
                action="view",
                request=request._request,
                organization=organization,
                actor_email=f"havola: {link.label}",
                entity_type="report_share_link",
                entity_id=link.id,
                changes={"version": snapshot.version},
            )
            period = f"{snapshot.period_month:02d}.{snapshot.period_year}"
            where = f" — {snapshot.branch.name}" if snapshot.branch is not None else ""
            title = gettext("{name}{where}: oylik moliyaviy hisobot {period} (v{version})").format(
                name=organization.name, where=where, period=period, version=snapshot.version
            )
            mark = gettext("{label} · faqat oʻqish uchun · {day} · {checksum}").format(
                label=link.label,
                day=timezone.localdate().strftime("%d.%m.%Y"),
                checksum=snapshot.checksum[:12],
            )
            content = pack_render.to_pdf(
                snapshot.data,
                title=title,
                prepared_by=snapshot.created_by.full_name
                if snapshot.created_by is not None
                else "",
                submitted_by=review.submitted_by.full_name
                if review is not None and review.submitted_by is not None
                else "",
                watermark=mark,
            )
        response = FileResponse(
            io.BytesIO(content),
            filename=f"hisobot-{snapshot.period_year}-{snapshot.period_month:02d}.pdf",
            content_type="application/pdf",
        )
        response["Content-Disposition"] = response["Content-Disposition"].replace(
            "attachment", "inline"
        )
        response["Cache-Control"] = "no-store"
        response["X-Robots-Tag"] = "noindex"
        return response
