"""
Fon vazifalari (docs/02 §18).

Eksport vazifasi **tenant kontekstini o'zi tiklaydi**: Celery ishchisi
boshqa jarayonda ishlaydi va so'rovdagi `ContextVar` unga o'tmaydi.
Kontekstsiz har qanday so'rov `TenantScopeMissing` bilan yiqiladi — ya'ni
bu yerda unutish jimgina barcha tashkilotni o'qishga emas, ochiq xatoga
olib keladi. Fail-closed shu ma'noda ishlaydi.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date
from typing import Any

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone, translation

from apps.core.tasks import reliable_task
from apps.core.tenancy import organization_context, platform_context
from apps.reports import exporters, selectors
from apps.reports import services as services_reports
from apps.reports.models import ExportStatus, ReportExport

logger = logging.getLogger(__name__)

__all__ = [
    "generate_export",
    "send_debt_reminders",
    "recompute_balances",
    "purge_old_exports",
    "remind_late_reports",
    "remind_taxes",
]


def _run_report(report_type: str, organization_id: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Parametrlarni tegishli selektorga uzatadi."""
    today = timezone.localdate()
    date_from = (
        date.fromisoformat(params["date_from"]) if params.get("date_from") else today.replace(day=1)
    )
    date_to = date.fromisoformat(params["date_to"]) if params.get("date_to") else today
    branch_id = params.get("branch_id")
    # Ekrandagi kesim eksportda ham saqlanadi: foydalanuvchi haftalik
    # grafikni ko'rib "yuklab olish"ni bossa, oylik jadval kutilmagan
    # bo'lardi. Noto'g'ri qiymat selektorda ochiq xato beradi.
    group_by = str(params.get("group_by") or selectors.DEFAULT_GROUP_BY)

    if report_type == "revenue":
        return selectors.revenue_report(
            organization_id=organization_id,
            date_from=date_from,
            date_to=date_to,
            branch_id=branch_id,
            group_by=group_by,
        )
    if report_type == "expenses":
        return selectors.expense_report(
            organization_id=organization_id,
            date_from=date_from,
            date_to=date_to,
            branch_id=branch_id,
            group_by=group_by,
        )
    if report_type == "payroll":
        return selectors.payroll_report(
            organization_id=organization_id,
            year=int(params.get("year") or today.year),
            branch_id=branch_id,
        )
    if report_type == "attendance":
        return selectors.attendance_report(
            organization_id=organization_id,
            year=int(params.get("year") or today.year),
            month=int(params.get("month") or today.month),
            group_id=params.get("group_id"),
        )
    if report_type == "debtors":
        return selectors.debtor_report(organization_id=organization_id, branch_id=branch_id)
    if report_type == "profit-loss":
        return selectors.profit_loss(
            organization_id=organization_id,
            date_from=date_from,
            date_to=date_to,
            branch_id=branch_id,
            group_by=group_by,
        )
    raise ValueError(f"Noma'lum hisobot turi: {report_type}")


def _staff_timesheet_rows(**kwargs: Any) -> list[dict[str, Any]]:
    """Xodimlar tabeli — davomat modulining servisidan (invariant 1)."""
    from apps.attendance.services_staff import timesheet_rows

    return timesheet_rows(**kwargs)


def _monthly_table_rows(**kwargs: Any) -> list[dict[str, Any]]:
    """Oylik to'lov jadvali — moliya modulining selektoridan (invariant 1)."""
    from apps.finance.selectors import monthly_table_rows

    return monthly_table_rows(**kwargs)


