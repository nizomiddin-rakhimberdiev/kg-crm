"""
API kompozitsiya ildizi — barcha modul router'lari shu yerda yig'iladi.

Har bir yangi app o'z ViewSet'ini shu yerga ro'yxatdan o'tkazadi (docs/02 §5).
"""

from rest_framework.routers import DefaultRouter

from apps.accounts.views import PermissionViewSet, RoleViewSet, UserViewSet
from apps.attendance.views import AttendanceViewSet
from apps.branches.views import BranchViewSet
from apps.children.views import ChildViewSet, GroupViewSet, GuardianViewSet
from apps.finance.views import (
    DebtorViewSet,
    DiscountViewSet,
    InvoiceViewSet,
    LedgerViewSet,
    PaymentViewSet,
    TariffPlanViewSet,
)
from apps.hr.views import EmployeeViewSet, PositionViewSet
from apps.payroll.views import PayrollRunViewSet

router = DefaultRouter(trailing_slash=False)

router.register("users", UserViewSet, basename="user")
router.register("roles", RoleViewSet, basename="role")
router.register("permissions", PermissionViewSet, basename="permission")
router.register("branches", BranchViewSet, basename="branch")
router.register("children", ChildViewSet, basename="child")
router.register("guardians", GuardianViewSet, basename="guardian")
router.register("groups", GroupViewSet, basename="group")
router.register("attendance", AttendanceViewSet, basename="attendance")
router.register("tariffs", TariffPlanViewSet, basename="tariff")
router.register("discounts", DiscountViewSet, basename="discount")
router.register("invoices", InvoiceViewSet, basename="invoice")
router.register("ledger", LedgerViewSet, basename="ledger")
router.register("payments", PaymentViewSet, basename="payment")
router.register("debtors", DebtorViewSet, basename="debtor")
router.register("employees", EmployeeViewSet, basename="employee")
router.register("positions", PositionViewSet, basename="position")
router.register("payroll/runs", PayrollRunViewSet, basename="payroll-run")

__all__ = ["router"]
