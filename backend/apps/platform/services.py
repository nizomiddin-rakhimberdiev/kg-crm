"""
Platforma konsoli mantiqi (docs/04 §19).

Bu modul ikkita qat'iy chegarani ushlab turadi:

1. **Faqat metama'lumot.** Bu yerdagi hech bir funksiya bola, vasiy,
   to'lov, oylik yoki davomat qatorini qaytarmaydi. Faqat sonlar.
   RLS ham xuddi shuni bazada ta'minlaydi (docs/03 §6.3) — ya'ni bu
   qoida ikki joyda, mustaqil ravishda qo'llanadi.

2. **Kirish audit qilinadi.** Har bir platforma amali `audit_log` ga
   yoziladi. Ruxsat (`SupportGrant`) bilan bog'liq yozuvlar mijozning
   tashkilotiga biriktiriladi — ya'ni mijoz ularni ko'radi
   (`/audit-logs/platform-access`).
"""

from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context, platform_context
from apps.core.tenant_address import tenant_login_url
from apps.organizations.models import Organization
from apps.platform.models import GRANT_MAX_HOURS, PlatformUser, SupportGrant
from apps.subscriptions.models import (
    Subscription,
    SubscriptionInvoice,
    SubscriptionInvoiceStatus,
    SubscriptionStatus,
)

logger = logging.getLogger(__name__)

__all__ = [
    "organization_overview",
    "organization_detail",
    "expiring_work_list",
    "record_platform_action",
    "create_organization",
    "create_support_grant",
    "start_support_session",
    "revoke_support_grant",
    "active_grant",
    "extend_trial",
    "suspend_organization",
    "reactivate_organization",
]


# --- Audit ---


def record_platform_action(
    *,
    actor: PlatformUser,
    action: str,
    organization: Any = None,
    entity_type: str = "",
    entity_id: Any = None,
    changes: dict[str, Any] | None = None,
    request: Any = None,
) -> AuditLog:
    """
    Platforma amalini jurnalga yozadi.

    `organization` berilsa — yozuv **mijozga ko'rinadi**. Bu qasddan:
    vendor mijozning tashkilotiga tegsa, mijoz buni bilishi kerak. Faqat
    vendorga tegishli amallar (masalan plan versiyasi) `organization`
    siz yoziladi va mijozga ko'rinmaydi.
    """
    from apps.audit.services import client_ip

    payload = {
        "platform_user": str(actor.id),
        "platform_email": actor.email,
        **(changes or {}),
    }
    return AuditLog.objects.create(
        organization=organization,
        actor=None,  # vendor `accounts.User` emas — bu boshqa tekislik
        actor_email=actor.email,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        changes=payload,
        ip=client_ip(request) if request else None,
    )


# --- Metama'lumot ---


def organization_overview(*, search: str = "", status: str = "") -> list[dict[str, Any]]:
    """
    Barcha tashkilotlar — **faqat metama'lumot**.

    Bolalar soni bu yerda son sifatida keladi, ro'yxat sifatida emas.
    Farq katta: son biznesni boshqarish uchun kerak, ro'yxat esa hech
    qachon kerak emas va u sizib chiqadigan narsa (docs/04 §19).
    """
    with platform_context():
        queryset = Organization.objects.all()
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(slug__icontains=search))

        subscriptions = {
            subscription.organization_id: subscription
            for subscription in Subscription.all_objects.exclude(
                status=SubscriptionStatus.CANCELLED
            ).select_related("plan")
        }
        if status:
            allowed = {
                organization_id
                for organization_id, subscription in subscriptions.items()
                if subscription.status == status
            }
            queryset = queryset.filter(id__in=allowed)

        rows = []
        for organization in queryset.order_by("name"):
            subscription = subscriptions.get(organization.id)
            rows.append(
                {
                    "id": str(organization.id),
                    "name": organization.name,
                    "slug": organization.slug,
                    "contact_email": organization.contact_email,
                    "is_active": organization.is_active,
                    "created_at": organization.created_at.isoformat(),
                    "subscription": _subscription_summary(subscription),
                    "billable_children": _billable_children(organization.id),
                }
            )
    return rows


