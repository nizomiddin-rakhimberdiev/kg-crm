"""
Maxsus User modeli (ADR-4).

Sprint 0 da ataylab **minimal**: faqat model va manager. Rol, permission,
JWT va auth endpointlari Sprint 1 da qo'shiladi.

Nega Sprint 0 da: `AUTH_USER_MODEL` ni keyinroq almashtirish Django'da eng
og'riqli migratsiyalardan biri, va `core.BaseModel` dagi `created_by` FK
allaqachon user modeliga tayanadi. `organization_id` bilan bir xil mantiq —
poydevorni bir marta to'g'ri qo'yish arzon, keyin tuzatish qimmat.
"""

from __future__ import annotations

import uuid
from pathlib import PurePosixPath
from typing import Any

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.core.managers import TenantManager, UnscopedManager
from apps.core.models import BaseModel, TenantScopedModel

__all__ = ["User", "Role", "Permission", "RolePermission", "RefreshToken"]


def user_photo_path(instance: User, filename: str) -> str:
    """
    `media/{organization}/avatars/{uuid}.{ext}`

    Fayl nomi UUID: yuklangan nom saqlansa, u (a) boshqa mijozning fayl
    nomini taxmin qilish yo'lini ochadi va (b) bir xil nomli fayllar
    to'qnashuviga olib keladi. Kengaytma esa saqlanadi — brauzer uni
    `Content-Type` aniqlashda ishlatadi.
    """
    suffix = PurePosixPath(filename).suffix.lower() or ".jpg"
    organization = instance.organization_id or "platform"
    return f"{organization}/avatars/{uuid.uuid4()}{suffix}"


