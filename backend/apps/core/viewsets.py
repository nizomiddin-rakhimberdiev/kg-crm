"""
Tenant va filial doirasini qo'llovchi baza viewset'lar.

Tartib docs/02 §11.3 dagi diagrammaga aynan mos:
    tashkilot (buzib bo'lmaydi) → ruxsat → filial (rolga bog'liq)

Diqqat — viewset'da `queryset = Model.objects.all()` YOZILMAYDI. U klass
e'lon qilinayotganda, ya'ni import paytida bajariladi va o'shanda tenant
konteksti yo'q. O'rniga `model` atributi belgilanadi va queryset har bir
so'rovda quriladi.
"""

from __future__ import annotations

from typing import Any

from django.db.models import Model, QuerySet
from rest_framework import viewsets

from apps.core.permissions import HasModulePermission
from apps.core.typing import request_user
from apps.subscriptions.permissions import SubscriptionWriteGate

__all__ = [
    "TenantViewSet",
    "TenantReadOnlyViewSet",
    "BranchScopedMixin",
    "BranchCreateMixin",
]


class BranchCreateMixin:
    """
    Yaratishda filialni aniqlaydi.

    `TenantViewSet.perform_create` faqat `organization` ni qo'yadi —
    `branch` esa modelda `NOT NULL`. Ya'ni bu mixinsiz (yoki o'z
    `perform_create` isiz) filialga bog'langan har qanday yaratish
    bazada `NULL` cheklovga uriladi va mijoz tushunarsiz `409` oladi.

    Aynan shu holat `GuardianViewSet` da bor edi: vasiy qo'shish
    endpointi umuman ishlamasdi. Seed va testlar vasiylarni servis
    qatlami orqali yaratgani uchun buni hech narsa ko'rsatmagan.
    `test_every_branch_scoped_viewset_can_create` shuning uchun bor.
    """

    def perform_create(self, serializer: Any) -> None:
        user = request_user(self.request)  # type: ignore[attr-defined]
        from apps.branches.selectors import resolve_branch

        branch = serializer.validated_data.get("branch") or resolve_branch(
            user,
            self.request.data.get("branch_id"),  # type: ignore[attr-defined]
        )
        serializer.save(organization=user.organization, branch=branch)


class BranchScopedMixin:
    """
    Filial doirasini qo'llaydi — tashkilot filtridan **keyin**.

    Org Owner o'z tashkilotining barcha filiallarini o'qiydi; qolgan rollar
    o'z filiali bilan cheklangan. Shuning uchun bu mantiq baza manager'da
    emas: u rolga bog'liq, ya'ni biznes qoidasi, xavfsizlik chegarasi emas.

    Org Owner `?branch=<uuid>` bilan bitta filialga filtrlashi mumkin. Bu
    xavfsiz: queryset allaqachon tashkilot bilan cheklangan, shuning uchun
    begona filial ID'si shunchaki bo'sh natija beradi.
    """

    branch_field = "branch"

    def filter_queryset_by_branch(self, queryset: QuerySet[Any]) -> QuerySet[Any]:
        user = request_user(self.request)  # type: ignore[attr-defined]

        if not user.is_org_owner:
            if user.branch_id is None:
                # Org Owner bo'lmagan foydalanuvchida filial bo'lishi shart.
                # Bo'lmasa — hech narsa ko'rsatmaymiz (fail-closed).
                return queryset.none()
            return queryset.filter(**{f"{self.branch_field}_id": user.branch_id})

        requested = self.request.query_params.get("branch")  # type: ignore[attr-defined]
        if requested:
            return queryset.filter(**{f"{self.branch_field}_id": requested})
        return queryset


class _TenantQuerysetMixin:
    """`model` atributidan tenant-scoped queryset quradi."""

    model: type[Model] | None = None
    select_related_fields: tuple[str, ...] = ()

    def get_base_queryset(self) -> QuerySet[Any]:
        if self.model is None:
            raise NotImplementedError(
                f"{type(self).__name__} uchun `model` belgilanmagan "
                f"(yoki `get_base_queryset()` qayta yozilmagan)."
            )
        # `Model.objects` — TenantManager, ya'ni allaqachon joriy tashkilot
        # bilan cheklangan. Bu yerda qo'shimcha filtr yozilmaydi: uni qo'lda
        # takrorlash aynan unutish mumkin bo'lgan joyni yaratardi.
        queryset = self.model.objects.all()  # type: ignore[attr-defined]
        if self.select_related_fields:
            queryset = queryset.select_related(*self.select_related_fields)
        return queryset

    def get_queryset(self) -> QuerySet[Any]:
        queryset = self.get_base_queryset()
        if isinstance(self, BranchScopedMixin):
            queryset = self.filter_queryset_by_branch(queryset)
        return queryset


class TenantViewSet(_TenantQuerysetMixin, viewsets.ModelViewSet):
    """
    Tashkilot bilan cheklangan CRUD viewset.

    Vorislar `permission_module` ni belgilaydi, aks holda `HasModulePermission`
    hamma narsani rad etadi (P5).
    """

    permission_classes = [HasModulePermission, SubscriptionWriteGate]
    permission_module: str | None = None
    #: Yozgandan keyin javob uchun ishlatiladigan serializer. Belgilanmasa,
    #: `get_serializer_class()` ishlatiladi.
    read_serializer_class: Any = None

    def perform_create(self, serializer: Any) -> None:
        # Tashkilot mijozdan olinmaydi — har doim so'rov egasidan.
        serializer.save(organization=request_user(self.request).organization)

    # --- Javob shakli ---
    #
    # Ko'p viewset'da yozish va o'qish serializerlari alohida (yozishda
    # `*_id` maydonlari, o'qishda kengaytirilgan obyektlar). DRF esa
    # yozgandan keyin YOZISH serializerini qaytaradi — natijada
    # `POST /x` javobi `GET /x/{id}` javobidan farq qiladi va mijoz
    # ikkita shaklni qo'llab-quvvatlashga majbur bo'ladi.
    #
    # Quyidagi ikkita override shu nomuvofiqlikni yopadi.

    def _read_representation(self, instance: Any) -> Any:
        serializer_class = self.read_serializer_class
        if serializer_class is None:
            method = self.request.method
            self.request.method = "GET"  # `get_serializer_class()` metodga qaraydi
            try:
                serializer_class = self.get_serializer_class()
            finally:
                self.request.method = method
        return serializer_class(instance, context=self.get_serializer_context()).data

    def create(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        from rest_framework import status as http_status
        from rest_framework.response import Response

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            self._read_representation(serializer.instance),
            status=http_status.HTTP_201_CREATED,
        )

    def update(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        from rest_framework.response import Response

        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(self._read_representation(serializer.instance))


class TenantReadOnlyViewSet(_TenantQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [HasModulePermission, SubscriptionWriteGate]
    permission_module: str | None = None
