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


def _parse_uuid(value: Any) -> Any:
    """Buzuq identifikator — "topilmadi" (404), xato emas."""
    import uuid

    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise Http404 from exc


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

# Moliya markazi mavzulari (ADR-42): `payroll.read` YOKI `reports.finance`.
# Ikkinchisi faqat jami summalarni ochadi — paketda xodim nomi bilan oylik
# yo'q, u `payroll.read` ortidagi oylik modulida qoladi. Shu bilan ega
# boshqaruvchiga hisobotni tayyorlashni beradi, kim qancha olishini emas.
FINANCE_CENTER_REPORTS: frozenset[str] = frozenset({"finance", "pack"})


def report_allowed(user: Any, report: str | None) -> bool:
    """Foydalanuvchi shu hisobot mavzusini ko'ra oladimi."""
    required = REPORT_SCOPE.get(report or "")
    if required is None:
        return True
    if report in FINANCE_CENTER_REPORTS and has_permission_code(user, "reports.finance"):
        return True
    return has_permission_code(user, required)


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
    "review": "pack",
    "review_submit": "pack",
    "review_note": "pack",
    "review_answer": "pack",
    "review_question": "pack",
    "review_accept": "pack",
    "review_return": "pack",
    "review_approve": "pack",
    "review_share": "pack",
    "review_share_revoke": "pack",
    "network": "pack",
    "budget": "finance",
    "budget_save": "finance",
    "budget_copy": "finance",
    "forecast": "finance",
    "trends": "finance",
    "kpi": "finance",
    "annual": "finance",
    "annual_pdf": "finance",
    "annual_xlsx": "finance",
    "tax_calendar": "finance",
    "tax_pay": "finance",
    "journal": "finance",
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
        return report_allowed(request_user(request), report)


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
        # Boshqaruv (13.6, ADR-42): paketni ko'ra olgan tayyorlaydi —
        # topshiradi, izoh va javob yozadi; rahbar (`reports.approve`)
        # savol beradi, qaytaradi, qabul qiladi, tasdiqlaydi va ulashadi.
        "review": "read",
        "review_submit": "read",
        "review_note": "read",
        "review_answer": "read",
        "review_question": "approve",
        "review_accept": "approve",
        "review_return": "approve",
        "review_approve": "approve",
        "review_share": "approve",
        "review_share_revoke": "approve",
        "network": "read",
        # Reja (13.7): o'qish — moliya ko'radigan har kim; o'zgartirish —
        # `reports.update` (egasi, direktor).
        "budget": "read",
        "budget_save": "update",
        "budget_copy": "update",
        "forecast": "read",
        "trends": "read",
        "kpi": "read",
        "annual": "read",
        "annual_pdf": "read",
        "annual_xlsx": "read",
        # Soliq taqvimi (13.8): to'lash — pul chiqadi, rahbar ishi.
        "tax_calendar": "read",
        "tax_pay": "approve",
        "journal": "read",
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
        """
        Davr va hisobot birligi. Bitta filialli bog'chada birlik — tashkilot:
        egasi (filialsiz) va filialga bog'langan boshqaruvchi aynan bitta
        hisobotni ko'rishi, topshirishi va qabul qilishi kerak (13.6).
        """
        from apps.branches.models import Branch

        source = request.query_params if request.method == "GET" else request.data
        today = timezone.localdate()
        year = _parse_int(source.get("year"), today.year, low=2000, high=2100)
        month = _parse_int(source.get("month"), today.month, low=1, high=12)
        branch = self.branch_for(request, source.get("branch"))
        if branch is not None and Branch.objects.count() == 1:
            branch = None
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
        _organization_id, year, month, branch = self._pack_scope(request)
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

    # --- Boshqaruv: topshirish, savol, qabul, ulashish (Bosqich 13.6) ---

    def _review(self, request: Request) -> Any:
        from apps.reports import review as flow

        _organization_id, year, month, branch = self._pack_scope(request)
        return flow.review_for(
            organization=request_user(request).organization,
            year=year,
            month=month,
            branch_id=branch,
        )

    def _review_state(self, request: Request, report: Any, code: int = 200) -> Response:
        from apps.reports import pack
        from apps.reports import review as flow

        live = None
        if report.snapshot_id:
            live = pack.checksum(
                pack.build(
                    organization_id=report.organization_id,
                    year=report.period_year,
                    month=report.period_month,
                    branch_id=report.branch_id,
                )
            )
        return Response(
            flow.state(review=report, user=request_user(request), live_checksum=live), status=code
        )

    def _audit_review(self, request: Request, report: Any, action: str, what: str) -> None:
        from apps.audit import services as audit

        audit.record(
            action=action,
            request=request._request,
            actor=request_user(request),
            entity_type="report_review",
            entity_id=report.id,
            changes={
                "period": f"{report.period_year}-{report.period_month:02d}",
                "step": what,
                "version": report.snapshot.version if report.snapshot_id else None,
            },
        )

    @action(detail=False, url_path="review")
    def review(self, request: Request) -> Response:
        """`GET /reports/review?year=&month=` — model, holat, shart, tarix, ochilishlar."""
        return self._review_state(request, self._review(request))

    @action(detail=False, methods=["post"], url_path="review/submit")
    def review_submit(self, request: Request) -> Response:
        from apps.reports import review as flow

        report = flow.submit(review=self._review(request), user=request_user(request))
        self._audit_review(request, report, "update", "submit")
        return self._review_state(request, report, status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="review/approve")
    def review_approve(self, request: Request) -> Response:
        from apps.reports import review as flow

        report = flow.approve(review=self._review(request), user=request_user(request))
        self._audit_review(request, report, "approve", "approve")
        return self._review_state(request, report, status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="review/accept")
    def review_accept(self, request: Request) -> Response:
        from apps.reports import review as flow

        report = flow.accept(review=self._review(request), user=request_user(request))
        self._audit_review(request, report, "approve", "accept")
        return self._review_state(request, report, status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="review/return")
    def review_return(self, request: Request) -> Response:
        from apps.reports import review as flow

        report = flow.send_back(
            review=self._review(request),
            user=request_user(request),
            text=request.data.get("text", ""),
        )
        self._audit_review(request, report, "reject", "return")
        return self._review_state(request, report, status.HTTP_201_CREATED)

    def _event_response(self, event: Any) -> Response:
        return Response(
            {"id": str(event.id), "kind": event.kind, "path": event.path},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], url_path="review/question")
    def review_question(self, request: Request) -> Response:
        from apps.reports import review as flow

        event = flow.ask(
            review=self._review(request),
            user=request_user(request),
            path=request.data.get("path", ""),
            text=request.data.get("text", ""),
        )
        return self._event_response(event)

    @action(detail=False, methods=["post"], url_path="review/answer")
    def review_answer(self, request: Request) -> Response:
        from apps.reports import review as flow
        from apps.reports.models import ReportEvent

        user = request_user(request)
        question = (
            ReportEvent.objects.select_related("review")
            .filter(pk=_parse_uuid(request.data.get("question")))
            .first()
        )
        # Filialga bog'langan xodim boshqa filial hisobotini ko'rmaydi —
        # uning savolini ham.
        if question is None or (
            not user.is_org_owner
            and user.branch_id is not None
            and question.review.branch_id not in (None, user.branch_id)
        ):
            raise Http404
        event = flow.answer(question=question, user=user, text=request.data.get("text", ""))
        return self._event_response(event)

    @action(detail=False, methods=["post"], url_path="review/note")
    def review_note(self, request: Request) -> Response:
        from apps.reports import review as flow

        event = flow.note(
            review=self._review(request),
            user=request_user(request),
            path=request.data.get("path", ""),
            text=request.data.get("text", ""),
        )
        return self._event_response(event)

    @action(detail=False, methods=["post"], url_path="review/share")
    def review_share(self, request: Request) -> Response:
        """Faqat o'qish uchun havola; token faqat shu javobda ko'rinadi."""
        from apps.audit import services as audit
        from apps.reports import share

        link, token = share.create_link(
            review=self._review(request),
            user=request_user(request),
            label=request.data.get("label", ""),
            days=request.data.get("days"),
        )
        audit.record(
            action="create",
            request=request._request,
            actor=request_user(request),
            entity_type="report_share_link",
            entity_id=link.id,
            changes={"label": link.label, "expires_at": link.expires_at.isoformat()},
        )
        return Response(
            {
                "id": str(link.id),
                "url": share.url_for(token),
                "expires_at": link.expires_at.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path=r"review/share/(?P<link_id>[0-9a-f-]{36})/revoke",
    )
    def review_share_revoke(self, request: Request, link_id: str = "") -> Response:
        from apps.audit import services as audit
        from apps.reports.models import ReportShareLink

        link = ReportShareLink.objects.filter(pk=_parse_uuid(link_id)).first()
        if link is None:
            raise Http404
        if link.revoked_at is None:
            link.revoked_at = timezone.now()
            link.save(update_fields=["revoked_at", "updated_at"])
            audit.record(
                action="update",
                request=request._request,
                actor=request_user(request),
                entity_type="report_share_link",
                entity_id=link.id,
                changes={"revoked": True},
            )
        return Response({"id": str(link.id), "revoked": True})

    @action(detail=False, url_path="network")
    def network(self, request: Request) -> Response:
        """`GET /reports/network` — filiallar yonma-yon; faqat butun tashkilotni ko'radiganga."""
        from rest_framework.exceptions import PermissionDenied

        from apps.reports import network

        user = request_user(request)
        if not user.is_org_owner and user.branch_id is not None:
            raise PermissionDenied(gettext("Tarmoq koʻrinishi butun tashkilot rahbari uchun."))
        year, month = self._year_month(request)
        return Response(
            network.network(organization_id=user.organization_id, year=year, month=month)
        )

    # --- Reja, prognoz, ko'rsatkichlar, trend, yillik (Bosqich 13.7) ---

    @action(detail=False, methods=["get"], url_path="budget")
    def budget(self, request: Request) -> Response:
        """`GET /reports/budget?year=&month=` — reja va fakt yonma-yon."""
        from apps.reports import planning

        organization_id, year, month, branch = self._pack_scope(request)
        return Response(
            planning.budget(
                organization_id=organization_id, year=year, month=month, branch_id=branch
            )
        )

    @budget.mapping.put
    def budget_save(self, request: Request) -> Response:
        """`PUT /reports/budget {year, month, lines:[{kind, category_id?, amount}]}`."""
        from apps.audit import services as audit
        from apps.reports import planning

        organization_id, year, month, branch = self._pack_scope(request)
        lines = request.data.get("lines")
        if not isinstance(lines, list):
            raise BusinessRuleViolation(gettext("Reja qatorlari roʻyxat boʻlishi kerak."))
        user = request_user(request)
        planning.save_budget(
            organization=user.organization,
            year=year,
            month=month,
            branch_id=branch,
            lines=lines,
            user=user,
        )
        audit.record(
            action="update",
            request=request._request,
            actor=user,
            entity_type="budget",
            changes={"period": f"{year}-{month:02d}", "lines": len(lines)},
        )
        return Response(
            planning.budget(
                organization_id=organization_id, year=year, month=month, branch_id=branch
            )
        )

    @action(detail=False, methods=["post"], url_path="budget/copy")
    def budget_copy(self, request: Request) -> Response:
        """`POST /reports/budget/copy {from_year, from_month, year, month}`."""
        from apps.reports import planning

        organization_id, year, month, branch = self._pack_scope(request)
        source = (
            _parse_int(request.data.get("from_year"), 0, low=2000, high=2100),
            _parse_int(request.data.get("from_month"), 0, low=1, high=12),
        )
        user = request_user(request)
        planning.copy_budget(
            organization=user.organization,
            branch_id=branch,
            source=source,
            target=(year, month),
            user=user,
        )
        return Response(
            planning.budget(
                organization_id=organization_id, year=year, month=month, branch_id=branch
            )
        )

    @action(detail=False)
    def forecast(self, request: Request) -> Response:
        """`GET /reports/forecast?date=` — 30/60/90 kun va xavfsiz olish summasi."""
        from apps.reports import forecast

        organization_id, _year, _month, branch = self._pack_scope(request)
        day = _parse_date(request.query_params.get("date"), timezone.localdate())
        return Response(
            forecast.forecast(organization_id=organization_id, as_of=day, branch_id=branch)
        )

    @action(detail=False)
    def trends(self, request: Request) -> Response:
        """`GET /reports/trends?year=&month=` — shu oy bilan tugaydigan 12 oy."""
        from apps.reports import planning

        organization_id, year, month, branch = self._pack_scope(request)
        return Response(
            planning.trends(
                organization_id=organization_id, year=year, month=month, branch_id=branch
            )
        )

    @action(detail=False)
    def kpi(self, request: Request) -> Response:
        """`GET /reports/kpi?year=&month=` — ko'rsatkichlar va ularning ta'rifi."""
        from apps.reports import planning

        organization_id, year, month, branch = self._pack_scope(request)
        return Response(
            planning.kpis(organization_id=organization_id, year=year, month=month, branch_id=branch)
        )

    def _annual(self, request: Request) -> tuple[dict[str, Any], int]:
        from apps.audit import services as audit
        from apps.reports import planning

        organization_id, _year, _month, branch = self._pack_scope(request)
        year = _parse_int(
            request.query_params.get("year"), timezone.localdate().year, low=2000, high=2100
        )
        audit.record(
            action="view",
            request=request._request,
            actor=request_user(request),
            entity_type="report_annual",
            changes={"year": year, "branch": str(branch) if branch else None},
        )
        return planning.annual(organization_id=organization_id, year=year, branch_id=branch), year

    @action(detail=False)
    def annual(self, request: Request) -> Response:
        """`GET /reports/annual?year=` — yillik hisobot (12 oy yig'indisi)."""
        data, _year = self._annual(request)
        return Response(data)

    @action(detail=False, url_path="annual/pdf")
    def annual_pdf(self, request: Request) -> FileResponse:
        import io

        from apps.reports import pack_render

        data, year = self._annual(request)
        content = pack_render.to_pdf(
            data,
            title=gettext("Yillik moliyaviy hisobot — {year}").format(year=year),
            prepared_by=request_user(request).full_name,
        )
        return FileResponse(
            io.BytesIO(content), filename=f"yillik-{year}.pdf", content_type="application/pdf"
        )

    @action(detail=False, url_path="annual/xlsx")
    def annual_xlsx(self, request: Request) -> FileResponse:
        import io

        from apps.reports import pack_render

        data, year = self._annual(request)
        months = next(section for section in data["sections"] if section["key"] == "months")
        return FileResponse(
            io.BytesIO(pack_render.to_xlsx(data, raw={gettext("Oylar"): months["rows"]})),
            filename=f"yillik-{year}.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    @action(detail=False)
    def journal(self, request: Request) -> Any:
        """
        `GET /reports/journal?year=&month=&file=xlsx|csv` — Dt/Kt jurnal (13.8).
        `format` emas: DRF uni javob formatini tanlash uchun o'zi ushlab oladi.
        """
        import io

        from apps.audit import services as audit
        from apps.reports import journal

        organization_id, year, month, branch = self._pack_scope(request)
        data = journal.build(
            organization_id=organization_id, year=year, month=month, branch_id=branch
        )
        kind = request.query_params.get("file", "")
        if kind not in ("xlsx", "csv"):
            return Response(data)
        audit.record(
            action="export",
            request=request._request,
            actor=request_user(request),
            entity_type="journal",
            changes={"period": f"{year}-{month:02d}", "format": kind},
        )
        if kind == "csv":
            return FileResponse(
                io.BytesIO(journal.to_csv(data)),
                filename=f"jurnal-{year}-{month:02d}.csv",
                content_type="text/csv; charset=utf-8",
            )
        return FileResponse(
            io.BytesIO(journal.to_xlsx(data)),
            filename=f"jurnal-{year}-{month:02d}.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # --- Soliq taqvimi (Bosqich 13.8) ---

    @action(detail=False, url_path="tax-calendar")
    def tax_calendar(self, request: Request) -> Response:
        """`GET /reports/tax-calendar?year=` — majburiyatlar, muddat va holat."""
        from apps.reports import taxes

        year = _parse_int(
            request.query_params.get("year"), timezone.localdate().year, low=2000, high=2100
        )
        return Response(
            taxes.calendar_for(organization=request_user(request).organization, year=year)
        )

    @action(
        detail=False,
        methods=["post"],
        url_path=r"tax-calendar/(?P<obligation_id>[0-9a-f-]{36})/pay",
    )
    def tax_pay(self, request: Request, obligation_id: str = "") -> Response:
        """`POST /reports/tax-calendar/{id}/pay {cash_account_id, paid_on?}`."""
        from apps.audit import services as audit
        from apps.cash.models import CashAccount
        from apps.reports import taxes
        from apps.reports.models import TaxObligation

        obligation = TaxObligation.objects.filter(pk=_parse_uuid(obligation_id)).first()
        if obligation is None:
            raise Http404
        account = CashAccount.objects.filter(
            pk=_parse_uuid(request.data.get("cash_account_id"))
        ).first()
        if account is None:
            raise BusinessRuleViolation(gettext("Pul qaysi qopdan toʻlanishini tanlang."))
        user = request_user(request)
        paid_on = request.data.get("paid_on")
        obligation = taxes.pay(
            obligation=obligation,
            account=account,
            user=user,
            paid_on=_parse_date(paid_on, timezone.localdate()) if paid_on else None,
            allow_negative=str(request.data.get("allow_negative", "")).lower() == "true",
        )
        audit.record(
            action="update",
            request=request._request,
            actor=user,
            entity_type="tax_obligation",
            entity_id=obligation.id,
            changes={"paid": str(obligation.amount), "kind": obligation.kind},
        )
        return Response(
            {
                "id": str(obligation.id),
                "status": taxes.status_of(obligation),
                "amount": f"{obligation.amount:.2f}",
            }
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
            report for report in REPORT_SCOPE if report_allowed(request_user(request), report)
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
        if not report_allowed(request_user(request), export.report_type):
            raise Http404
        return export