class UserManager(TenantManager, BaseUserManager["User"]):  # type: ignore[misc]
    """
    `User` ning **default** manageri — tenant bilan cheklangan.

    Nega scoped: `/users` endpointi shu manager ustida ishlaydi va tenant
    filtri baza qatlamida bo'lmasa, uni yozishni unutish mumkin. Aynan shu
    unutish cross-tenant sweep testida ushlandi.

    Login esa tashkilotlar bo'ylab qidirishi shart (email tashkilot ichida
    unikal), shuning uchun u `User.auth_objects` dan foydalanadi — aniq,
    ataylab va `grep auth_objects` bilan topiladigan chiqish yo'li.

    `create_user`/`create_superuser` queryset qurmaydi, shuning uchun ular
    tenant kontekstisiz ham ishlaydi (masalan `createsuperuser` buyrug'i).
    """

    use_in_migrations = True

    def create_user(self, email: str, password: str | None = None, **extra: Any) -> User:
        if not email:
            raise ValueError("Email majburiy.")
        user = self.model(email=self.normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra: Any) -> User:
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        if extra.get("is_superuser") is not True:
            raise ValueError("Superuser uchun is_superuser=True bo'lishi kerak.")
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    """
    Tizim foydalanuvchisi — har doim bitta tashkilotga tegishli.

    `organization` `null=True`: platforma (vendor) xodimlari uchun — ular
    hech qanday tenant'ga tegishli emas va shuning uchun hech qanday tenant
    ma'lumotini ko'rmaydi (ADR-10). Ular Sprint 11 da `platform` app'ida
    to'liq ishlanadi.
    """

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.RESTRICT,
        related_name="users",
        null=True,
        blank=True,
        editable=False,
    )

    email = models.EmailField()
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)

    # Profil rasmi. `upload_to` tashkilot bo'yicha ajratilgan (docs/02 §16.2)
    # va fayl nomi UUID: original nom saqlanmaydi, chunki u fayl tizimida
    # taxmin qilish va nizolar manbai bo'ladi.
    #
    # `null=True` YO'Q (Django konvensiyasi matnli maydonlar uchun): Django
    # baribir bo'sh qiymatni `''` qilib yozadi, `null=True` esa "bo'sh"ning
    # ikkinchi ko'rinishini yaratardi — xotirada `None`, bazada `''`. Aynan
    # shu nomuvofiqlikni cross-tenant sweep testi ushladi.
    photo = models.ImageField(upload_to=user_photo_path, blank=True)
    # Xodimning Telegram'i (Bosqich 13.3c): chiqimni bot orqali kiritish va
    # (13.4) egaga darhol xabarlar. Kod tashkilotni ichida olib yuradi —
    # ota-ona havolasi bilan bir xil yo'l (ADR-23), oldida `s_`.
    telegram_chat_id = models.CharField(max_length=32, blank=True, db_index=True)
    telegram_code = models.CharField(max_length=48, blank=True)
    telegram_linked_at = models.DateTimeField(null=True, blank=True)

    role = models.ForeignKey(
        "accounts.Role",
        on_delete=models.RESTRICT,
        related_name="users",
        null=True,
        blank=True,
    )
    # `null=True` — faqat Org Owner va platforma xodimlari uchun.
    # Qolgan rollar uchun majburiyligi `clean()` va servis qatlamida
    # tekshiriladi (rol kodiga bog'liq shart FK bilan ifodalanmaydi).
    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.RESTRICT,
        related_name="users",
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    last_login_at = models.DateTimeField(null=True, blank=True)

    # --- Ikki bosqichli tasdiqlash (PLAN 5.4, ADR-24) ---
    #
    # Mijoz tomonida 2FA **IXTIYORIY** va har bir foydalanuvchi uni
    # o'zi yoqadi. Majburiy qilish bog'chada ish bermaydi: smenada
    # ishlaydigan tarbiyachida shaxsiy smartfon bo'lmasligi mumkin va
    # majburiy kod ularni bitta umumiy telefonga o'tishga majburlardi
    # — ya'ni audit izi "kim kirdi" degan savolga javob bermay
    # qolardi.
    #
    # `totp_confirmed_at` ALOHIDA maydon: sir yaratilgani 2FA
    # yoqilgani degani emas. Odam QR'ni ko'rib, ilovaga qo'shmasdan
    # sahifani yopsa va biz sirni "yoqilgan" deb hisoblasak, u
    # keyingi kirishda o'z hisobidan chiqib qolardi.
    totp_secret = models.CharField(max_length=64, blank=True)
    totp_confirmed_at = models.DateTimeField(null=True, blank=True)
    # Zaxira kodlarining XESHLARI (`core/backup_codes.py`). Alohida
    # jadval EMAS, va bu ataylab: kodni tekshirish kirish paytida,
    # ya'ni tenant konteksti hali yo'q holatda bo'ladi
    # (`auth_lookup_context()`). Yangi jadval uchun tor eshikni
    # kengaytirish kerak bo'lardi — RLS siyosatini qulaylik uchun
    # bo'shatish esa eng yomon almashuv (ADR-10).
    totp_backup_codes = models.JSONField(default=list, blank=True, editable=False)

    objects = UserManager()
    # Faqat autentifikatsiya yo'li uchun: login tashkilot tanlanishidan
    # OLDIN bo'lgani sababli tenant konteksti hali mavjud emas (ADR-9).
    auth_objects = UnscopedManager()

    @property
    def has_2fa(self) -> bool:
        return bool(self.totp_secret and self.totp_confirmed_at)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        db_table = "user"
        ordering = ["full_name"]
        constraints = [
            # Email tashkilot ICHIDA unikal, global emas: bir odam ikki
            # bog'chada ishlashi mumkin. Global unikallik bu holatni jimgina
            # bloklardi va ro'yxatdan o'tishda boshqa tenant'da shu email
            # borligini oshkor qilardi (docs/03 §10.6).
            models.UniqueConstraint(
                fields=["organization", "email"],
                name="uq_user_org_email",
            ),
            # Platforma xodimlari uchun (organization IS NULL) email global unikal.
            models.UniqueConstraint(
                fields=["email"],
                condition=models.Q(organization__isnull=True),
                name="uq_user_platform_email",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} <{self.email}>"

    @property
    def is_org_owner(self) -> bool:
        return bool(self.role and self.role.code == "org_owner")

    @property
    def is_platform_staff(self) -> bool:
        """Vendor xodimi — hech qanday tenant'ga tegishli emas (ADR-10)."""
        return self.organization_id is None

    def permission_codes(self) -> set[str]:
        """Foydalanuvchining `<modul>.<amal>` ruxsatlari to'plami."""
        if self.role_id is None:
            return set()
        return set(
            Permission.objects.filter(role_permissions__role_id=self.role_id).values_list(
                "code", flat=True
            )
        )


class Role(TenantScopedModel):
    """
    Biznes roli — Django guruhi emas (ADR-4).

    Har bir tashkilot o'z rollar to'plamiga ega: ular ro'yxatdan o'tishda
    seed qilinadi va UI orqali boshqariladi.
    """

    name = models.CharField(max_length=80)
    code = models.CharField(max_length=40)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False)
    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.RESTRICT,
        related_name="roles",
        null=True,
        blank=True,
        help_text="NULL = tashkilotning barcha filiallariga tegishli",
    )
    # Bu roldagi odam faqat O'ZI qabul qilgan to'lovlarni ko'radi
    # (mijoz so'rovi, 2026-10-14; ADR-30).
    #
    # Ruxsat emas, BAYROQ — ataylab. "`payments.read_all` yo'q bo'lsa
    # cheklansin" degan qoida mavjud har bir rolni (direktor, buxgalter,
    # bog'chaning o'zi yasagan rollari) deploy paytida birdaniga
    # ko'r qilib qo'yardi, chunki ularning hech birida yangi ruxsat yo'q
    # — 14-invariant aynan shundan ogohlantiradi. Bayroq esa sukut
    # bo'yicha o'chiq: kimdir uni aniq yoqmaguncha hech kim cheklanmaydi.
    payments_own_only = models.BooleanField(default=False)

    class Meta:
        db_table = "role"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code", "branch"],
                name="uq_role_org_code_branch",
            ),
            models.UniqueConstraint(
                fields=["organization", "code"],
                condition=models.Q(branch__isnull=True),
                name="uq_role_org_code_global",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Permission(BaseModel):
    """
    Atomik imkoniyat — `<modul>.<amal>`.

    `organization_id` YO'Q: bu vendor egalik qiladigan global katalog,
    docs/03 §6.2 dagi ikkita istisnodan biri.
    """

    code = models.CharField(max_length=60, unique=True)
    module = models.CharField(max_length=40)
    action = models.CharField(max_length=20)
    label = models.CharField(max_length=120)

    class Meta:
        db_table = "permission"
        ordering = ["module", "action"]
        constraints = [
            models.UniqueConstraint(
                fields=["module", "action"], name="uq_permission_module_action"
            ),
        ]

    def __str__(self) -> str:
        return self.code


class RolePermission(BaseModel):
    """Rol ↔ permission ko'prigi."""

    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey(
        Permission, on_delete=models.CASCADE, related_name="role_permissions"
    )

    class Meta:
        db_table = "role_permission"
        constraints = [
            models.UniqueConstraint(fields=["role", "permission"], name="uq_role_permission"),
        ]

    def __str__(self) -> str:
        return f"{self.role.code} → {self.permission.code}"


class RefreshToken(BaseModel):
    """
    Refresh token'ning davomli yozuvi (docs/03 §10.7).

    Tez blacklist tekshiruvi Redis'da; bu jadval audit va "faol sessiyalar"
    ekrani uchun. Token XOM holda emas, faqat hash sifatida saqlanadi —
    baza nusxasi sizib chiqsa ham sessiyalarni tiklab bo'lmasin.
    """

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="refresh_tokens"
    )
    token_hash = models.CharField(max_length=255, unique=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "refresh_token"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "revoked_at"])]

    def __str__(self) -> str:
        return f"{self.user_id} · {self.created_at:%Y-%m-%d %H:%M}"

    @property
    def is_valid(self) -> bool:
        return self.revoked_at is None and self.expires_at > timezone.now()
