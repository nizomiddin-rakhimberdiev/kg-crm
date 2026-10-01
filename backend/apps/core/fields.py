"""
Tenant-scoped modellar uchun serializer maydonlari.

Muammo: `PrimaryKeyRelatedField(queryset=Role.objects.all())` queryset'ni
**klass e'lon qilinayotganda**, ya'ni import paytida hisoblaydi. O'sha paytda
tenant konteksti yo'q va `TenantManager` `TenantScopeMissing` ko'taradi —
loyiha umuman ishga tushmaydi.

Yechim: queryset'ni so'rov paytida hisoblash. Yon foydasi muhimroq —
maydon avtomatik ravishda **faqat joriy tashkilotning** qatorlarini qabul
qiladi, ya'ni begona tashkilot ID'si "mavjud emas" validatsiya xatosini
beradi, `403` emas. Boshqa tenant'da o'sha qator borligi oshkor bo'lmaydi
(docs/04 §2).
"""

from __future__ import annotations

from typing import Any

from django.db.models import Model, QuerySet
from rest_framework import serializers

__all__ = ["TenantPrimaryKeyRelatedField"]


class TenantPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    def __init__(self, model: type[Model], **kwargs: Any) -> None:
        self._model = model
        # DRF init paytida queryset talab qiladi. `all_objects` tenant
        # filtrini qo'llamaydi, shuning uchun import paytida xato bermaydi;
        # haqiqiy queryset quyida, so'rov paytida hisoblanadi.
        kwargs.setdefault("queryset", model.all_objects.none())  # type: ignore[attr-defined]
        super().__init__(**kwargs)

    def get_queryset(self) -> QuerySet[Any]:
        return self._model.objects.all()  # type: ignore[attr-defined,no-any-return]


class TenantUserRelatedField(serializers.PrimaryKeyRelatedField):
    """
    Foydalanuvchiga havola — tenant ichida (PLAN 2.8).

    `TenantPrimaryKeyRelatedField` dan alohida, chunki `User` da
    `all_objects` yo'q: u `AbstractBaseUser` dan keladi va o'z
    menejeriga ega. `objects.none()` ni init paytida chaqirish esa
    tenant kontekstini talab qiladi va import vaqtida yiqilardi.
    """

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("queryset", None)
        kwargs.setdefault("required", False)
        kwargs.setdefault("allow_null", True)
        super().__init__(**kwargs)

    def get_queryset(self) -> QuerySet[Any]:
        from apps.accounts.models import User

        return User.objects.filter(is_active=True)
