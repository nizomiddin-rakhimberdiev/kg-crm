"""
Platforma (vendor) tekisligi — ADR-10, docs/02 §11.0.

Vendor xodimlari `accounts.User` da **yashamaydi**. Bu ataylab: bitta
jadval bo'lganda "vendor bayrog'i" degan ustun paydo bo'lardi, va o'sha
bayroq bir kun kimningdir hisobiga tasodifan qo'yilardi. Ikki jadval —
ikki kirish yo'li, ikki parol siyosati, va eng muhimi: mijoz
ma'lumotiga tenant filtri orqali kirish YO'Q.

Vendor sukut bo'yicha **hech qanday** mijoz ma'lumotini ko'rmaydi. U
tashkilot metama'lumotini ko'radi — nomi, rejasi, holati, bolalar soni.
Operatsion ma'lumotni o'qish uchun vaqt bilan cheklangan, sababi
yozilgan va **mijozga ko'rinadigan** ruxsat (`SupportGrant`) kerak.
Bu ruxsat ham alohida kod yo'li emas: xodim oddiy mijoz API'si orqali,
o'sha tashkilot kontekstida ishlaydi — ya'ni audit qilinadigan yagona
yo'l bor (docs/04 §19).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone

__all__ = [
    "PlatformRole",
    "PlatformUser",
    "SupportGrant",
    "LeadStatus",
    "Lead",
    "GRANT_MAX_HOURS",
]

# Ruxsatning eng uzun muddati. "Doimiy kirish" degan tushuncha yo'q:
# muddatsiz ruxsat vaqt o'tib oddiy imtiyozga aylanadi va uni hech kim
# qaytarib olmaydi.
GRANT_MAX_HOURS = 24


class PlatformRole(models.TextChoices):
    ADMIN = "platform_admin", "Platforma administratori"
    SUPPORT = "platform_support", "Platforma qo'llab-quvvatlash"


class PlatformUser(models.Model):
    """
    Vendor xodimi.

    `AbstractBaseUser` dan meros OLMAYDI: Django auth mashinasi
    `accounts.User` bilan bog'langan va ikkisini bitta mashinaga ulash
    aynan biz qochayotgan chalkashlikni yaratardi.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)
    password = models.CharField(max_length=128)
    role = models.CharField(
        max_length=30, choices=PlatformRole.choices, default=PlatformRole.SUPPORT
    )
    is_active = models.BooleanField(default=True)

    # 2FA MAJBURIY (ADR-10). `totp_secret` bo'sh bo'lsa kirish
    # mumkin emas — "keyin yoqaman" degan holat yo'q.
    totp_secret = models.CharField(max_length=64, blank=True)
    totp_confirmed_at = models.DateTimeField(null=True, blank=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "platform_user"
        ordering = ["email"]

    def __str__(self) -> str:
        return f"{self.full_name} <{self.email}>"

    @property
    def has_2fa(self) -> bool:
        return bool(self.totp_secret and self.totp_confirmed_at)

    def set_password(self, raw: str) -> None:
        self.password = make_password(raw)

    def check_password(self, raw: str) -> bool:
        return check_password(raw, self.password)


class SupportGrant(models.Model):
    """
    Vaqt bilan cheklangan operatsion kirish ruxsati.

    Uch xossasi majburiy va ularning har biri alohida sababga ega:

    * **sabab** — "nima uchun kirdingiz?" degan savolga javob keyin
      emas, kirishdan OLDIN yoziladi;
    * **muddat** — ruxsat o'zi tugaydi, uni qaytarib olishni eslash
      kerak emas;
    * **mijozga ko'rinishi** — mijoz `/audit-logs/platform-access`
      orqali har bir kirishni ko'radi. Ko'rinmaydigan kirish ishonchni
      texnik jihatdan emas, ijtimoiy jihatdan buzadi.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.RESTRICT, related_name="support_grants"
    )
    platform_user = models.ForeignKey(
        PlatformUser, on_delete=models.RESTRICT, related_name="support_grants"
    )
    reason = models.TextField()
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "support_grant"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="ix_grant_org_created"),
        ]
        constraints = [
            # Sababsiz ruxsat — sababsiz kirish.
            models.CheckConstraint(condition=~models.Q(reason=""), name="ck_grant_reason"),
        ]

    def __str__(self) -> str:
        return f"{self.platform_user_id} → {self.organization_id}"

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and self.expires_at > timezone.now()

    @classmethod
    def default_expiry(cls, hours: int = 2) -> datetime:
        return timezone.now() + timedelta(hours=min(hours, GRANT_MAX_HOURS))


class LeadStatus(models.TextChoices):
    """Sotuv jamoasi uchun kichik, aniq holatlar to'plami."""

    NEW = "new", "Yangi"
    CONTACTED = "contacted", "Bog'lanildi"
    QUALIFIED = "qualified", "Mos keladi"
    CLOSED = "closed", "Yopildi"


class Lead(models.Model):
    """Public saytdan kelgan zayavka — tenant emas, platforma obyektidir.

    Bu jadvalda `organization_id` ataylab yo'q: ariza yuborgan bog'cha
    hali mijoz bo'lmasligi mumkin. Uni tenant jadvaliga bog'lash RLS
    chegarasi va "lead → sotuv suhbati → tenant" oqimini buzgan bo'lardi.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=13, db_index=True)
    kindergarten_name = models.CharField(max_length=200)
    children_count = models.PositiveSmallIntegerField()
    city = models.CharField(max_length=120)
    message = models.TextField(blank=True, max_length=1_000)
    language = models.CharField(
        max_length=2, choices=[("uz", "O'zbekcha"), ("ru", "Русский"), ("en", "English")]
    )
    source = models.CharField(max_length=40, default="website")
    status = models.CharField(max_length=20, choices=LeadStatus.choices, default=LeadStatus.NEW)
    # Sotuvchining qisqa izohi ("ertaga qo'ng'iroq", "narx yubordim") —
    # holat bilan birga konsoldan yoziladi.
    note = models.TextField(blank=True, max_length=2_000)
    status_changed_at = models.DateTimeField(null=True, blank=True)

    # Rozilik dalili hamda so'rovni takror yuborishga qarshi kalit. Kalit
    # brauzerda bir forma ochilganda yaratiladi; qayta urinish yangi lead
    # yasamaydi.
    consented_at = models.DateTimeField()
    privacy_policy_version = models.CharField(max_length=32)
    submission_id = models.UUIDField(unique=True, editable=False)

    class Meta:
        db_table = "platform_lead"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="ix_lead_status_created"),
            models.Index(fields=["phone", "-created_at"], name="ix_lead_phone_created"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(children_count__gte=1) & models.Q(children_count__lte=10_000),
                name="ck_lead_children_count",
            ),
        ]

    def __str__(self) -> str:
        # Telefonni admin/loglarda tasodifan ko'rsatmaslik uchun qaytarmaymiz.
        return f"{self.kindergarten_name} — {self.status}"
