"""
Hisobot va dashboard endpointlari (docs/04 §14).

Hammasi faqat o'qish. Eksport esa yozadi — lekin u ham hisobotning o'zini
o'zgartirmaydi, faqat ish yozuvini yaratadi.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from django.db import transaction
from django.http import FileResponse, Http404
from django.utils import timezone
from django.utils.translation import get_language, gettext, gettext_lazy
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.core.exceptions import BusinessRuleViolation
from apps.core.permissions import HasModulePermission, has_permission_code
from apps.core.typing import request_user
from apps.reports import selectors, services
from apps.reports.models import REPORT_TYPES, ExportStatus, ReportExport
from apps.reports.serializers import ExportRequestSerializer, ReportExportSerializer
from apps.reports.tasks import generate_export
from apps.subscriptions.permissions import SubscriptionWriteGate

__all__ = ["DashboardViewSet", "ReportViewSet"]


def _parse_date(value: Any, fallback: date) -> date:
    if not value:
        return fallback
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise BusinessRuleViolation(
            gettext("Sana formati notoʻgʻri: {value}").format(value=value)
        ) from exc


def _parse_int(value: Any, fallback: int, *, low: int, high: int) -> int:
    if value in (None, ""):
        return fallback
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise BusinessRuleViolation(
            gettext("Butun son kutilgan: {value}").format(value=value)
        ) from exc
    if not low <= parsed <= high:
        raise BusinessRuleViolation(
            gettext("Qiymat {low}–{high} oraligʻida boʻlishi kerak: {parsed}").format(
                low=low, high=high, parsed=parsed
            )
        )
    return parsed


class _ScopeMixin:
    """
    So'rovdagi davr va filialni o'qiydi.

    Filial doirasi ROLGA bog'liq — Dashboard bilan bir xil (docs/02 §11.3):
    ega `?branch=` bilan bitta filialni yoki hammasini ko'radi, filialga
    bog'langan xodim esa FAQAT o'z filialini, so'rovda nima yozilganidan
    qat'i nazar. Avval parametr bo'lmasa butun tashkilot qaytardi — ya'ni
    bitta filial menejeri boshqa filialning tushumini ham ko'rardi.

    Begona tashkilotning filial ID'si baribir bo'sh natija beradi: so'rov
    tashkilot bilan cheklangan.
    """

    @staticmethod
    def branch_for(request: Request, requested: Any = None) -> Any:
        user = request_user(request)
        if user.is_org_owner:
            return requested or None
        return user.branch_id

    def scope(self, request: Request) -> dict[str, Any]:
        today = timezone.localdate()
        default_from = today.replace(day=1) - timedelta(days=180)
        return {
            "organization_id": request_user(request).organization_id,
            "date_from": _parse_date(request.query_params.get("from"), default_from),
            "date_to": _parse_date(request.query_params.get("to"), today),
            "branch_id": self.branch_for(request, request.query_params.get("branch")),
        }

    def period_scope(self, request: Request) -> dict[str, Any]:
        """
        `scope()` + `group_by` — davr kesimli hisobotlar uchun
        (docs/04 §14.2). Qiymat selektorda tekshiriladi: noto'g'ri
        kesim `422` beradi, jimgina oylikka tushib ketmaydi.
        """
        return {
            **self.scope(request),
            "group_by": request.query_params.get("group_by") or selectors.DEFAULT_GROUP_BY,
        }


class DashboardViewSet(_ScopeMixin, viewsets.ViewSet):
    """`GET /dashboard` — bitta ekranga sig'adigan KPI to'plami."""

    permission_classes = [HasModulePermission, SubscriptionWriteGate]
    permission_module = "dashboard"

    def list(self, request: Request) -> Response:
        user = request_user(request)
        # Filial doirasi ROLGA bog'liq: Org Owner butun tashkilotni
        # ko'radi, qolganlar o'z filialini (docs/02 §11.3).
        branch_id = request.query_params.get("branch") or (
            user.branch_id if not user.is_org_owner else None
        )
        # Har bir bo'lak o'z ruxsatini talab qiladi (docs/02 §11.2).
        # Ro'yxatdagi bittasi yetarli bo'lgan bo'laklar ham bor
        # ("finance": to'lov YOKI qarzdorlik), `cash` esa uchalasini
        # ham talab qiladi — u uchtasini bitta raqamga yig'adi.
        sections = frozenset(
            name
            for name, codes in services.DASHBOARD_SECTIONS.items()
            if (all if name == "cash" else any)(has_permission_code(user, code) for code in codes)
        )
        return Response(
            services.dashboard_kpis(
                organization_id=user.organization_id,
                branch_id=branch_id,
                sections=sections,
            )
        )


# Har bir hisobot O'ZI HISOBOT BERADIGAN modul ruxsatini ham talab qiladi.
#
# `reports.read` ning o'zi yetarli emas edi: docs/02 §11.2 jadvalida Kassir
# uchun "R (finance only)", Davomat menejeri uchun "R (attendance only)" deb
# yozilgan, kodda esa bitta `reports.read` HAMMASINI ochib yuborardi — ya'ni
# tarbiyachi bog'chaning tushumini va foyda-zararini (ichida oylik maosh)
# o'qiy olardi. Bu jadvalga ham, "No finance, payroll, or settings" degan
# rol ta'rifiga ham zid.
#
# `profit-loss` oylik maoshni o'z ichiga oladi, shuning uchun u eng qattiq
# komponent — `payroll.read` — bilan qo'riqlanadi.
REPORT_SCOPE: dict[str, str] = {
    "staff-attendance": "attendance.read",
    "revenue": "payments.read",
    "debtors": "debtors.read",
    "expenses": "expenses.read",
    "payroll": "payroll.read",
    "profit-loss": "payroll.read",
    "attendance": "attendance.read",
    # Imtiyozlar — pul (Bosqich 12.2): kassirga emas, to'lovlarni ko'radiganga.
    "benefits": "payments.read",
    # Oylik yig'ma, oyni yopish va eski jadval (Bosqich 12.6).
    "monthly": "payments.read",
    # Foyda-zarar, pul oqimi, holat (Bosqich 13.2d): oylik jami ham bor,
    # shuning uchun profit-loss kabi `payroll.read`.
    "finance": "payroll.read",
    # Oylik hisobot paketi (Bosqich 13.5): foyda, oylik jami — `payroll.read`.
    "pack": "payroll.read",
}

# View action nomi → hisobot turi (`REPORT_SCOPE` kaliti).
_ACTION_REPORT: dict[str, str] = {
    "revenue": "revenue",
    "debtors": "debtors",
    "expenses": "expenses",
    "payroll": "payroll",
    "profit_loss": "profit-loss",
    "attendance": "attendance",
    "benefits": "benefits",
    "monthly_summary": "monthly",
    "monthly_close": "monthly",
    "pnl": "finance",
    "pack": "pack",
    "pack_snapshot": "pack",
    "pack_versions": "pack",
    "pack_diff": "pack",
    "pack_source": "pack",
    "pack_pdf": "pack",
    "pack_xlsx": "pack",
    "cash_flow": "finance",
    "position": "finance",
    "completeness": "monthly",
    "home": "finance",
    "daily": "monthly",
    "checks": "monthly",
    "attention": "monthly",
}


class HasReportScope(permissions.BasePermission):
    """`reports.read` ustiga hisobot mavzusining ruxsatini tekshiradi."""

    message = gettext_lazy("Bu amalga ruxsat yoʻq.")

    def has_permission(self, request: Request, view: Any) -> bool:
        action = getattr(view, "action", None)
        report = _ACTION_REPORT.get(action or "")
        if report is None and action == "export":
            # `POST /reports/{type}/export` — tur manzilda.
            report = view.kwargs.get("pk")
        if report is None:
            return True
        required = REPORT_SCOPE.get(report)
        return required is None or has_permission_code(request_user(request), required)


class ReportViewSet(_ScopeMixin, viewsets.ViewSet):
    """`/reports/*` — agregatsiyalar va eksport."""

    permission_classes = [HasModulePermission, HasReportScope, SubscriptionWriteGate]
    permission_module = "reports"
    permission_action_map = {
        "export": "export",
        "exports": "read",
        "export_detail": "read",
        "download": "read",
        # Oyni yopish — egasi va direktor (`reports.approve`); kassirda
        # `reports` umuman yo'q.
        "monthly_close": "approve",
        # O'zgarmas nusxa — topshirish/tasdiqlash (egasi, direktor).
        "pack_snapshot": "approve",
    }
    lookup_value_regex = "|".join(REPORT_TYPES)
    # `ScopedRateThrottle` shu nomdagi tezlikni qidiradi. U faqat
    # `export` action'iga ulangan (pastda), shuning uchun o'qish
    # endpointlariga ta'sir qilmaydi.
    throttle_scope = "export"

    @action(detail=False)
    def revenue(self, request: Request) -> Response:
        return Response(selectors.revenue_report(**self.period_scope(request)))

    @action(detail=False)
    def expenses(self, request: Request) -> Response:
        return Response(selectors.expense_report(**self.period_scope(request)))

    @action(detail=False)
    def benefits(self, request: Request) -> Response:
        """`GET /reports/benefits?from=&to=` — imtiyozlar: kim, kimga, qancha, nega."""
        return Response(selectors.benefits_report(**self.scope(request)))

    def _year_month(self, request: Request) -> tuple[int, int]:
        today = timezone.localdate()
        return (
            _parse_int(request.query_params.get("year"), today.year, low=2000, high=2100),
            _parse_int(request.query_params.get("month"), today.month, low=1, high=12),
        )

    @action(detail=False)
    def pnl(self, request: Request) -> Response:
        """`GET /reports/pnl?year=&month=` — foyda-zarar, tegishli oy bo'yicha (13.2d)."""
        from apps.reports import money

        year, month = self._year_month(request)
        return Response(
            money.profit_and_loss(
                organization_id=request_user(request).organization_id,
                year=year,
                month=month,
                branch_id=self.branch_for(request, request.query_params.get("branch")),
            )
        )

    @action(detail=False, url_path="cash-flow")
    def cash_flow(self, request: Request) -> Response:
        """`GET /reports/cash-flow?year=&month=` — pul qachon harakatlangan (13.2d)."""
        from apps.reports import money

        year, month = self._year_month(request)
        return Response(
            money.cash_flow(
                organization_id=request_user(request).organization_id,
                year=year,
                month=month,
                branch_id=self.branch_for(request, request.query_params.get("branch")),
            )
        )

    # --- Oylik hisobot paketi (Bosqich 13.5) ---

    def _pack_scope(self, request: Request) -> tuple[Any, int, int, Any]:
        year, month = self._year_month(request)
        branch = self.branch_for(
            request, request.query_params.get("branch") or request.data.get("branch")
        )
        return request_user(request).organization_id, year, month, branch

    def _snapshots(self, organization_id: Any, year: int, month: int, branch: Any) -> Any:
        from apps.reports.models import ReportSnapshot

        return ReportSnapshot.objects.filter(
            period_year=year, period_month=month, branch_id=branch
        ).order_by("-version")

    @action(detail=False, url_path="pack")
    def pack(self, request: Request) -> Response:
        """`GET /reports/pack?year=&month=` — 16 bo'lim; ochilishi jurnalda."""
        from apps.audit import services as audit
        from apps.reports import pack

        organization_id, year, month, branch = self._pack_scope(request)
        data = pack.build(organization_id=organization_id, year=year, month=month, branch_id=branch)
        latest = self._snapshots(organization_id, year, month, branch).first()
        audit.record(
            action="view",
            request=request._request,
            actor=request_user(request),
            entity_type="report_pack",
            changes={"period": f"{year}-{month:02d}", "branch": str(branch) if branch else None},
        )
        return Response(
            {
                **data,
                "checksum": pack.checksum(data),
                "latest_version": latest.version if latest else None,
                "changed_since_snapshot": bool(latest and latest.checksum != pack.checksum(data)),
            }
        )

    @action(detail=False, methods=["post"], url_path="pack/snapshot")
    def pack_snapshot(self, request: Request) -> Response:
        """
        `POST /reports/pack/snapshot {year, month}` — o'zgarmas nusxa. Ma'lumot
        o'zgarmagan bo'lsa yangi versiya yaratilmaydi.
        """
        from django.db import transaction

        from apps.audit import services as audit
        from apps.reports import pack
        from apps.reports.models import ReportSnapshot

        if not request.data.get("year") or not request.data.get("month"):
            raise BusinessRuleViolation(gettext("Yil va oyni koʻrsating."))
        user = request_user(request)
        year = _parse_int(request.data.get("year"), 0, low=2000, high=2100)
        month = _parse_int(request.data.get("month"), 0, low=1, high=12)
        branch = self.branch_for(request, request.data.get("branch"))
        data = pack.build(
            organization_id=user.organization_id, year=year, month=month, branch_id=branch
        )
        digest = pack.checksum(data)
        with transaction.atomic():
            latest = (
                self._snapshots(user.organization_id, year, month, branch)
                .select_for_update()
                .first()
            )
            if latest is not None and latest.checksum == digest:
                snapshot = latest
            else:
                snapshot = ReportSnapshot.objects.create(
                    organization=user.organization,
                    branch_id=branch,
                    period_year=year,
                    period_month=month,
                    version=(latest.version + 1) if latest else 1,
                    data=data,
                    checksum=digest,
                    created_by=user,
                )
                audit.record(
                    action="create",
                    request=request._request,
                    actor=user,
                    entity_type="report_snapshot",
                    entity_id=snapshot.id,
                    changes={"period": f"{year}-{month:02d}", "version": snapshot.version},
                )
        return Response(
            {"id": str(snapshot.id), "version": snapshot.version, "checksum": snapshot.checksum},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, url_path="pack/versions")
    def pack_versions(self, request: Request) -> Response:
        organization_id, year, month, branch = self._pack_scope(request)
        return Response(
            [
                {
                    "version": row.version,
                    "checksum": row.checksum,
                    "created_at": row.created_at.isoformat(),
                    "created_by": row.created_by.full_name if row.created_by_id else "",
                }
                for row in self._snapshots(organization_id, year, month, branch).select_related(
                    "created_by"
                )
            ]
        )

    @action(detail=False, url_path="pack/diff")
    def pack_diff(self, request: Request) -> Response:
        """`GET /reports/pack/diff?from=1&to=2` (`to` bo'lmasa — jonli paket bilan)."""
        from apps.reports import pack

        organization_id, year, month, branch = self._pack_scope(request)
        rows = {row.version: row for row in self._snapshots(organization_id, year, month, branch)}
        old = rows.get(_parse_int(request.query_params.get("from"), 0, low=0, high=100000))
        if old is None:
            raise Http404
        target = request.query_params.get("to")
        if target:
            new_row = rows.get(_parse_int(target, 0, low=0, high=100000))
            if new_row is None:
                raise Http404
            new = new_row.data
        else:
            new = pack.build(
                organization_id=organization_id, year=year, month=month, branch_id=branch
            )
        return Response({"changes": pack.diff(old.data, new)})

    @action(detail=False, url_path="pack/source")
    def pack_source(self, request: Request) -> Response:
        """`GET /reports/pack/source?key=allocations:collected` — raqam manbasi (test 19)."""
        from apps.reports import pack

        organization_id, year, month, branch = self._pack_scope(request)
        rows = pack.source_rows(
            organization_id=organization_id,
            year=year,
            month=month,
            key=str(request.query_params.get("key") or ""),
            branch_id=branch,
        )
        return Response({"rows": rows})

    def _pack_file(self, request: Request, kind: str) -> FileResponse:
        import io

        from apps.audit import services as audit
        from apps.reports import pack, pack_render

        organization_id, year, month, branch = self._pack_scope(request)
        data = pack.build(organization_id=organization_id, year=year, month=month, branch_id=branch)
        title = gettext("Oylik moliyaviy hisobot — {period}").format(period=f"{month:02d}.{year}")
        audit.record(
            action="view",
            request=request._request,
            actor=request_user(request),
            entity_type="report_pack",
            changes={"period": f"{year}-{month:02d}", "format": kind},
        )
        if kind == "pdf":
            content = pack_render.to_pdf(
                data, title=title, prepared_by=request_user(request).full_name
            )
            return FileResponse(
                io.BytesIO(content),
                filename=f"hisobot-{year}-{month:02d}.pdf",
                content_type="application/pdf",
            )
        raw = {
            gettext("Yigʻilgan pul"): pack.source_rows(
                organization_id=organization_id,
                year=year,
                month=month,
                key="allocations:collected",
                branch_id=branch,
            ),
            gettext("Fakturalar"): pack.source_rows(
                organization_id=organization_id,
                year=year,
                month=month,
                key="invoices:due",
                branch_id=branch,
            ),
        }
        return FileResponse(
            io.BytesIO(pack_render.to_xlsx(data, raw=raw)),
            filename=f"hisobot-{year}-{month:02d}.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    @action(detail=False, url_path="pack/pdf")
    def pack_pdf(self, request: Request) -> FileResponse:
        return self._pack_file(request, "pdf")

    @action(detail=False, url_path="pack/xlsx")
    def pack_xlsx(self, request: Request) -> FileResponse:
        return self._pack_file(request, "xlsx")

    @action(detail=False)
    def checks(self, request: Request) -> Response:
        """`GET /reports/checks?year=&month=` — nazorat tekshiruvlari (13.4)."""
        from apps.intelligence import control

        year, month = self._year_month(request)
        return Response(
            control.checks(
                organization_id=request_user(request).organization_id,
                year=year,
                month=month,
                branch_id=self.branch_for(request, request.query_params.get("branch")),
            )
        )

    @action(detail=False)
    def attention(self, request: Request) -> Response:
        """`GET /reports/attention?year=&month=` — "Diqqat" ro'yxati (13.4)."""
        from apps.intelligence import control

        year, month = self._year_month(request)
        items = control.attention(
            organization_id=request_user(request).organization_id,
            year=year,
            month=month,
            branch_id=self.branch_for(request, request.query_params.get("branch")),
        )
        return Response({"items": items, "count": len(items)})

    @action(detail=False)
    def home(self, request: Request) -> Response:
        """`GET /reports/home` — "Bog'cha moliyasi bugun": oltita savol (13.4)."""
        from apps.reports import home

        return Response(
            home.home(
                organization_id=request_user(request).organization_id,
                day=_parse_date(request.query_params.get("date"), timezone.localdate()),
                branch_id=self.branch_for(request, request.query_params.get("branch")),
            )
        )

    @action(detail=False)
    def daily(self, request: Request) -> Response:
        """`GET /reports/daily?date=` — kunlik ko'rinish (13.4)."""
        from apps.reports import home

        return Response(
            home.daily(
                organization_id=request_user(request).organization_id,
                day=_parse_date(request.query_params.get("date"), timezone.localdate()),
                branch_id=self.branch_for(request, request.query_params.get("branch")),
            )
        )

    @action(detail=False)
    def completeness(self, request: Request) -> Response:
        """`GET /reports/completeness?year=&month=` — ma'lumot to'liqligi (13.3e)."""
        from apps.reports import money

        year, month = self._year_month(request)
        return Response(
            money.data_completeness(
                organization_id=request_user(request).organization_id,
                year=year,
                month=month,
                branch_id=self.branch_for(request, request.query_params.get("branch")),
            )
        )

    @action(detail=False)
    def position(self, request: Request) -> Response:
        """`GET /reports/position?as_of=YYYY-MM-DD` — talablar va majburiyatlar (13.2d)."""
        from apps.reports import money

        return Response(
            money.position(
                organization_id=request_user(request).organization_id,
                as_of=_parse_date(request.query_params.get("as_of"), timezone.localdate()),
                branch_id=self.branch_for(request, request.query_params.get("branch")),
            )
        )

    @action(detail=False, url_path="monthly-summary")
    def monthly_summary(self, request: Request) -> Response:
        """`GET /reports/monthly-summary?year=&month=` — oyning yig'masi (Bosqich 12.6)."""
        from apps.finance.selectors import monthly_summary

        today = timezone.localdate()
        return Response(
            monthly_summary(
                organization_id=request_user(request).organization_id,
                year=_parse_int(request.query_params.get("year"), today.year, low=2000, high=2100),
                month=_parse_int(request.query_params.get("month"), today.month, low=1, high=12),
                branch_id=self.branch_for(request, request.query_params.get("branch")),
            )
        )

    @action(detail=False, methods=["post"], url_path="monthly-summary/close")
    def monthly_close(self, request: Request) -> Response:
        """
        `POST /reports/monthly-summary/close {year, month, branch_id?}` — oyni
        yopish (Bosqich 12.6). Faqat tugagan va tengligi yashil oy, bir marta.
        """
        from apps.audit import services as audit
        from apps.branches.models import Branch
        from apps.finance.services import close_month

        user = request_user(request)
        if not request.data.get("year") or not request.data.get("month"):
            raise BusinessRuleViolation(gettext("Yil va oyni koʻrsating."))
        branch_id = self.branch_for(request, request.data.get("branch_id"))
        if branch_id:
            branch = Branch.objects.filter(pk=branch_id).first()
            if branch is None:
                raise Http404
        else:
            branches = list(Branch.objects.filter(is_active=True)[:2])
            if len(branches) != 1:
                raise BusinessRuleViolation(
                    gettext("Qaysi filial oyini yopish — filialni tanlang.")
                )
            branch = branches[0]
        record = close_month(
            branch=branch,
            year=_parse_int(request.data.get("year"), 0, low=2000, high=2100),
            month=_parse_int(request.data.get("month"), 0, low=1, high=12),
            closed_by=user,
        )
        audit.record(
            action="approve",
            request=request._request,
            actor=user,
            entity_type="month_close",
            entity_id=record.id,
            changes={"period": f"{record.period_year}-{record.period_month:02d}"},
        )
        return Response(
            {"id": str(record.id), "period": f"{record.period_year}-{record.period_month:02d}"},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, url_path="profit-loss")
    def profit_loss(self, request: Request) -> Response:
        return Response(selectors.profit_loss(**self.period_scope(request)))

    @action(detail=False)
    def debtors(self, request: Request) -> Response:
        scope = self.scope(request)
        return Response(
            selectors.debtor_report(
                organization_id=scope["organization_id"], branch_id=scope["branch_id"]
            )
        )

    @action(detail=False)
    def payroll(self, request: Request) -> Response:
        today = timezone.localdate()
        scope = self.scope(request)
        return Response(
            selectors.payroll_report(
                organization_id=scope["organization_id"],
                year=_parse_int(request.query_params.get("year"), today.year, low=2000, high=2100),
                branch_id=scope["branch_id"],
            )
        )

    @action(detail=False)
    def attendance(self, request: Request) -> Response:
        today = timezone.localdate()
        scope = self.scope(request)
        return Response(
            selectors.attendance_report(
                organization_id=scope["organization_id"],
                year=_parse_int(request.query_params.get("year"), today.year, low=2000, high=2100),
                month=_parse_int(request.query_params.get("month"), today.month, low=1, high=12),
                group_id=request.query_params.get("group") or None,
            )
        )

    # --- Eksport ---

    @action(detail=True, methods=["post"], throttle_classes=[ScopedRateThrottle])
    def export(self, request: Request, pk: str | None = None) -> Response:
        """
        `POST /reports/{type}/export` — eksportni navbatga qo'yadi.

        Javob darhol qaytadi: katta hisobotni so'rov ichida tayyorlash
        brauzerni kutdirib qo'yardi va vaqt tugashi bilan uzilardi.
        """
        serializer = ExportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request_user(request)

        # So'rov tilini parametrlarga yozamiz: fayl keyinroq, Celery
        # ishchisida yig'iladi va u yerda `Accept-Language` yo'q — ustun
        # sarlavhalari foydalanuvchi ko'rgan tilda bo'lishi kerak.
        params = {**serializer.validated_data.get("params", {}), "language": get_language()}
        # Filial doirasi eksportda ham — o'qishdagi bilan bir xil (yuqorida).
        branch_id = self.branch_for(request, params.get("branch_id"))
        params["branch_id"] = str(branch_id) if branch_id else None
        export = ReportExport.objects.create(
            organization=user.organization,
            report_type=pk,
            params=params,
            requested_by=user,
        )
        # `on_commit` — `delay()` EMAS, to'g'ridan-to'g'ri emas.
        #
        # `ATOMIC_REQUESTS` yoqilmagan bo'lsa ham, bu view yuqoridagi
        # qatlamlarda tranzaksiya ichiga tushishi mumkin (masalan test,
        # yoki kelajakdagi `atomic` blok). U holda vazifa qatordan
        # OLDIN navbatga tushadi va ishchi hali mavjud bo'lmagan
        # `export.id` ni qidiradi — natija "eksport topilmadi" degan
        # jimgina nosozlik bo'lardi.
        #
        # `on_commit` vazifani commit'dan KEYIN yuboradi; tranzaksiya
        # bo'lmasa esa darhol chaqiradi, ya'ni oddiy holatda xatti-harakat
        # o'zgarmaydi.
        export_id, organization_id = str(export.id), str(user.organization_id)
        transaction.on_commit(lambda: generate_export.delay(export_id, organization_id))
        return Response(ReportExportSerializer(export).data, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=["get"])
    def exports(self, request: Request) -> Response:
        """Faqat foydalanuvchi ko'rishga haqli mavzudagi eksportlar."""
        allowed = [
            report
            for report, code in REPORT_SCOPE.items()
            if has_permission_code(request_user(request), code)
        ]
        queryset = (
            ReportExport.objects.filter(report_type__in=allowed)
            .select_related("requested_by")
            .order_by("-created_at")[:50]
        )
        return Response(ReportExportSerializer(queryset, many=True).data)

    @action(detail=False, methods=["get"], url_path=r"exports/(?P<job_id>[0-9a-f-]{36})")
    def export_detail(self, request: Request, job_id: str = "") -> Response:
        return Response(ReportExportSerializer(self._checked_export(request, job_id)).data)

    @action(
        detail=False,
        methods=["get"],
        url_path=r"exports/(?P<job_id>[0-9a-f-]{36})/download",
    )
    def download(self, request: Request, job_id: str = "") -> FileResponse:
        """
        Faylni **shu endpoint** beradi, `/media/` havolasi emas.

        Statik media URL'i autentifikatsiyani ham, tashkilot chegarasini
        ham bilmaydi: havolani topgan har kim boshqa bog'chaning moliyaviy
        hisobotini yuklab olardi. Bu yerda esa `ReportExport.objects`
        tenant bilan cheklangan, ya'ni begona ish oddiygina `404`.
        """
        export = self._checked_export(request, job_id)
        if export.status != ExportStatus.READY or not export.file:
            raise BusinessRuleViolation(gettext("Eksport hali tayyor emas."))
        filename = export.file.name.rsplit("/", 1)[-1]
        return FileResponse(
            export.file.open("rb"),
            as_attachment=True,
            filename=filename,
            # Eski eksportlar `.csv` bo'lib qolgan — turni kengaytmadan
            # aniqlaymiz, aks holda Excel faylni CSV deb ochib buzardi.
            content_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                if filename.endswith(".xlsx")
                else "text/csv"
            ),
        )

    def _get_export(self, job_id: str) -> ReportExport:
        export = ReportExport.objects.filter(pk=job_id).first()
        if export is None:
            raise Http404
        return export

    def _checked_export(self, request: Request, job_id: str) -> ReportExport:
        """
        Tayyor eksport ham O'Z MAVZUSI bo'yicha qo'riqlanadi.

        Aks holda `reports.read` ga ega har kim boshqa rol yaratgan oylik
        maosh faylini yuklab olardi — ya'ni eksport ruxsat matritsasidan
        chetlab o'tadigan yo'l bo'lib qolardi. Begona mavzu `404`:
        "bunday fayl yo'q" javobi kimningdir nimadir eksport qilganini ham
        oshkor qilmaydi.
        """
        export = self._get_export(job_id)
        required = REPORT_SCOPE.get(export.report_type)
        if required and not has_permission_code(request_user(request), required):
            raise Http404
        return export
