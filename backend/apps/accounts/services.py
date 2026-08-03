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
from django.utils import timezone
from django.utils.text import slugify

from apps.accounts.constants import (
    ACTIONS,
    MODULES,
    PERMISSION_LABELS,
    ROLE_MATRIX,
    SYSTEM_ROLES,
)
from apps.accounts.models import Permission, RefreshToken, Role, RolePermission, User
from apps.branches.models import Branch
from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context
from apps.organizations.models import Organization

__all__ = [
    "sync_permission_catalog",
    "seed_system_roles",
    "register_organization",
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
        for action in ACTIONS
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

        wanted = {
            f"{module}.{action}"
            for module, allowed in ROLE_MATRIX[code].items()
            for action in allowed
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
    password: str,
    contact_phone: str = "",
    branch_name: str | None = None,
) -> RegistrationResult:
    """
    Yangi mijozni ro'yxatdan o'tkazadi: tashkilot + birinchi filial +
    Org Owner + seed qilingan rollar.

    Bitta tranzaksiyada: yarim yaratilgan tashkilot — kirib bo'lmaydigan,
    lekin mavjud bo'lgan tenant degani, va uni qo'lda tozalash kerak bo'ladi.

    Obuna (`trialing`) Sprint 10 da shu yerga qo'shiladi (docs/03 §20.2).
    """
    slug = _unique_slug(organization_name)

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
        sync_permission_catalog()
        roles = seed_system_roles(organization)

        owner = User.objects.create_user(
            email=contact_email,
            password=password,
            full_name=full_name,
            phone=contact_phone,
            organization=organization,
            role=roles["org_owner"],
            branch=None,  # Org Owner barcha filiallarni ko'radi
        )

    return RegistrationResult(organization=organization, branch=branch, owner=owner)


def _unique_slug(name: str) -> str:
    base = slugify(name)[:40] or "org"
    slug = base
    # `slug` global unikal (docs/03 §10.1) — shuning uchun unscoped tekshiruv.
    while Organization.objects.filter(slug=slug).exists():
        slug = f"{base}-{secrets.token_hex(3)}"
    return slug


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
        raise BusinessRuleViolation("Rol boshqa tashkilotga tegishli.")

    if branch is not None and branch.organization_id != organization.id:
        raise BusinessRuleViolation("Filial boshqa tashkilotga tegishli.")

    if role.code != "org_owner" and branch is None:
        raise BusinessRuleViolation(
            "Org Owner'dan boshqa barcha rollar uchun filial ko'rsatilishi shart."
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


def user_payload(user: User) -> dict[str, Any]:
    """`/auth/me` va login javoblari uchun yagona shakl (docs/04 §5)."""
    return {
        "id": str(user.id),
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "role": ({"code": user.role.code, "name": user.role.name} if user.role else None),
        "organization": (
            {
                "id": str(user.organization.id),
                "name": user.organization.name,
                "slug": user.organization.slug,
            }
            if user.organization
            else None
        ),
        "branch": ({"id": str(user.branch.id), "name": user.branch.name} if user.branch else None),
        "permissions": sorted(user.permission_codes()),
    }
