"""
Tenant-scoped queryset va manager.

Bu fayl P10 ni amalga oshiradi: `organization_id` filtri **default queryset**
darajasida, view mantig'idan oldin qo'llanadi. View yozuvchi uni yozishi
shart emas — va shuning uchun unutishi ham mumkin emas.
"""

from __future__ import annotations

from typing import Any

from django.db import models

from apps.core.tenancy import TenantScopeMissing, get_current_organization_id

__all__ = ["TenantQuerySet", "TenantManager", "UnscopedManager"]


class TenantQuerySet(models.QuerySet):
    """Joriy tashkilot bo'yicha avtomatik filtrlanadigan queryset."""

    # Sinf darajasidagi default: har bir yangi queryset cheklangan hisoblanadi.
    _tenant_scope_disabled: bool = False

    def unscoped(self) -> TenantQuerySet:
        """
        Tenant filtrini ATAYLAB o'chiradi.

        Faqat quyidagilar uchun: migratsiyalar, platforma (vendor) darajasidagi
        xizmat vazifalari, va tashkilotlar bo'ylab ishlaydigan boshqaruv
        buyruqlari. Har bir chaqiruv ko'rib chiqilishi kerak — shuning uchun
        nomi aniq va `grep -rn "unscoped()"` bilan topiladi (docs/02 §11.3).
        """
        # `_chain`/`_clone` — Django'ning ichki API'si; django-stubs ularni
        # e'lon qilmaydi, shuning uchun nuqtali ignore.
        clone = self._chain()  # type: ignore[attr-defined]
        clone._tenant_scope_disabled = True
        return clone  # type: ignore[no-any-return]

    def for_organization(self, organization_id: Any) -> TenantQuerySet:
        """Aniq tashkilot bo'yicha filtrlaydi (kontekstga bog'liq emas)."""
        return self.unscoped().filter(organization_id=organization_id)

    def _clone(self) -> TenantQuerySet:  # type: ignore[misc]
        """
        Bayroqni har bir nusxaga ko'chiradi.

        `_clone()` ni `.filter()`, `.exclude()`, `.all()` — hammasi chaqiradi.
        Bayroq shu yerda ko'chirilmasa, `.unscoped().filter(...)` jimgina yana
        cheklanib qolardi va platforma vazifalari tushunarsiz bo'sh natija
        olardi.
        """
        clone: TenantQuerySet = super()._clone()  # type: ignore[misc]
        clone._tenant_scope_disabled = self._tenant_scope_disabled
        return clone


class TenantManager(models.Manager.from_queryset(TenantQuerySet)):  # type: ignore[misc]
    """
    Default manager: har bir so'rovni joriy tashkilot bilan cheklaydi.

    Kontekst o'rnatilmagan bo'lsa `TenantScopeMissing` ko'taradi — fail-closed.
    """

    def get_queryset(self) -> TenantQuerySet:
        queryset: TenantQuerySet = super().get_queryset()
        if queryset._tenant_scope_disabled:
            return queryset

        organization_id = get_current_organization_id()
        if organization_id is None:
            raise TenantScopeMissing(
                f"{self.model.__name__} tenant-scoped, lekin tashkilot konteksti "
                f"o'rnatilmagan. `organization_context(org_id)` ishlating yoki "
                f"ataylab kerak bo'lsa `.unscoped()` chaqiring."
            )
        return queryset.filter(organization_id=organization_id)

    # `from_queryset` avtomatik yasagan proksilar `self.get_queryset()` ni
    # chaqiradi — ya'ni chiqish yo'llarigacha yetib bormay xato ko'tarilardi.
    # Shuning uchun ular filtrsiz bazadan boshlanadi.

    def unscoped(self) -> TenantQuerySet:
        return super().get_queryset().unscoped()

    def for_organization(self, organization_id: Any) -> TenantQuerySet:
        return super().get_queryset().for_organization(organization_id)


class UnscopedManager(models.Manager.from_queryset(TenantQuerySet)):  # type: ignore[misc]
    """
    Tenant filtrisiz manager — modelda `all_objects` sifatida beriladi.

    Django admin, migratsiyalar va platforma vazifalari uchun. Hech qachon
    oddiy view/selector'da ishlatilmaydi.
    """

    def get_queryset(self) -> TenantQuerySet:
        return super().get_queryset().unscoped()
