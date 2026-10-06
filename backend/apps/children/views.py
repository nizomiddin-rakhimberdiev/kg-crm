"""Bolalar CRM endpointlari (docs/04 §7)."""

from __future__ import annotations

import io
from typing import Any
from uuid import UUID

from django.db import transaction
from django.http import FileResponse, Http404
from django.utils.translation import gettext
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from apps.audit import services as audit
from apps.branches.selectors import resolve_branch
from apps.children import importer, scope, services
from apps.children.importer import import_children
from apps.children.models import Child, Enrollment, Group, Guardian
from apps.children.serializers import (
    AddGuardianSerializer,
    ChildGuardianSerializer,
    ChildSerializer,
    ChildStatusSerializer,
    ChildWriteSerializer,
    EnrollmentSerializer,
    GroupSerializer,
    GuardianSerializer,
)
from apps.core import translit
from apps.core.exceptions import BusinessRuleViolation
from apps.core.typing import request_user
from apps.core.viewsets import BranchCreateMixin, BranchScopedMixin, TenantViewSet

__all__ = ["ChildViewSet", "GuardianViewSet", "GroupViewSet"]


def _valid_uuids(values: list[str]) -> list[UUID]:
    """Noto'g'ri formatdagi qiymat 500 emas, shunchaki mos kelmaydi."""
    result: list[UUID] = []
    for value in values:
        try:
            result.append(UUID(value))
        except ValueError:
            continue
    return result