def _detail_rows(report_type: str, organization_id: Any, params: dict[str, Any]) -> list[Any]:
    """
    Eksport uchun BATAFSIL qatorlar.

    `profit-loss` — tabiatan yig'ma hisobot (davr bo'yicha), shuning uchun
    u eski yo'ldan boradi. Qolganlari yozuv darajasida chiqadi: buxgalter
    faylni ochib har bir to'lovni, chiqimni, xodimni ko'radi.
    """
    today = timezone.localdate()
    date_from = (
        date.fromisoformat(params["date_from"]) if params.get("date_from") else today.replace(day=1)
    )
    date_to = date.fromisoformat(params["date_to"]) if params.get("date_to") else today
    common = {
        "organization_id": organization_id,
        "branch_id": params.get("branch_id"),
        "date_from": date_from,
        "date_to": date_to,
        "year": int(params.get("year") or today.year),
        "month": int(params.get("month") or today.month),
        "group_id": params.get("group_id"),
        # Ekrandagi filtr EKSPORTDA ham saqlanadi: buxgalter "terminal"
        # ni tanlab "yuklab olish"ni bossa, faylda hamma usul chiqishi
        # kutilmagan bo'lardi (PLAN 1.8).
        "method": params.get("method") or "",
        "child_id": params.get("child_id"),
        "received_by": params.get("received_by"),
    }
    builders: dict[str, Callable[..., list[dict[str, Any]]]] = {
        "revenue": selectors.revenue_rows,
        "expenses": selectors.expense_rows,
        "payroll": selectors.payroll_rows,
        "debtors": selectors.debtor_rows,
        "attendance": selectors.attendance_rows,
        "staff-attendance": _staff_timesheet_rows,
        "monthly": _monthly_table_rows,
    }
    builder = builders.get(report_type)
    if builder is None:
        payload = _run_report(report_type, organization_id, params)
        _, rows = exporters.rows_for(report_type, payload)
        return rows
    return builder(**common)


@reliable_task(name="reports.generate_export")
def generate_export(export_id: str, organization_id: str | None = None) -> str:
    """
    Eksportni tayyorlaydi va faylni saqlaydi.

    `organization_id` argument sifatida uzatiladi. Avval u yozuvning
    o'zidan o'qilardi — lekin RLS ostida bu ishlamaydi: kontekstsiz
    ulanish yozuvni umuman ko'rmaydi va vazifa "topilmadi" deb
    qaytarardi. Ya'ni foydalanuvchi eksport so'raydi, xato ham
    chiqmaydi, fayl ham kelmaydi.

    Endi tenant vazifa argumentida — bu to'g'riroq ham: ishchi qaysi
    tashkilot uchun ishlayotganini BILISHI kerak, uni bazadan taxmin
    qilib olmasligi.

    Xato bo'lsa yozuv `failed` holatiga o'tadi va sabab saqlanadi —
    "eksport bosdim, hech narsa bo'lmadi" degan holat qolmasligi kerak.
    """
    if organization_id is None:
        logger.warning("Eksport uchun tashkilot ko'rsatilmagan: %s", export_id)
        return "missing"

    with organization_context(organization_id):
        export = ReportExport.objects.filter(pk=export_id).first()
        if export is None:
            logger.warning("Eksport topilmadi: %s", export_id)
            return "missing"
        export.status = ExportStatus.RUNNING
        export.save(update_fields=["status", "updated_at"])
        try:
            params = export.params or {}
            # Til so'rov paytida saqlanadi: vazifa keyinroq, boshqa
            # jarayonda ishlaydi va `Accept-Language` u yerga yetib
            # bormaydi — sarlavhalar o'zbekcha bo'lib qolardi (ADR-16).
            with translation.override(params.get("language") or settings.LANGUAGE_CODE):
                rows = _detail_rows(export.report_type, export.organization_id, params)
                content = exporters.to_xlsx(export.report_type, rows, title=export.report_type)

            # Fayl nomi SO'ROV tilida (PLAN 4.2): buxgalter uni
            # papkasida nomi bo'yicha topadi va boshqa odamga
            # uzatadi, ya'ni nom unga ham ma'noli bo'lishi kerak.
            stamp = timezone.localtime().strftime("%Y-%m-%d_%H-%M")
            export.file.save(
                exporters.export_filename(
                    export.report_type,
                    language=params.get("language") or settings.LANGUAGE_CODE,
                    stamp=stamp,
                ),
                ContentFile(content),
                save=False,
            )
            export.row_count = len(rows)
            export.status = ExportStatus.READY
            export.error = ""
        except Exception as exc:  # noqa: BLE001 — sabab yozuvda qolishi kerak
            logger.exception("Eksport tayyorlanmadi: %s", export_id)
            export.status = ExportStatus.FAILED
            export.error = str(exc)[:500]

        export.completed_at = timezone.now()
        export.save(
            update_fields=["status", "file", "row_count", "error", "completed_at", "updated_at"]
        )

    return export.status