def _subscription_summary(subscription: Subscription | None) -> dict[str, Any] | None:
    if subscription is None:
        return None
    return {
        "status": subscription.status,
        "payment_term": subscription.payment_term,
        "discount_percent": str(subscription.discount_percent),
        "plan_code": subscription.plan.code,
        "trial_ends_at": (
            subscription.trial_ends_at.isoformat() if subscription.trial_ends_at else None
        ),
        "current_period_end": subscription.current_period_end.isoformat(),
    }


def _billable_children(organization_id: Any) -> int:
    """
    Bolalar SONI — ro'yxati emas.

    Bu so'rov tashkilot kontekstida bajariladi, chunki `child` jadvali
    platforma rejimida ko'rinmaydi (va ko'rinmasligi kerak). Ya'ni
    vendor sonni oladi, qatorlarni emas — hatto shu kodda ham.
    """
    from apps.reports.selectors import active_children_count

    with organization_context(organization_id):
        return active_children_count(organization_id=organization_id)


def organization_detail(*, organization_id: Any) -> dict[str, Any]:
    """Bitta tashkilot: obuna, o'lchov tarixi, hisoblar — metama'lumot."""
    from apps.subscriptions.models import UsageSnapshot

    with platform_context():
        organization = Organization.objects.filter(pk=organization_id).first()
        if organization is None:
            raise BusinessRuleViolation("Tashkilot topilmadi.")

        subscription = (
            Subscription.all_objects.filter(organization=organization)
            .exclude(status=SubscriptionStatus.CANCELLED)
            .select_related("plan")
            .first()
        )
        snapshots = (
            UsageSnapshot.all_objects.filter(organization=organization).order_by(
                "-period_year", "-period_month"
            )[:12]
            if subscription
            else []
        )
        invoices = SubscriptionInvoice.all_objects.filter(organization=organization).order_by(
            "-issued_at"
        )[:12]

        return {
            "id": str(organization.id),
            "name": organization.name,
            "slug": organization.slug,
            "contact_email": organization.contact_email,
            "contact_phone": organization.contact_phone,
            "is_active": organization.is_active,
            "created_at": organization.created_at.isoformat(),
            "subscription": _subscription_summary(subscription),
            "billable_children": _billable_children(organization.id),
            "usage_history": [
                {
                    "period": f"{row.period_year}-{row.period_month:02d}",
                    "peak_children": row.peak_children,
                    "billable_children": row.billable_children,
                    "method": row.measurement_method,
                    "closed": row.closed_at is not None,
                }
                for row in snapshots
            ],
            "invoices": [
                {
                    "number": invoice.number,
                    "status": invoice.status,
                    "issued_at": invoice.issued_at.isoformat(),
                    "due_at": invoice.due_at.isoformat(),
                    "total_amount": f"{invoice.total_amount:.2f}",
                }
                for invoice in invoices
            ],
        }


