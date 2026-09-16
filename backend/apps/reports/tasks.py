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
from datetime import date
from typing import Any

from django.core.files.base import ContentFile
from django.utils import timezone

from apps.core.tasks import reliable_task
from apps.core.tenancy import organization_context, platform_context
from apps.reports import exporters, selectors
from apps.reports.models import ExportStatus, ReportExport

logger = logging.getLogger(__name__)

__all__ = ["generate_export", "send_debt_reminders", "recompute_balances"]


def _run_report(report_type: str, organization_id: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Parametrlarni tegishli selektorga uzatadi."""
    today = timezone.localdate()
    date_from = (
        date.fromisoformat(params["date_from"]) if params.get("date_from") else today.replace(day=1)
    )
    date_to = date.fromisoformat(params["date_to"]) if params.get("date_to") else today
    branch_id = params.get("branch_id")

    if report_type == "revenue":
        return selectors.revenue_report(
            organization_id=organization_id,
            date_from=date_from,
            date_to=date_to,
            branch_id=branch_id,
        )
    if report_type == "expenses":
        return selectors.expense_report(
            organization_id=organization_id,
            date_from=date_from,
            date_to=date_to,
            branch_id=branch_id,
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
        )
    raise ValueError(f"Noma'lum hisobot turi: {report_type}")


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
            payload = _run_report(export.report_type, export.organization_id, export.params or {})
            headers, rows = exporters.rows_for(export.report_type, payload)
            content = exporters.to_csv(headers, rows)

            stamp = timezone.localtime().strftime("%Y%m%d-%H%M")
            export.file.save(f"{export.report_type}-{stamp}.csv", ContentFile(content), save=False)
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
    with platform_context():
        all_organizations = list(Organization.objects.filter(is_active=True))
    for organization in all_organizations:
        with organization_context(organization.id):
            if not get_setting(key="notifications.sms_enabled"):
                continue
            organizations += 1
            for notification in notifications.queue_debt_reminders(organization=organization):
                notifications.dispatch_notification(notification)
                sent += 1

    return {"organizations": organizations, "queued": sent}


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
    with platform_context():
        all_organizations = list(Organization.objects.filter(is_active=True))
    for organization in all_organizations:
        with organization_context(organization.id):
            for child in Child.objects.all():
                before = child.balance
                after = recompute_child_balance(child)
                checked += 1
                if before != after:
                    drifted += 1
                    logger.warning(
                        "Balans siljishi: bola=%s kesh=%s ledger=%s", child.id, before, after
                    )

    return {"checked": checked, "drifted": drifted}