@reliable_task(name="reports.send_debt_reminders")
def send_debt_reminders() -> dict[str, int]:
    """
    Beat vazifasi: har bir tashkilotning qarzdorlariga eslatma.

    Tashkilotlar bo'ylab aylanadi va HAR BIRI uchun kontekstni alohida
    o'rnatadi — ya'ni bitta tsiklda ham tenant chegarasi saqlanadi.
    """
    from apps.notifications import services as notifications
    from apps.organizations.models import Organization
    from apps.settings_app.services import get_setting

    sent = 0
    organizations = 0
    failed = 0
    with platform_context():
        all_organizations = list(Organization.objects.filter(is_active=True))
    # Har bir tashkilot ALOHIDA: ikkinchisida chiqqan xato uchinchisidan
    # oxirigacha bo'lgan hammasini o'sha kechadan mahrum qilmasin.
    for organization in all_organizations:
        try:
            with organization_context(organization.id):
                if not get_setting(key="notifications.sms_enabled"):
                    continue
                organizations += 1
                for notification in notifications.queue_debt_reminders(organization=organization):
                    notifications.dispatch_notification(notification)
                    sent += 1
        except Exception:
            failed += 1
            logger.exception("Eslatmalarni yuborib bo'lmadi: %s", organization.slug)

    if failed:
        logger.error("Qarz eslatmalari: %s tashkilotda muvaffaqiyatsiz", failed)
    return {"organizations": organizations, "queued": sent, "failed": failed}


@reliable_task(name="reports.recompute_balances")
def recompute_balances() -> dict[str, int]:
    """
    Tunlik solishtirish: `child.balance` keshini ledger'dan qayta hisoblaydi
    va farq topilsa log'ga yozadi (docs/03 §26).

    Kesh siljishi jimgina yuz beradi va eng yomon joyda — qarz talab
    qilishda — chiqadi. Shuning uchun uni kutib o'tirmasdan, har kecha
    tekshiramiz.
    """
    from apps.children.models import Child
    from apps.finance.services import recompute_child_balance
    from apps.organizations.models import Organization

    checked = 0
    drifted = 0
    failed = 0
    with platform_context():
        all_organizations = list(Organization.objects.filter(is_active=True))
    # Bitta bolaning nosozligi butun kechani yo'qotmasin: tekshiruvning
    # o'zi JIM, ya'ni to'xtab qolgani ham jim bo'lardi — ro'yxatning
    # quyruq qismi hech qachon solishtirilmay qolardi.
    for organization in all_organizations:
        with organization_context(organization.id):
            for child in Child.objects.all():
                try:
                    before = child.balance
                    after = recompute_child_balance(child)
                except Exception:
                    failed += 1
                    logger.exception("Balansni qayta hisoblab bo'lmadi: bola=%s", child.id)
                    continue
                checked += 1
                if before != after:
                    drifted += 1
                    logger.warning(
                        "Balans siljishi: bola=%s kesh=%s ledger=%s", child.id, before, after
                    )

    if failed:
        logger.error("Balans solishtiruvi: %s bolada muvaffaqiyatsiz", failed)
    return {"checked": checked, "drifted": drifted, "failed": failed}


@reliable_task(name="reports.purge_old_exports")
def purge_old_exports(days: int = 30) -> dict[str, int]:
    """
    Tunlik tozalash: eskirgan va yetim eksport fayllari.

    Nega jadvalda: eksportni hech narsa oʻchirmasdi, yaʼni qarzdorlar
    roʻyxati serverda cheksiz yotaverardi. Bir marta qoʻlda tozalash
    muammoni yopmaydi — u ertaga qaytadan yigʻila boshlaydi.

    Mantiq servisda; bu yerda faqat jadval va natija.
    """
    result = services_reports.purge_old_exports(days=days, apply=True)
    if result["removed_files"]:
        logger.info(
            "Eksportlar tozalandi: %s ta yozuv, %s ta fayl",
            result["removed_rows"],
            result["removed_files"],
        )
    return {"rows": result["removed_rows"], "files": result["removed_files"]}


