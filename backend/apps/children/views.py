"""Bolalar CRM endpointlari (docs/04 §7)."""

from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from apps.audit import services as audit
from apps.branches.selectors import resolve_branch
from apps.children import services
from apps.children.importer import import_children
from apps.children.models import Child, Enrollment, Group, Guardian
from apps.children.serializers import (
    ChildGuardianSerializer,
    ChildSerializer,
    ChildWriteSerializer,
    EnrollmentSerializer,
    GroupSerializer,
    GuardianSerializer,
)
from apps.core.exceptions import BusinessRuleViolation
from apps.core.typing import request_user
from apps.core.viewsets import BranchCreateMixin, BranchScopedMixin, TenantViewSet

__all__ = ["ChildViewSet", "GuardianViewSet", "GroupViewSet"]


class ChildViewSet(BranchScopedMixin, TenantViewSet):
    permission_module = "children"
    permission_action_map = {
        "enroll": "update",
        "add_guardian": "update",
        "bulk_import": "create",
    }
    model = Child
    search_fields = ["first_name", "last_name", "middle_name"]
    ordering_fields = ["last_name", "date_of_birth", "created_at"]
    filterset_fields = ["enrollment_status", "gender"]

    def get_base_queryset(self) -> Any:
        # `prefetch_related` — ro'yxatda har bir bola uchun vasiy va guruh
        # so'rovi yuborilmasin (docs/02 §21.1: N+1 selector qatlamida
        # o'ldiriladi).
        return (
            super()
            .get_base_queryset()
            .prefetch_related("guardian_links__guardian", "enrollments__group")
        )

    def get_serializer_class(self) -> Any:
        return ChildSerializer if self.request.method in ("GET", "HEAD") else ChildWriteSerializer

    def perform_create(self, serializer: Any) -> None:
        user = request_user(self.request)
        branch = serializer.validated_data.get("branch") or resolve_branch(user)
        child = serializer.save(organization=user.organization, branch=branch)
        audit.record(
            action="create",
            request=self.request._request,
            actor=user,
            entity_type="child",
            entity_id=child.id,
        )

    def perform_destroy(self, instance: Child) -> None:
        # Moliyaviy tarixi bo'lgan bola hech qachon fizik o'chirilmaydi (D5).
        instance.is_active = False
        instance.save(update_fields=["is_active"])
        audit.record(
            action="delete",
            request=self.request._request,
            actor=request_user(self.request),
            entity_type="child",
            entity_id=instance.id,
        )

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
        phone = (request.data.get("phone") or "").strip()
        if not phone:
            raise BusinessRuleViolation("Telefon raqami majburiy.")

        guardian = services.upsert_guardian(
            organization=child.organization,
            branch=child.branch,
            phone=phone,
            first_name=(request.data.get("first_name") or "").strip(),
            last_name=(request.data.get("last_name") or "").strip(),
            email=(request.data.get("email") or "").strip(),
        )
        link = services.attach_guardian(
            child=child,
            guardian=guardian,
            relation=request.data.get("relation", "other"),
            is_primary=bool(request.data.get("is_primary", False)),
            can_pickup=bool(request.data.get("can_pickup", True)),
        )
        return Response(ChildGuardianSerializer(link).data, status=status.HTTP_201_CREATED)

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
            raise BusinessRuleViolation("Fayl yuborilmagan.")

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
    model = Guardian
    serializer_class = GuardianSerializer
    search_fields = ["first_name", "last_name", "phone"]


class GroupViewSet(BranchScopedMixin, TenantViewSet):
    permission_module = "children"
    model = Group
    serializer_class = GroupSerializer
    search_fields = ["name"]
    ordering_fields = ["name", "enrolled_count"]

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
                f"Guruhda {active} ta faol bola bor — avval ularni ko'chiring."
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
