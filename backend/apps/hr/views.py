"""HR endpointlari (docs/04 §11.1)."""

from __future__ import annotations

from typing import Any

from django.utils import timezone

from apps.branches.selectors import resolve_branch
from apps.core.typing import request_user
from apps.core.viewsets import BranchScopedMixin, TenantViewSet
from apps.hr.models import Employee, EmploymentStatus, Position
from apps.hr.serializers import (
    EmployeeSerializer,
    EmployeeWriteSerializer,
    PositionSerializer,
)

__all__ = ["PositionViewSet", "EmployeeViewSet"]


class PositionViewSet(BranchScopedMixin, TenantViewSet):
    permission_module = "payroll"
    model = Position
    serializer_class = PositionSerializer
    search_fields = ["title", "department"]

    def perform_create(self, serializer: Any) -> None:
        user = request_user(self.request)
        branch = resolve_branch(user, self.request.data.get("branch_id"))
        serializer.save(organization=user.organization, branch=branch)


class EmployeeViewSet(BranchScopedMixin, TenantViewSet):
    permission_module = "payroll"
    model = Employee
    select_related_fields = ("position",)
    search_fields = ["first_name", "last_name", "phone"]
    ordering_fields = ["last_name", "hire_date", "base_salary"]
    filterset_fields = ["employment_status", "position"]

    def get_serializer_class(self) -> Any:
        return (
            EmployeeSerializer
            if self.request.method in ("GET", "HEAD")
            else EmployeeWriteSerializer
        )

    def perform_create(self, serializer: Any) -> None:
        user = request_user(self.request)
        branch = resolve_branch(user, self.request.data.get("branch_id"))
        serializer.save(organization=user.organization, branch=branch)

    def perform_destroy(self, instance: Employee) -> None:
        """
        Xodim o'chirilmaydi — ishdan bo'shatiladi (D5).

        Oylik tarixida uning satrlari qoladi va ular `RESTRICT` bilan
        himoyalangan: o'tgan oylarning hisoblashi buzilmasligi kerak.

        Holat HAR DOIM `terminated` bo'ladi, tarixi bor-yo'qligidan qat'i
        nazar. Avval tarixsiz xodimda faqat `is_active=False` qo'yilardi
        va u ro'yxatda "Ishlayapti" yorlig'i bilan qolib ketardi — ekran
        bazaga zid gapirardi.
        """
        instance.employment_status = EmploymentStatus.TERMINATED
        instance.is_active = False
        if instance.termination_date is None:
            # `ck_employee_termination`: bo'shash sanasi ishga kirishdan
            # oldin bo'lolmaydi — kelajakdagi sana bilan yozilgan xodim
            # bo'shatilsa, sana ishga kirish kuniga tenglashadi.
            instance.termination_date = max(timezone.localdate(), instance.hire_date)
        instance.save(update_fields=["employment_status", "is_active", "termination_date"])