@reliable_task(name="reports.remind_late_reports")
def remind_late_reports() -> dict[str, int]:
    """
    Har kuni: o'tgan oy hisoboti muddatdan (sukut — 5-sana) o'tib ham
    topshirilmagan bo'lsa, rahbarlarga bir marta eslatma (Bosqich 13.6,
    brif §8). Faqat B/C modelda — A'da topshiruvchi yo'q.

    Bir filialli bog'chada hisobot tashkilot darajasida; ko'p filialli
    bog'chada — har filial o'z modeli bilan.
    """
    from django.utils.translation import gettext

    from apps.branches.models import Branch
    from apps.intelligence import alerts
    from apps.organizations.models import Organization
    from apps.reports import review as flow
    from apps.reports.models import ReviewStatus

    today = timezone.localdate()
    year, month = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
    with platform_context():
        organizations = list(Organization.objects.filter(is_active=True))
    totals = {"organizations": 0, "reminded": 0, "failed": 0}
    for organization in organizations:
        try:
            with organization_context(organization.id):
                branches = list(Branch.objects.filter(is_active=True).order_by("name"))
                units = [None] if len(branches) <= 1 else branches
                for branch in units:
                    branch_id = branch.id if branch else None
                    if flow.model_for(branch_id) == "A":
                        continue
                    if today <= flow.deadline(year, month, branch_id):
                        continue
                    totals["organizations"] += 1
                    report = flow.review_for(
                        organization=organization, year=year, month=month, branch_id=branch_id
                    )
                    waiting = report.status in (ReviewStatus.DRAFT, ReviewStatus.RETURNED)
                    if not waiting or report.late_notified_at is not None:
                        continue
                    where = f", {branch.name}" if branch else ""
                    alerts.notify(
                        organization_id=organization.id,
                        text=gettext(
                            "⏰ {period}{where} hisoboti muddatda topshirilmadi "
                            "(muddat {deadline})."
                        ).format(
                            period=f"{month:02d}.{year}",
                            where=where,
                            deadline=flow.deadline(year, month, branch_id).strftime("%d.%m.%Y"),
                        ),
                    )
                    report.late_notified_at = timezone.now()
                    report.save(update_fields=["late_notified_at", "updated_at"])
                    totals["reminded"] += 1
        except Exception:  # noqa: BLE001 — bitta tashkilot boshqalarini to'xtatmasin
            totals["failed"] += 1
            logger.exception(
                "Kechikkan hisobot eslatmasi yiqildi: organization=%s", organization.id
            )
    return totals


@reliable_task(name="reports.remind_taxes")
def remind_taxes() -> dict[str, int]:
    """
    Har kuni: soliq muddatiga 3 kun qolganda bir marta, o'tib ketganda yana
    bir marta rahbarlarga eslatma (Bosqich 13.8, brif §9). Avval o'tgan va
    joriy oy majburiyatlari hujjatlardan yangilanadi.
    """
    from django.utils.translation import gettext

    from apps.intelligence import alerts
    from apps.organizations.models import Organization
    from apps.reports import taxes
    from apps.reports.models import TaxKind, TaxObligation

    today = timezone.localdate()
    previous = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
    with platform_context():
        organizations = list(Organization.objects.filter(is_active=True))
    totals = {"organizations": 0, "reminded": 0, "failed": 0}
    for organization in organizations:
        try:
            with organization_context(organization.id):
                totals["organizations"] += 1
                for year, month in (previous, (today.year, today.month)):
                    taxes.sync(organization=organization, year=year, month=month)
                for row in TaxObligation.objects.filter(operation__isnull=True, amount__gt=0):
                    days = (row.due_date - today).days
                    title = str(TaxKind(row.kind).label)
                    period = f"{row.period_month:02d}.{row.period_year}"
                    amount = f"{int(row.amount):,}".replace(",", " ")
                    if 0 <= days <= 3 and row.reminded_at is None:
                        text = gettext("🧾 {title} ({period}): {amount} soʻm, muddat {due}.")
                        field = "reminded_at"
                    elif days < 0 and row.overdue_notified_at is None:
                        text = gettext(
                            "⚠️ {title} ({period}): {amount} soʻm — muddati oʻtdi ({due})."
                        )
                        field = "overdue_notified_at"
                    else:
                        continue
                    alerts.notify(
                        organization_id=organization.id,
                        text=text.format(
                            title=title,
                            period=period,
                            amount=amount,
                            due=row.due_date.strftime("%d.%m.%Y"),
                        ),
                    )
                    setattr(row, field, timezone.now())
                    row.save(update_fields=[field, "updated_at"])
                    totals["reminded"] += 1
        except Exception:  # noqa: BLE001 — bitta tashkilot boshqalarini to'xtatmasin
            totals["failed"] += 1
            logger.exception("Soliq eslatmasi yiqildi: organization=%s", organization.id)
    return totals