class ChildViewSet(BranchScopedMixin, TenantViewSet):
    permission_module = "children"
    permission_action_map = {
        "enroll": "update",
        "add_guardian": "update",
        "bulk_import": "create",
        "change_status": "update",
        "archive": "update",
        "restore": "update",
        "hard_delete": "delete",
        "guardian_link": "update",
    }
    model = Child
    # `search_fields` ataylab qoldirilgan: u DRF ning standart qidiruvi
    # va `?search=` bilan ishlaydi. Qidiruv kaliti esa ustiga qo'shiladi
    # (`get_base_queryset`), ya'ni "Улугбек" ham, "Ulug'bek" ham topiladi.
    search_fields = ["first_name", "last_name", "middle_name"]
    ordering_fields = ["last_name", "date_of_birth", "created_at"]
    filterset_fields = ["enrollment_status", "gender"]

    # Bir so'rovda nechta `id` — Radix Intelligence evidence'idagi bolalar
    # ro'yxati 50 ga cheklangan (docs/07 §6); sahifa maksimumi 100.
    IDS_CAP = 100

    def get_base_queryset(self) -> Any:
        # `prefetch_related` — ro'yxatda har bir bola uchun vasiy va guruh
        # so'rovi yuborilmasin (docs/02 §21.1: N+1 selector qatlamida
        # o'ldiriladi).
        queryset = (
            super()
            .get_base_queryset()
            .prefetch_related("guardian_links__guardian", "enrollments__group")
        )
        # `?ids=a,b,c` — yorliqlarni id bo'yicha bitta so'rovda olish
        # (docs/07 §6: "Nega?" paneli nomlarni snapshot'dan emas, jonli
        # oladi). Tenant filtri va RLS yuqorida allaqachon qo'llangan —
        # begona id shunchaki topilmaydi. Nofaol (o'chirilgan) bola ham
        # qaytadi: uning raqamlari snapshot'da bor, yorlig'i kerak.
        ids = self.request.query_params.get("ids")
        if ids:
            wanted = [value for value in ids.split(",") if value][: self.IDS_CAP]
            queryset = queryset.filter(id__in=_valid_uuids(wanted))

        # Qidiruv kaliti (PLAN 2.7): apostrof va alifbo farqi yo'qoladi.
        # DRF ning `?search=` filtri `search_fields` bo'yicha alohida
        # ishlaydi; bu esa uni TO'LDIRADI — "Улугбек" deb yozilgan
        # so'rov "Ulug'bek" ni ham topadi.
        term = self.request.query_params.get("q")
        if term:
            queryset = queryset.filter(search_key__contains=translit.search_key(term))

        # Qator darajasidagi doira (PLAN 2.6): guruhga biriktirilgan
        # tarbiyachi faqat o'z guruhining bolalarini ko'radi. Boshqa
        # hamma uchun queryset o'zgarmay qaytadi, ya'ni "shartni
        # unutish" xatosi tuzilishi bo'yicha mumkin emas.
        queryset = scope.restrict_children(queryset, request_user(self.request))
        return queryset

    def get_serializer_class(self) -> Any:
        return ChildSerializer if self.request.method in ("GET", "HEAD") else ChildWriteSerializer

    def perform_create(self, serializer: Any) -> None:
        user = request_user(self.request)
        branch = serializer.validated_data.get("branch") or resolve_branch(user)
        # `opening_debt` modelda yo'q — u ledger'ga yoziladi (PLAN 7.8).
        opening_debt = serializer.validated_data.pop("opening_debt", None)
        child = serializer.save(organization=user.organization, branch=branch)
        if opening_debt:
            from apps.finance.services import record_opening_debt

            record_opening_debt(child=child, amount=opening_debt, created_by=user)
        audit.record(
            action="create",
            request=self.request._request,
            actor=user,
            entity_type="child",
            entity_id=child.id,
            changes={"opening_debt": str(opening_debt)} if opening_debt else None,
        )

    def perform_destroy(self, instance: Child) -> None:
        # `DELETE` = ARXIV (Q6). Bolalar hech qachon fizik o'chirilmaydi:
        # ularning hisob-fakturasi, to'lovi va davomati bog'chaning
        # moliyaviy tarixi. Xato kiritilgan yozuv uchun alohida,
        # qattiq cheklangan yo'l bor: `POST /children/{id}/hard-delete`.
        services.archive_child(child=instance, actor=request_user(self.request))
        audit.record(
            action="delete",
            request=self.request._request,
            actor=request_user(self.request),
            entity_type="child",
            entity_id=instance.id,
        )

    @action(detail=True, methods=["post"], url_path="change-status")
    def change_status(self, request: Request, pk: str | None = None) -> Response:
        """
        `POST /children/{id}/change-status` — holat, SANA va SABAB bilan (Q5).

        Ikkalasi ham majburiy: "Chiqib ketgan" degan holat o'zi hech
        narsa demaydi, savol esa har doim pul bilan birga keladi —
        "qachondan buyon?".
        """
        serializer = ChildStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        child = self.get_object()
        before = {"status": child.enrollment_status, "on": str(child.status_changed_on)}
        services.change_status(
            child=child,
            status=data["enrollment_status"],
            on_date=data["status_changed_on"],
            reason=data["status_reason"],
            actor=request_user(request),
        )
        audit.record(
            action="update",
            request=request._request,
            actor=request_user(request),
            entity_type="child",
            entity_id=child.id,
            changes={
                "before": before,
                "after": {
                    "status": child.enrollment_status,
                    "on": str(child.status_changed_on),
                    "reason": child.status_reason,
                },
            },
        )
        return Response(ChildSerializer(child).data)

    @action(detail=True, methods=["post"])
    def archive(self, request: Request, pk: str | None = None) -> Response:
        """`POST /children/{id}/archive` — ro'yxatdan chiqadi, ma'lumot qoladi (Q6)."""
        child = self.get_object()
        services.archive_child(
            child=child,
            actor=request_user(request),
            reason=str(request.data.get("reason", "")),
        )
        audit.record(
            action="update",
            request=request._request,
            actor=request_user(request),
            entity_type="child",
            entity_id=child.id,
            changes={"archived": True, "reason": child.status_reason},
        )
        return Response(ChildSerializer(child).data)

    @action(detail=True, methods=["post"])
    def restore(self, request: Request, pk: str | None = None) -> Response:
        """`POST /children/{id}/restore` — xato arxivlash tuzatiladi."""
        child = self.get_object()
        services.restore_child(child=child)
        audit.record(
            action="update",
            request=request._request,
            actor=request_user(request),
            entity_type="child",
            entity_id=child.id,
            changes={"archived": False},
        )
        return Response(ChildSerializer(child).data)

    @action(detail=True, methods=["post"], url_path="hard-delete")
    def hard_delete(self, request: Request, pk: str | None = None) -> Response:
        """
        `POST /children/{id}/hard-delete` — xato kiritilgan yozuvni o'chiradi (Q6).

        Yagona qattiq o'chirish yo'li va u ataylab tor: moliyaviy
        yozuvi yo'q va 24 soat ichida yaratilgan yozuv. Ya'ni "ism
        noto'g'ri yozildi, qaytadan kiritaman" degan holat — va faqat
        o'sha. Audit izi bolaning o'zi o'chgandan KEYIN ham qoladi.
        """
        child = self.get_object()
        snapshot = {"full_name": child.full_name, "date_of_birth": str(child.date_of_birth)}
        child_id = child.id
        services.delete_child(child=child, actor=request_user(request))
        audit.record(
            action="delete",
            request=request._request,
            actor=request_user(request),
            entity_type="child",
            entity_id=child_id,
            changes=snapshot,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def enroll(self, request: Request, pk: str | None = None) -> Response:
        """Bolani guruhga yozadi (avvalgi a'zolik yopiladi)."""
        child = self.get_object()
        serializer = EnrollmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        enrollment = services.enroll_child(
            child=child,
            group=serializer.validated_data["group"],
            start_date=serializer.validated_data.get("start_date"),
        )
        audit.record(
            action="update",
            request=request._request,
            actor=request_user(request),
            entity_type="enrollment",
            entity_id=enrollment.id,
            changes={"child": str(child.id), "group": str(enrollment.group_id)},
        )
        return Response(EnrollmentSerializer(enrollment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="guardians")
    def add_guardian(self, request: Request, pk: str | None = None) -> Response:
        """Vasiyni topadi/yaratadi va bolaga bog'laydi."""
        child = self.get_object()
        serializer = AddGuardianSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        guardian = services.upsert_guardian(
            organization=child.organization,
            branch=child.branch,
            phone=data["phone"],
            phone_alt=data.get("phone_alt", "").strip(),
            first_name=data.get("first_name", "").strip(),
            last_name=data.get("last_name", "").strip(),
            email=data.get("email", "").strip(),
            # SMS tili (PLAN 3.4). Bo'sh — bog'chaning sukut tili.
            language=data.get("language", "").strip()[:2],
        )
        link = services.attach_guardian(
            child=child,
            guardian=guardian,
            relation=data["relation"],
            is_primary=data["is_primary"],
            can_pickup=data["can_pickup"],
        )
        return Response(ChildGuardianSerializer(link).data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["patch", "delete"],
        url_path=r"guardians/(?P<link_id>[0-9a-f-]{36})",
    )
    def guardian_link(self, request: Request, pk: str | None = None, link_id: str = "") -> Response:
        """
        Vasiy bog'lanishini tahrirlaydi yoki uzadi (PLAN 2.1).

        Ilgari vasiyni faqat QO'SHISH mumkin edi: qarindoshligi noto'g'ri
        yozilgan bo'lsa yoki ota-ona ajrashgan bo'lsa, bog'lanishni
        o'zgartirishning yo'li yo'q edi.

        Vasiyning O'ZI o'chirilmaydi — faqat bog'lanish uziladi: u
        boshqa bolaning ham vasiysi bo'lishi mumkin.
        """
        child = self.get_object()
        link = child.guardian_links.filter(pk=link_id).first()
        if link is None:
            raise Http404

        if request.method == "DELETE":
            link.delete()
            audit.record(
                action="delete",
                request=request._request,
                actor=request_user(request),
                entity_type="child_guardian",
                entity_id=link.id,
                changes={"child": child.full_name, "guardian": link.guardian.full_name},
            )
            return Response(status=status.HTTP_204_NO_CONTENT)

        for field in ("relation", "is_primary", "can_pickup"):
            if field in request.data:
                setattr(link, field, request.data[field])

        # Asosiy vasiy BITTA va buni BAZA qo'riqlaydi (qisman unikal
        # indeks). Shuning uchun tartib muhim: avval eskisi tushiriladi,
        # keyin yangisi saqlanadi. Teskari tartibda `INSERT` cheklovga
        # urilib, 409 qaytarardi — foydalanuvchi uchun esa bu shunchaki
        # "nega ishlamayapti?" bo'lardi.
        with transaction.atomic():
            if link.is_primary:
                child.guardian_links.exclude(pk=link.pk).update(is_primary=False)
            link.save(update_fields=["relation", "is_primary", "can_pickup", "updated_at"])

        return Response(ChildGuardianSerializer(link).data)

    @action(detail=False, methods=["get"], url_path="import-template")
    def import_template(self, request: Request) -> FileResponse:
        """
        `GET /children/import-template` — to'ldirish uchun Excel shabloni.

        Shablon SERVERDA yaratiladi, frontendda emas: ustun nomlari
        importer bilan aynan bir xil bo'lishi kerak, va ikki joyda
        yozilgan ro'yxat ertami-kechmi ajralib qoladi — o'shanda mijoz
        to'ldirgan fayl "majburiy ustun topilmadi" deb rad etilardi.
        """
        from apps.branches.selectors import resolve_branch
        from apps.finance.models import TariffPlan

        # Guruh va tarif ro'yxati BOG'CHANIKI (PLAN 7.6): kotib nom
        # o'ylab topmasin va "Quyoshcha"ni "Quyosha" deb yozib
        # yubormasin. Ro'yxat shablon yuklanayotgan paytdagi holat.
        branch = resolve_branch(request_user(request), request.query_params.get("branch"))
        groups = list(
            Group.objects.filter(branch=branch, is_active=True)
            .order_by("name")
            .values_list("name", flat=True)
        )
        tariffs = list(
            TariffPlan.objects.filter(branch=branch, is_active=True)
            .order_by("name")
            .values_list("name", flat=True)
        )
        content = importer.build_template(groups=groups, tariffs=tariffs)
        return FileResponse(
            io.BytesIO(content),
            as_attachment=True,
            filename="bolalar-shablon.xlsx",
            content_type=("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="import",
        parser_classes=[MultiPartParser],
    )
    def bulk_import(self, request: Request) -> Response:
        """
        Excel/CSV import (docs/06 Sprint 2).

        `dry_run=true` (default) — faqat tekshiradi va hisobot qaytaradi.
        Foydalanuvchi natijani ko'rgach `dry_run=false` bilan qayta yuboradi.
        """
        uploaded = request.FILES.get("file")
        if uploaded is None:
            raise BusinessRuleViolation(gettext("Fayl yuborilmagan."))

        user = request_user(request)
        branch = resolve_branch(user, request.data.get("branch_id"))

        dry_run = str(request.data.get("dry_run", "true")).lower() != "false"

        report = import_children(
            organization=user.organization,
            branch=branch,
            file_bytes=uploaded.read(),
            dry_run=dry_run,
        )

        if not dry_run and report.is_valid:
            audit.record(
                action="create",
                request=request._request,
                actor=user,
                entity_type="child_import",
                changes={"created": report.created, "skipped": report.skipped_duplicates},
            )

        return Response(report.as_dict())


class GuardianViewSet(BranchCreateMixin, BranchScopedMixin, TenantViewSet):
    permission_module = "children"
    permission_action_map = {"telegram_link": "update", "telegram_unlink": "update"}
    model = Guardian
    serializer_class = GuardianSerializer
    search_fields = ["first_name", "last_name", "phone"]

    @action(detail=True, methods=["post"], url_path="telegram-link")
    def telegram_link(self, request: Request, pk: str | None = None) -> Response:
        """
        `POST /guardians/{id}/telegram-link` — ota-onaga beriladigan havola.

        `rotate=true` eski havolani darhol ishlamas qiladi. Bu kerak,
        chunki havola oilaviy guruhga tashlanishi mumkin va xabarlar
        ichida bolaning ismi bilan qarz summasi ketadi.

        Javobda `url` bo'sh bo'lishi mumkin — bot sozlanmagan. Ekran
        o'shanda havola emas, izoh ko'rsatadi: ishlamaydigan havolani
        berib qo'yish eng yomon variant.
        """
        from apps.children import telegram as links

        guardian = self.get_object()
        rotate = str(request.data.get("rotate") or "").lower() in ("true", "1", "yes")
        url = links.link_url(guardian, rotate=rotate)
        guardian.refresh_from_db()
        audit.record(
            action="update",
            request=request._request,
            actor=request_user(request),
            entity_type="guardian",
            entity_id=guardian.id,
            changes={"telegram": "link_issued"},
        )
        return Response(
            {
                "url": url,
                "bot_username": links.bot_username(),
                "linked": links.is_linked(guardian),
            }
        )

    @action(detail=True, methods=["post"], url_path="telegram-unlink")
    def telegram_unlink(self, request: Request, pk: str | None = None) -> Response:
        """
        Bog'lanishni bog'cha tomonidan uzadi.

        Kerak bo'ladigan holat: raqam boshqa odamga o'tdi yoki ota-ona
        "menga kelmayapti" deb murojaat qildi va qayta ulanish kerak.
        Ota-onaning o'zi esa botda `/stop` yuboradi.
        """
        guardian = self.get_object()
        guardian.telegram_chat_id = ""
        guardian.telegram_linked_at = None
        guardian.save(update_fields=["telegram_chat_id", "telegram_linked_at", "updated_at"])
        audit.record(
            action="update",
            request=request._request,
            actor=request_user(request),
            entity_type="guardian",
            entity_id=guardian.id,
            changes={"telegram": "unlinked"},
        )
        return Response(GuardianSerializer(guardian).data)


class GroupViewSet(BranchScopedMixin, TenantViewSet):
    permission_module = "children"
    model = Group
    serializer_class = GroupSerializer
    search_fields = ["name"]
    ordering_fields = ["name", "enrolled_count"]

    def get_base_queryset(self) -> Any:
        return scope.restrict_groups(
            super().get_base_queryset().select_related("teacher"),
            request_user(self.request),
        )

    def perform_create(self, serializer: Any) -> None:
        user = request_user(self.request)
        branch = resolve_branch(user, self.request.data.get("branch_id"))
        serializer.save(organization=user.organization, branch=branch)

    def perform_destroy(self, instance: Group) -> None:
        active = Enrollment.objects.filter(
            group=instance, status="active", end_date__isnull=True
        ).count()
        if active:
            raise BusinessRuleViolation(
                gettext("Guruhda {active} ta faol bola bor — avval ularni koʻchiring.").format(
                    active=active
                )
            )
        instance.is_active = False
        instance.save(update_fields=["is_active"])

    @action(detail=True, methods=["get"], url_path="children")
    def children(self, request: Request, pk: str | None = None) -> Response:
        """
        `GET /groups/{id}/children` — guruhdagi HOZIRGI bolalar (docs/04 §7.3).

        Manba — ochiq `enrollment` yozuvlari, `child.group` maydoni emas:
        bola guruhga vaqt bo'yicha biriktiriladi, va o'tgan a'zoliklar
        tarixda qoladi (docs/03 §11.5). Shu sababli "kim shu guruhda"
        degan savolga faqat ochiq a'zolik javob beradi.
        """
        group = self.get_object()

        children = (
            Child.objects.filter(
                enrollments__group=group,
                enrollments__status="active",
                enrollments__end_date__isnull=True,
                is_active=True,
            )
            .prefetch_related("guardian_links__guardian", "enrollments__group")
            .order_by("last_name", "first_name")
        )

        return Response(
            {
                "group": GroupSerializer(group).data,
                "capacity": group.capacity,
                # `0` = cheklovsiz (docs/04 §7.3), shunda "bo'sh joy" ma'nosiz.
                "free_seats": (
                    max(group.capacity - children.count(), 0) if group.capacity else None
                ),
                "children": ChildSerializer(children, many=True).data,
            }
        )
