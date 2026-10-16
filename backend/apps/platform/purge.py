"""
Tashkilotni butunlay o'chirish (docs/03 §7, §21).

Bu fayl loyihadagi eng xavfli kod. U **qaytarib bo'lmaydigan** amalni
bajaradi, shuning uchun uchta himoya bor:

1. **Eksport oynasi.** Bekor qilingan tashkilot 30 kun davomida faqat
   o'qish rejimida qoladi va o'z ma'lumotini eksport qila oladi
   (docs/01 §4.4). Bu muddat tugamaguncha o'chirish rad etiladi.
2. **Ochiq tasdiq.** `confirm_slug` tashkilot slug'i bilan aynan mos
   kelishi kerak — "hammasini o'chir" tugmasini tasodifan bosib
   bo'lmaydi.
3. **Jadval tartibi qat'iy.** FK'lar `RESTRICT`, ya'ni noto'g'ri
   tartibda o'chirish xato beradi — bu yaxshi. Lekin xatoga tayanish
   o'rniga tartib shu yerda ochiq yozilgan va u testda tekshiriladi.

**Nega `CASCADE` emas:** kaskad o'chirish jimgina ishlaydi va nimani
o'chirganini aytmaydi. Bu yerda esa har bir jadval sanaladi va natija
audit jurnaliga yoziladi — o'chirish ham hodisa, va u ham yozuv
qoldirishi kerak.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context, platform_context

logger = logging.getLogger(__name__)

__all__ = ["EXPORT_WINDOW_DAYS", "PURGE_ORDER", "purge_organization"]

# Bekor qilingandan keyin ma'lumot shuncha kun saqlanadi (docs/01 §4.4).
EXPORT_WINDOW_DAYS = 30

# O'chirish tartibi: BOLALARDAN OTAGA.
#
# Har bir qator o'zidan oldingi qatorlarga bog'liq bo'lishi mumkin,
# shuning uchun tartib teskari — eng chekkadagi bog'liqliklardan
# boshlanadi. Bu ro'yxat qo'lda yozilgan va bu ataylab: avtomatik
# aniqlash "shekilli to'g'ri" bo'lardi, bu yerda esa "shekilli"
# yetarli emas.
PURGE_ORDER: tuple[str, ...] = (
    # Moliyaviy tarix — eng chuqur bog'liqliklar
    "apps.subscriptions.SubscriptionOnlineTransaction",
    "apps.subscriptions.SubscriptionPayment",
    "apps.subscriptions.SubscriptionInvoice",
    "apps.subscriptions.UsageSnapshot",
    "apps.subscriptions.Subscription",
    # Kassa harakatlari eng chekkada: ular to'lov, chiqim va avansga
    # `source_id` bilan (FK'siz) bog'langan, qopga esa `RESTRICT` bilan.
    # Shuning uchun ular hammasidan OLDIN, qop esa eng oxirida ketadi.
    "apps.cash.CashMovement",
    # Topshirish va sanoq — qopga va odamga `RESTRICT` (Bosqich 12.5).
    "apps.cash.CashHandover",
    "apps.cash.CashCount",
    "apps.cash.MoneyOperation",
    # Online payments (PLAN 6.1): they point at payments and invoices with
    # `RESTRICT`, so they go before both.
    "apps.online_payments.OnlineTransaction",
    "apps.online_payments.PaymentLink",
    "apps.online_payments.MerchantCredential",
    # Taqsimot to'lovga ham, hisob-fakturaga ham `RESTRICT` bilan
    # bog'langan — u ikkalasidan ham OLDIN o'chadi.
    # Contracts point at child, guardian and template with RESTRICT (PLAN 6.5).
    "apps.contracts.Contract",
    "apps.contracts.ContractTemplate",
    # Da'vo bolaga ham, hisob-fakturaga ham `RESTRICT` bilan bog'langan
    # (`applied_invoice`) — u ikkalasidan ham OLDIN o'chadi. Avval u
    # ro'yxatda hisob-fakturadan KEYIN turardi: izoh to'g'ri edi, o'rni
    # esa yo'q, va buni hech narsa ko'rsatmadi, chunki testlarda
    # tasdiqlangan da'vo yo'q edi. Jonli bazada esa bitta shunday da'vo
    # butun o'chirishni yiqitdi (PLAN 11.4).
    "apps.attendance.AbsenceClaim",
    # Qaytarish to'lovga, bolaga va qopga RESTRICT (13.2b).
    "apps.finance.Refund",
    "apps.finance.PaymentAllocation",
    "apps.finance.Payment",
    "apps.finance.ChildLedgerEntry",
    "apps.finance.InvoiceWriteOff",
    "apps.finance.MonthClose",
    "apps.finance.Invoice",
    "apps.finance.Discount",
    # Operatsion yozuvlar
    "apps.intelligence.Insight",  # acted_by → User; hosila, avval ketadi
    "apps.attendance.AttendanceRecord",
    # Xodimlar tabeli — `employee` ga RESTRICT, ya'ni xodimdan OLDIN.
    "apps.attendance.StaffAttendance",
    # To'lov qatori hisoblash va satrga `RESTRICT` bilan bog'langan —
    # u ikkalasidan ham OLDIN o'chadi.
    "apps.payroll.PayrollPayout",
    "apps.payroll.PayrollItem",
    "apps.payroll.PayrollRun",
    # Avans xodimga `RESTRICT` bilan bog'langan — u xodimdan OLDIN o'chadi.
    "apps.payroll.EmployeeAdvance",
    "apps.hr.Employee",
    "apps.hr.Position",
    # Kitchen (PLAN 6.6): menus point at dishes, dishes at products — all
    # before the products and warehouses they reference.
    "apps.kitchen.MenuItem",
    "apps.kitchen.MenuDay",
    "apps.kitchen.DishIngredient",
    "apps.kitchen.Dish",
    "apps.inventory.StockMovement",
    "apps.inventory.Product",
    "apps.inventory.ProductCategory",
    "apps.inventory.Warehouse",
    "apps.expenses.ExpenseItem",
    "apps.expenses.Expense",
    "apps.expenses.ExpenseCategory",
    # Yetkazib beruvchi chiqimdan KEYIN: nasiya chiqim unga `RESTRICT` (13.2a).
    "apps.inventory.Supplier",
    # Chiqim qopga `RESTRICT` bilan bog'langan — qop chiqimdan KEYIN.
    "apps.cash.CashAccount",
    "apps.notifications.Notification",
    "apps.parent_bot.ContactIndex",
    "apps.notifications.NotificationTemplate",
    "apps.reports.ReportExport",
    "apps.attendance.Holiday",
    "apps.attendance.AbsenceKind",
    "apps.settings_app.SystemSetting",
    # CRM
    "apps.children.Enrollment",
    "apps.children.ChildPause",
    "apps.children.ChildGuardian",
    "apps.children.Child",
    # Tarif BOLADAN KEYIN: `Child.tariff` — `RESTRICT`. Avval u moliya
    # bo'limida, bolalardan oldin turardi va tarifi bor bitta bola ham
    # butun o'chirishni yiqitardi (PLAN 5.10 da topildi).
    "apps.finance.TariffPlan",
    "apps.children.Guardian",
    "apps.children.Group",
    # Kirish
    "apps.accounts.User",
    "apps.accounts.Role",
    "apps.branches.Branch",
)


# `organization_id` ustuni YO'Q jadvallar — ular ota orqali bog'langan
# (docs/03 §21). Ularni ota-jadvaldan OLDIN o'chirish kerak, aks holda
# `RESTRICT` bloklaydi. Filtr yo'li shu yerda ochiq yozilgan, chunki
# uni taxmin qilib bo'lmaydi.
DERIVED_PURGE: dict[str, str] = {
    "apps.finance.InvoiceLine": "invoice__organization_id",
    "apps.accounts.RefreshToken": "user__organization_id",
}


def _model(path: str) -> Any:
    from django.apps import apps as django_apps

    module, name = path.rsplit(".", 1)
    app_label = module.split(".")[-1]
    return django_apps.get_model(app_label, name)


@transaction.atomic
def purge_organization(
    *, organization_id: Any, confirm_slug: str, actor: Any = None, force: bool = False
) -> dict[str, int]:
    """
    Tashkilotni va uning butun ma'lumotini o'chiradi.

    `force=True` faqat sud qarori yoki GDPR-tipidagi talab uchun:
    eksport oynasini chetlab o'tadi. Uni ishlatish audit jurnalida
    alohida ko'rinadi.
    """
    from apps.audit.models import AuditLog
    from apps.organizations.models import Organization
    from apps.platform.models import SignupRequest, SupportGrant

    with platform_context():
        organization = Organization.objects.filter(pk=organization_id).first()
        if organization is None:
            raise BusinessRuleViolation("Tashkilot topilmadi.")

        if confirm_slug != organization.slug:
            raise BusinessRuleViolation(
                "Tasdiq mos kelmadi. O'chirish uchun tashkilot slug'ini aynan kiriting."
            )

        if organization.is_active and not force:
            raise BusinessRuleViolation(
                "Faol tashkilotni o'chirib bo'lmaydi. Avval obunani bekor qiling."
            )

        cutoff = timezone.now() - timedelta(days=EXPORT_WINDOW_DAYS)
        if not force and organization.updated_at > cutoff:
            raise BusinessRuleViolation(
                f"Eksport oynasi hali tugamagan ({EXPORT_WINDOW_DAYS} kun). "
                f"Mijoz o'z ma'lumotini yuklab olish huquqiga ega."
            )

    deleted: dict[str, int] = {}
    with organization_context(organization.id):
        for path, lookup in DERIVED_PURGE.items():
            model = _model(path)
            manager = getattr(model, "all_objects", None) or model._default_manager
            count, _ = manager.filter(**{lookup: organization.id}).delete()
            if count:
                deleted[model._meta.db_table] = count

        for path in PURGE_ORDER:
            model = _model(path)
            manager = getattr(model, "all_objects", None) or model._default_manager
            count, _ = manager.filter(organization_id=organization.id).delete()
            if count:
                deleted[model._meta.db_table] = count

        # Audit jurnali — MIJOZ kontekstida, boshqa tenant jadvallari
        # bilan birga. U ham o'chiriladi: mijozning ma'lumotini o'chirib,
        # uning kim nima qilgani haqidagi yozuvlarini saqlab qolish
        # ma'nosiz — ular ham shaxsiy ma'lumot (ism, email, IP).
        #
        # **Nega platforma rejimida EMAS.** Avval shunday edi va u
        # ishlamasdi: `audit_log` siyosati platforma rejimida faqat
        # `organization_id IS NULL` qatorlarni ochadi (ADR-10 — vendor
        # mijozning audit yozuvlarini ko'rmaydi). Ya'ni `DELETE` hech
        # narsa topmasdi, XATO BERMASDI, va o'chirish oxirida
        # `organization.delete()` FK cheklovi bilan yiqilardi. Nosozlik
        # testlarda ko'rinmadi, chunki ular audit qatorsiz tashkilot
        # bilan ishlardi — amalda esa har bir kirish qator yozadi.
        deleted["audit_log"] = AuditLog.objects.filter(organization_id=organization.id).delete()[0]

    with platform_context():
        # `support_grant` — vendor tekisligining jadvali, shuning uchun
        # u platforma rejimida o'chiriladi.
        deleted["support_grant"] = SupportGrant.objects.filter(
            organization_id=organization.id
        ).delete()[0]
        # The self-signup that created this tenant (PLAN 6.7): personal data,
        # and it points at the organization with RESTRICT.
        deleted["platform_signup_request"] = SignupRequest.objects.filter(
            organization_id=organization.id
        ).delete()[0]

        slug = organization.slug
        name = organization.name
        organization.delete()
        deleted["organization"] = 1

        AuditLog.objects.create(
            organization=None,
            actor=None,
            actor_email=getattr(actor, "email", "") or "system",
            action="delete",
            entity_type="organization",
            entity_id=organization_id,
            changes={
                "slug": slug,
                "name": name,
                "forced": force,
                "deleted_rows": deleted,
            },
        )

    logger.warning("Tashkilot o'chirildi: %s (%s)", name, slug)
    return deleted
