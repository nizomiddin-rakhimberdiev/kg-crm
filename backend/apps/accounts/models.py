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

from typing import Any

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

from apps.core.models import BaseModel

__all__ = ["User"]


class UserManager(BaseUserManager["User"]):
    """
    Foydalanuvchi yaratish yordamchilari.

    E'tibor: bu manager tenant filtri qo'llamaydi — `User` ning o'zi login
    paytida, ya'ni tenant konteksti hali o'rnatilmagan holda o'qiladi.
    Tashkilot bo'yicha cheklash `for_organization()` orqali aniq bajariladi.
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

    def for_organization(self, organization_id: Any) -> models.QuerySet[User]:
        return self.get_queryset().filter(organization_id=organization_id)


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

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    last_login_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

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