def expiring_work_list() -> dict[str, Any]:
    """
    Kunlik ish ro'yxati: tugayotgan sinovlar va muddati o'tgan hisoblar.

    Bu ekran solo asoschi uchun eng ko'p ishlatiladigan joy — "bugun
    kimga qo'ng'iroq qilish kerak?" degan savolga javob.
    """
    today = timezone.localdate()
    soon = timezone.now() + timedelta(days=5)

    with platform_context():
        trials = [
            {
                "organization": subscription.organization.name,
                "organization_id": str(subscription.organization_id),
                "trial_ends_at": subscription.trial_ends_at.isoformat(),
            }
            for subscription in Subscription.all_objects.filter(
                status=SubscriptionStatus.TRIALING, trial_ends_at__lte=soon
            ).select_related("organization")
        ]
        overdue = [
            {
                "organization": invoice.organization.name,
                "organization_id": str(invoice.organization_id),
                "number": invoice.number,
                "due_at": invoice.due_at.isoformat(),
                "total_amount": f"{invoice.total_amount:.2f}",
                "days_late": (today - invoice.due_at).days,
            }
            for invoice in SubscriptionInvoice.all_objects.filter(
                status__in=[
                    SubscriptionInvoiceStatus.ISSUED,
                    SubscriptionInvoiceStatus.OVERDUE,
                ],
                due_at__lt=today,
            ).select_related("organization")
        ]
        unpaid_total = SubscriptionInvoice.all_objects.filter(
            status__in=[SubscriptionInvoiceStatus.ISSUED, SubscriptionInvoiceStatus.OVERDUE]
        ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0")
        counts = Subscription.all_objects.exclude(status=SubscriptionStatus.CANCELLED).aggregate(
            total=Count("id"),
            trialing=Count("id", filter=Q(status=SubscriptionStatus.TRIALING)),
            active=Count("id", filter=Q(status=SubscriptionStatus.ACTIVE)),
            suspended=Count("id", filter=Q(status=SubscriptionStatus.SUSPENDED)),
        )

    return {
        "trials_ending": sorted(trials, key=lambda row: row["trial_ends_at"]),
        "overdue_invoices": sorted(overdue, key=lambda row: -row["days_late"]),
        "unpaid_total": f"{unpaid_total:.2f}",
        "counts": counts,
    }


# --- Mijoz ochish ---


@transaction.atomic
def create_organization(
    *,
    actor: PlatformUser,
    organization_name: str,
    contact_email: str,
    full_name: str,
    password: str,
    contact_phone: str = "",
    branch_name: str = "",
    slug: str = "",
    request: Any = None,
) -> dict[str, Any]:
    """
    Yangi mijozni VENDOR ochadi — ochiq ro'yxatdan o'tish o'rniga.

    Nega ochiq `/auth/signup` olib tashlandi: har bir signup haqiqiy
    tenant yaratadi — RLS siyosatlari, obuna yozuvi, rollar, SMS
    shablonlari. Va ADR-11 bo'yicha mijoz ma'lumoti hech qachon
    o'chirilmaydi. Ya'ni internetdan kelgan tasodifiy tashrif bazada
    abadiy qoladigan tenant qoldirardi. Bu biznes modeliga ham mos
    kelmasdi: mijozlar yuridik shaxs va schyot-faktura orqali to'laydi,
    ya'ni tenant sotuv suhbatidan KEYIN paydo bo'lishi kerak.

    Sinov muddati SHU PAYTDAN boshlanadi (`start_trial`), shuning uchun
    akkauntni mijoz haqiqatan boshlashga tayyor bo'lganda oching.
    """
    from apps.accounts.services import register_organization

    result = register_organization(
        organization_name=organization_name,
        contact_email=contact_email,
        full_name=full_name,
        password=password,
        contact_phone=contact_phone,
        branch_name=branch_name or None,
        slug=slug or None,
    )

    # Yozuv MIJOZNING tashkilotiga biriktiriladi: bog'cha o'z audit
    # jurnalida "akkauntni vendor ochdi" faktini ko'rishi kerak.
    with organization_context(result.organization.id):
        record_platform_action(
            actor=actor,
            action="create",
            organization=result.organization,
            entity_type="organization",
            entity_id=result.organization.id,
            changes={"name": result.organization.name, "slug": result.organization.slug},
            request=request,
        )

    return {
        "id": str(result.organization.id),
        "name": result.organization.name,
        "slug": result.organization.slug,
        "login_url": tenant_login_url(result.organization.slug),
        "owner_email": result.owner.email,
        "branch": result.branch.name,
    }


# --- Ruxsatlar ---


@transaction.atomic
def create_support_grant(
    *,
    actor: PlatformUser,
    organization_id: Any,
    reason: str,
    hours: int = 2,
    request: Any = None,
) -> SupportGrant:
    """
    Vaqt bilan cheklangan operatsion kirish ruxsatini yaratadi.

    Sabab MAJBURIY va u kirishdan oldin yoziladi. Yozuv mijozning
    tashkilotiga biriktiriladi, ya'ni u `/audit-logs/platform-access`
    da darhol ko'rinadi.
    """
    if not reason.strip():
        raise BusinessRuleViolation("Ruxsat uchun sabab majburiy.")
    if hours < 1 or hours > GRANT_MAX_HOURS:
        raise BusinessRuleViolation(f"Muddat 1–{GRANT_MAX_HOURS} soat oralig'ida bo'lishi kerak.")

    with platform_context():
        organization = Organization.objects.filter(pk=organization_id).first()
        if organization is None:
            raise BusinessRuleViolation("Tashkilot topilmadi.")

        grant = SupportGrant.objects.create(
            organization=organization,
            platform_user=actor,
            reason=reason.strip(),
            expires_at=SupportGrant.default_expiry(hours),
        )

    with organization_context(organization.id):
        record_platform_action(
            actor=actor,
            action="create",
            organization=organization,
            entity_type="support_grant",
            entity_id=grant.id,
            changes={"reason": grant.reason, "expires_at": grant.expires_at.isoformat()},
            request=request,
        )
    return grant


def start_support_session(
    *, actor: PlatformUser, organization_id: Any, request: Any = None
) -> dict[str, Any]:
    """
    Amaldagi ruxsat asosida mijoz ilovasiga KIRISH tokenini beradi.

    Bu — `SupportGrant` ning yetishmayotgan yarmi edi. Ruxsat yozilardi,
    mijoz uni ko'rardi, lekin u hech qanday kirish bermasdi: `active_grant()`
    ishlab chiqarish kodida umuman chaqirilmasdi. Natijada qo'llab-quvvatlash
    uchun yagona amaliy yo'l mijozning parolini bilish bo'lib qolgandi —
    ya'ni audit jurnali vendor amalini bog'chaning O'Z egasi deb
    yozadigan, va bitta noutbuk barcha bog'chalarning kalitini
    saqlaydigan holat.

    Sessiya egasining hisobi orqali ochiladi, chunki u tashkilotdagi
    hamma narsani ko'radi — muammoni ko'rish uchun aynan shu kerak.
    Yozish esa `TenantJWTAuthentication` da bloklanadi.

    Har bir kirish MIJOZNING audit jurnaliga yoziladi: ruxsat berilgani
    emas, aynan KIRILGANI ko'rinishi kerak.
    """
    from apps.accounts.authentication import issue_support_token
    from apps.accounts.models import User
    from apps.core.tenant_address import tenant_base_url

    grant = active_grant(platform_user=actor, organization_id=organization_id)
    if grant is None:
        raise BusinessRuleViolation(
            "Amaldagi ruxsat yoʻq. Avval sabab koʻrsatib kirish ruxsatini oling."
        )

    with platform_context():
        organization = Organization.objects.filter(pk=organization_id).first()
    if organization is None:
        raise BusinessRuleViolation("Tashkilot topilmadi.")

    with organization_context(organization.id):
        owner = (
            User.objects.filter(role__code="org_owner", is_active=True)
            .select_related("organization", "role", "branch")
            .order_by("created_at")
            .first()
        )
        if owner is None:
            raise BusinessRuleViolation("Bog'chada faol egasi hisobi topilmadi.")

        token = issue_support_token(
            user=owner,
            platform_user_id=actor.id,
            grant_id=grant.id,
            expires_at=grant.expires_at,
        )

        record_platform_action(
            actor=actor,
            action="login",
            organization=organization,
            entity_type="support_session",
            entity_id=grant.id,
            changes={"reason": grant.reason},
            request=request,
        )

    return {
        "access": token,
        "organization": organization.name,
        "slug": organization.slug,
        "app_url": tenant_base_url(organization.slug),
        "grant_expires_at": grant.expires_at.isoformat(),
        "read_only": True,
    }


def revoke_support_grant(
    *, actor: PlatformUser, grant: SupportGrant, request: Any = None
) -> SupportGrant:
    with platform_context():
        grant.revoked_at = timezone.now()
        grant.save(update_fields=["revoked_at"])
        organization = grant.organization

    with organization_context(organization.id):
        record_platform_action(
            actor=actor,
            action="update",
            organization=organization,
            entity_type="support_grant",
            entity_id=grant.id,
            changes={"revoked": True},
            request=request,
        )
    return grant


def active_grant(*, platform_user: PlatformUser, organization_id: Any) -> SupportGrant | None:
    """Amaldagi ruxsat yoki `None`."""
    with platform_context():
        return (
            SupportGrant.objects.filter(
                platform_user=platform_user,
                organization_id=organization_id,
                revoked_at__isnull=True,
                expires_at__gt=timezone.now(),
            )
            .order_by("-created_at")
            .first()
        )


# --- Tashkilot amallari ---


def _load_subscription(organization_id: Any) -> tuple[Organization, Subscription]:
    with platform_context():
        organization = Organization.objects.filter(pk=organization_id).first()
        if organization is None:
            raise BusinessRuleViolation("Tashkilot topilmadi.")
        subscription = (
            Subscription.all_objects.filter(organization=organization)
            .exclude(status=SubscriptionStatus.CANCELLED)
            .first()
        )
        if subscription is None:
            raise BusinessRuleViolation("Bu tashkilotda faol obuna yo'q.")
        return organization, subscription


def extend_trial(
    *, actor: PlatformUser, organization_id: Any, days: int, reason: str, request: Any = None
) -> Subscription:
    """Sinovni uzaytiradi — sabab majburiy."""
    if not reason.strip():
        raise BusinessRuleViolation("Uzaytirish uchun sabab majburiy.")
    if days < 1 or days > 30:
        raise BusinessRuleViolation("Uzaytirish 1–30 kun oralig'ida bo'lishi kerak.")

    organization, subscription = _load_subscription(organization_id)
    if subscription.status != SubscriptionStatus.TRIALING:
        raise BusinessRuleViolation("Faqat sinov davridagi obunani uzaytirish mumkin.")

    previous = subscription.trial_ends_at
    with organization_context(organization.id):
        subscription.trial_ends_at = (previous or timezone.now()) + timedelta(days=days)
        subscription.save(update_fields=["trial_ends_at", "updated_at"])
        record_platform_action(
            actor=actor,
            action="update",
            organization=organization,
            entity_type="subscription",
            entity_id=subscription.id,
            changes={
                "trial_extended_days": days,
                "reason": reason.strip(),
                "from": previous.isoformat() if previous else None,
                "to": subscription.trial_ends_at.isoformat(),
            },
            request=request,
        )
    return subscription


def suspend_organization(
    *, actor: PlatformUser, organization_id: Any, reason: str, request: Any = None
) -> Subscription:
    """
    Obunani to'xtatadi — mijoz faqat o'qish rejimiga o'tadi.

    Ma'lumot O'CHIRILMAYDI va yashirilmaydi (docs/03 §20.6). Bu amal
    qaytariladigan bo'lishi shart, chunki to'lamaslik vaqtinchalik
    holat.
    """
    if not reason.strip():
        raise BusinessRuleViolation("To'xtatish uchun sabab majburiy.")

    organization, subscription = _load_subscription(organization_id)
    with organization_context(organization.id):
        subscription.status = SubscriptionStatus.SUSPENDED
        subscription.save(update_fields=["status", "updated_at"])
        record_platform_action(
            actor=actor,
            action="update",
            organization=organization,
            entity_type="subscription",
            entity_id=subscription.id,
            changes={"suspended": True, "reason": reason.strip()},
            request=request,
        )
    return subscription


def reactivate_organization(
    *, actor: PlatformUser, organization_id: Any, request: Any = None
) -> Subscription:
    organization, subscription = _load_subscription(organization_id)
    with organization_context(organization.id):
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.save(update_fields=["status", "updated_at"])
        record_platform_action(
            actor=actor,
            action="update",
            organization=organization,
            entity_type="subscription",
            entity_id=subscription.id,
            changes={"reactivated": True},
            request=request,
        )
    return subscription
