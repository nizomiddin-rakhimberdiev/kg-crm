"""
Identity domenining biznes mantiqi — mutatsiyalar FAQAT shu yerda (P3).

Views yupqa: ular so'rovni tekshiradi va shu funksiyalarni chaqiradi.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext

from apps.accounts.constants import (
    ACTIONS,
    EXTRA_ACTIONS,
    MODULES,
    PERMISSION_LABELS,
    ROLE_MATRIX,
    SYSTEM_ROLES,
)
from apps.accounts.models import Permission, RefreshToken, Role, RolePermission, User
from apps.branches.models import Branch
from apps.core.deployment import is_saas
from apps.core.exceptions import BusinessRuleViolation
from apps.core.features import enabled_features
from apps.core.tenancy import organization_context, platform_context
from apps.organizations.models import Organization

__all__ = [
    "sync_permission_catalog",
    "seed_system_roles",
    "register_organization",
    "subscription_payload",
    "create_user",
    "store_refresh_token",
    "revoke_refresh_token",
    "hash_token",
]


# --- Permission katalogi ---


def sync_permission_catalog() -> int:
    """
    `MODULES × ACTIONS` katalogini bazaga moslashtiradi.

    Idempotent: migratsiyada ham, boshqaruv buyrug'ida ham xavfsiz chaqiriladi.
    """
    existing = set(Permission.objects.values_list("code", flat=True))
    new = [
        Permission(
            code=f"{module}.{action}",
            module=module,
            action=action,
            label=f"{PERMISSION_LABELS.get(module, module)} — {action}",
        )
        for module in MODULES
        # `EXTRA_ACTIONS` — faqat ayrim modullarda ma'noga ega amallar
        # (`children.read_all`), ya'ni katalog keraksiz qatorlar bilan
        # shishmaydi.
        for action in (*ACTIONS, *EXTRA_ACTIONS.get(module, ()))
        if f"{module}.{action}" not in existing
    ]
    Permission.objects.bulk_create(new)
    return len(new)


@transaction.atomic
def seed_system_roles(organization: Organization) -> dict[str, Role]:
    """
    Tashkilot uchun 5 ta tizim rolini va ularning ruxsatlarini yaratadi.

    Matritsa `constants.ROLE_MATRIX` da — ya'ni ruxsatlar **ma'lumot**, kod
    emas. Yangi rol qo'shish migratsiya emas, konfiguratsiya o'zgarishi
    (docs/02 §11.3).
    """
    permissions = {p.code: p for p in Permission.objects.all()}
    roles: dict[str, Role] = {}

    for code, name in SYSTEM_ROLES.items():
        role, _ = Role.all_objects.get_or_create(
            organization=organization,
            code=code,
            branch=None,
            defaults={"name": name, "is_system": True},
        )
        roles[code] = role

        # Matritsa `read_all` ni hamma modulga beradi, lekin u faqat
        # `EXTRA_ACTIONS` da e'lon qilinganlarida mavjud — qolganlari
        # shu yerda tushib qoladi.
        wanted = {
            f"{module}.{action}"
            for module, allowed in ROLE_MATRIX[code].items()
            for action in allowed
            if action in ACTIONS or action in EXTRA_ACTIONS.get(module, ())
        }
        current = set(
            RolePermission.objects.filter(role=role).values_list("permission__code", flat=True)
        )
        RolePermission.objects.bulk_create(
            [
                RolePermission(role=role, permission=permissions[c])
                for c in sorted(wanted - current)
                if c in permissions
            ]
        )
    return roles


# --- Onboarding ---


@dataclass(frozen=True)
class RegistrationResult:
    organization: Organization
    branch: Branch
    owner: User


@transaction.atomic
def register_organization(
    *,
    organization_name: str,
    contact_email: str,
    full_name: str,
    # `None` — parol O'RNATILMAYDI (PLAN 5.5): egaga taklif havolasi
    # ketadi va u parolni o'zi tanlaydi. Vendor mijozning parolini
    # bilmasligi kerak — aks holda "biz mijoz ma'lumotini ko'rmaymiz"
    # (ADR-10) degan da'vo ishonchsiz bo'lib qoladi.
    password: str | None = None,
    contact_phone: str = "",
    branch_name: str | None = None,
    slug: str | None = None,
) -> RegistrationResult:
    """
    Yangi mijozni ro'yxatdan o'tkazadi: tashkilot + birinchi filial +
    Org Owner + seed qilingan rollar.

    Bitta tranzaksiyada: yarim yaratilgan tashkilot — kirib bo'lmaydigan,
    lekin mavjud bo'lgan tenant degani, va uni qo'lda tozalash kerak bo'ladi.

    Sinov obunasi shu tranzaksiyada ochiladi: obunasiz tashkilot —
    hisob-kitobi yo'q mijoz degani, va uni keyin qo'lda tuzatish kerak
    bo'lardi.
    """
    # Tashkilot yaratish — PLATFORMA tekisligidagi amal: o'sha paytda
    # hali hech qanday tenant yo'q, va `slug` global unikallik butun
    # baza bo'ylab tekshiriladi. RLS buni ochiq so'rashga majbur qiladi
    # (docs/03 §6.3) — va bu to'g'ri: cross-tenant amal kodda ko'rinib
    # tursin.
    with platform_context():
        slug = _unique_slug(organization_name) if slug is None else _checked_slug(slug)
        organization = Organization.objects.create(
            name=organization_name.strip(),
            slug=slug,
            contact_email=contact_email,
            contact_phone=contact_phone,
        )

    with organization_context(organization.id):
        branch = Branch.objects.create(
            organization=organization,
            name=branch_name or organization_name.strip(),
            code="MAIN",
        )

        # Birinchi filialning pul qoplari (ADR-17) — ro'yxatdan o'tish
        # tranzaksiyasi ichida, chunki qopsiz bog'cha birinchi to'lovni
        # qayerga yozishni bilmaydi.
        from apps.cash.services import ensure_branch_accounts

        ensure_branch_accounts(branch=branch)
        sync_permission_catalog()
        roles = seed_system_roles(organization)

        # Boshlang'ich SMS shablonlari — bog'cha ularni tahrirlashi
        # mumkin; matn mahsulot qarori emas, mijoz qarori.
        from apps.notifications.services import seed_default_templates

        seed_default_templates(organization)

        owner = User.objects.create_user(
            email=contact_email,
            password=password,
            full_name=full_name,
            phone=contact_phone,
            organization=organization,
            role=roles["org_owner"],
            branch=None,  # Org Owner barcha filiallarni ko'radi
        )
        if not password:
            # Parolsiz hisob KIRISHGA YARAMAYDI: `set_unusable_password`
            # tekshirishda hech qachon mos kelmaydigan qiymat yozadi.
            # Bo'sh parol qoldirish esa `check_password("")` ni
            # ishlatib qo'yish xavfini tug'dirardi.
            owner.set_unusable_password()
            owner.save(update_fields=["password", "updated_at"])

        # 15 kunlik sinov — karta so'ralmaydi (docs/01 §4.4).
        #
        # Standalone nusxada obuna ochilmaydi (ADR-13): tizim bir marta
        # sotilgan, sinov muddati ham, hisob-faktura ham yo'q. Obunasiz
        # tashkilotni `SubscriptionWriteGate` allaqachon ochiq qoldiradi.
        if is_saas():
            from apps.subscriptions.services import start_trial

            start_trial(organization=organization)

    return RegistrationResult(organization=organization, branch=branch, owner=owner)


def _unique_slug(name: str) -> str:
    base = slugify(name)[:40] or "org"
    slug = base
    # `slug` global unikal (docs/03 §10.1) — shuning uchun unscoped tekshiruv.
    while Organization.objects.filter(slug=slug).exists():
        slug = f"{base}-{secrets.token_hex(3)}"
    return slug


# Band nomlar — bugun emas, ERTAGA kerak bo'ladigan ro'yxat.
#
# Bugun mijoz manzili `/t/<slug>` ko'rinishida va prefiks tufayli hech
# qanday to'qnashuv yo'q. Lekin subdomenga o'tilganda (`<slug>.kg-crm.uz`)
# bu nomlar to'g'ridan-to'g'ri infratuzilma bilan urishadi: `www` saytni,
# `api` backendni, `mail` pochtani sindiradi. O'shanda ro'yxatni qo'shish
# KECH bo'ladi — mijoz allaqachon o'sha slug bilan ishlab turgan bo'ladi
# va uni ko'chirish havolalarini sindiradi.
RESERVED_SLUGS: frozenset[str] = frozenset(
    {
        "admin",
        "api",
        "app",
        "assets",
        "auth",
        "billing",
        "blog",
        "cdn",
        "dashboard",
        "dev",
        "docs",
        "ftp",
        "help",
        "login",
        "mail",
        "media",
        "new",
        "platform",
        "pricing",
        "root",
        "signup",
        "static",
        "status",
        "support",
        "t",
        "test",
        "www",
    }
)


def _checked_slug(slug: str) -> str:
    """
    Vendor tanlagan slug'ni tekshiradi.

    Slug — mijozning MANZILI. U havolalarga, hisob-fakturalarga va SMS
    matnlariga tushadi, ya'ni keyin o'zgartirish eski havolalarni
    sindiradi. Shuning uchun tekshiruv yaratish paytida qat'iy: keyin
    tuzatib bo'lmaydigan narsa oldindan tekshiriladi.
    """
    candidate = slugify(slug)[:50]
    if not candidate:
        raise BusinessRuleViolation(gettext("Manzil (slug) boʻsh boʻlishi mumkin emas."))
    if candidate in RESERVED_SLUGS:
        raise BusinessRuleViolation(
            gettext("'{candidate}' — band nom, boshqasini tanlang.").format(candidate=candidate)
        )
    if Organization.objects.filter(slug=candidate).exists():
        raise BusinessRuleViolation(
            gettext("'{candidate}' allaqachon band.").format(candidate=candidate)
        )
    return candidate


@transaction.atomic
def create_user(
    *,
    organization: Organization,
    email: str,
    password: str,
    full_name: str,
    role: Role,
    branch: Branch | None = None,
    phone: str = "",
) -> User:
    """Tashkilot ichida yangi foydalanuvchi yaratadi."""
    if role.organization_id != organization.id:
        # Bu holat faqat kod xatosi bo'lishi mumkin — serializer roldan
        # oldin tenant filtridan o'tkazadi. Baribir tekshiramiz.
        raise BusinessRuleViolation(gettext("Rol boshqa tashkilotga tegishli."))

    if branch is not None and branch.organization_id != organization.id:
        raise BusinessRuleViolation(gettext("Filial boshqa tashkilotga tegishli."))

    if role.code != "org_owner" and branch is None:
        raise BusinessRuleViolation(
            gettext("Org Ownerʼdan boshqa barcha rollar uchun filial koʻrsatilishi shart.")
        )

    return User.objects.create_user(
        email=email,
        password=password,
        full_name=full_name,
        phone=phone,
        organization=organization,
        role=role,
        branch=branch,
    )


# --- Refresh token ---


def hash_token(raw: str) -> str:
    """Token xom holda saqlanmaydi — faqat SHA-256 hash."""
    return hashlib.sha256(raw.encode()).hexdigest()


def store_refresh_token(
    *,
    user: User,
    raw_token: str,
    lifetime: timedelta,
    user_agent: str = "",
    ip: str | None = None,
) -> RefreshToken:
    return RefreshToken.objects.create(
        user=user,
        token_hash=hash_token(raw_token),
        expires_at=timezone.now() + lifetime,
        user_agent=user_agent[:255],
        ip=ip,
    )


def revoke_refresh_token(raw_token: str) -> bool:
    """Logout va rotatsiyada chaqiriladi. Qaytadi: yozuv topildimi."""
    updated = RefreshToken.objects.filter(
        token_hash=hash_token(raw_token), revoked_at__isnull=True
    ).update(revoked_at=timezone.now())
    return bool(updated)


def revoke_all_refresh_tokens(user: User) -> int:
    """Parol o'zgarganda yoki foydalanuvchi o'chirilganda barcha sessiyani yopadi."""
    return RefreshToken.objects.filter(user=user, revoked_at__isnull=True).update(
        revoked_at=timezone.now()
    )


def touch_last_login(user: User) -> None:
    User.objects.filter(pk=user.pk).update(last_login_at=timezone.now())


def subscription_payload(organization: Any) -> dict[str, Any]:
    """
    Frontend uchun obuna holati (docs/04 §5).

    `read_only` shu yerdan keladi, chunki UI uni har bir tugmada
    tekshiradi. Bu **UX**, xavfsizlik emas: haqiqiy to'siq backend'dagi
    `SubscriptionWriteGate` va u `402` qaytaradi.

    Kontekst SHU YERDA o'rnatiladi, chaqiruvchida emas. Sabab: signup va
    login javoblarida bu funksiya `organization_context` blokidan
    TASHQARIDA chaqirilardi, va RLS ostida so'rov jimgina bo'sh
    qaytardi — obuna bazada bor, javobda esa `null`. Xato chiqmasdi,
    shunchaki sinov banneri hech qachon ko'rinmasdi.

    Chaqiruv joylarini tuzatish yetarli emasdi: keyingi chaqiruv ham
    xuddi shunday adashardi. Kontekstni funksiyaning o'ziga ko'chirish
    esa bu xatoni umuman mumkin bo'lmagan holga keltiradi.
    """
    from apps.subscriptions.models import Subscription, SubscriptionStatus

    empty = {"status": None, "read_only": False, "trial_ends_at": None, "amount_due": None}
    if organization is None:
        return empty

    from apps.subscriptions.models import SubscriptionInvoice, SubscriptionInvoiceStatus

    with organization_context(organization.id):
        subscription = (
            Subscription.objects.exclude(status=SubscriptionStatus.CANCELLED)
            .only("status", "trial_ends_at")
            .first()
        )
        if subscription is None:
            return empty

        # To'lanmagan hisoblarning SUMMASI (PLAN 4.9). Banner "to'lov
        # kutilmoqda" deb aytib, qancha ekanini aytmasa, mijoz
        # baribir boshqa ekranga o'tishi kerak bo'ladi — ya'ni
        # banner ishini bajarmagan bo'ladi.
        unpaid = SubscriptionInvoice.objects.filter(
            status__in=[
                SubscriptionInvoiceStatus.ISSUED,
                SubscriptionInvoiceStatus.OVERDUE,
            ]
        ).aggregate(total=Sum("total_amount"))["total"]

    return {
        "status": subscription.status,
        "read_only": subscription.is_read_only,
        "trial_ends_at": (
            subscription.trial_ends_at.isoformat() if subscription.trial_ends_at else None
        ),
        # Satr sifatida: pul JSON'da `float` bo'lib ketmasligi kerak
        # (CLAUDE.md, invariant 3).
        "amount_due": str(unpaid) if unpaid else None,
    }


def user_payload(user: User) -> dict[str, Any]:
    """`/auth/me` va login javoblari uchun yagona shakl (docs/04 §5)."""
    return {
        "id": str(user.id),
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        # Rasm bo'lmasa `None` — frontend bosh harflarga qaytadi.
        "photo_url": user.photo.url if user.photo else None,
        "role": ({"code": user.role.code, "name": user.role.name} if user.role else None),
        "organization": (
            {
                "id": str(user.organization.id),
                "name": user.organization.name,
                "slug": user.organization.slug,
                # Logotip SHU YERDA (PLAN 4.6): u har sahifaning
                # sarlavhasida ko'rinadi, `/organization` esa
                # `settings.read` talab qiladi — tarbiyachi uni
                # o'qiy olmaydi va belgi faqat ba'zi rollarda
                # ko'rinardi.
                "logo_url": (user.organization.logo.url if user.organization.logo else None),
            }
            if user.organization
            else None
        ),
        "branch": ({"id": str(user.branch.id), "name": user.branch.name} if user.branch else None),
        "permissions": sorted(user.permission_codes()),
        # 2FA holati (PLAN 5.4): sozlamalar ekrani buni ko'rsatishi
        # kerak, va u ALOHIDA so'rov bilan olinmaydi — "yoqilganmi?"
        # degan savol profil bilan birga keladi. Sir yoki kodlar
        # javobga TUSHMAYDI: bu yerda faqat holat.
        "two_factor": user.has_2fa,
        "backup_codes_left": len(user.totp_backup_codes or []) if user.has_2fa else 0,
        # Switched-on product modules (apps/core/features.py) — the screens
        # follow the same switch as the endpoints.
        "features": enabled_features(),
    }
