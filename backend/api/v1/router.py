"""
API kompozitsiya ildizi — barcha modul router'lari shu yerda yig'iladi.

Har bir yangi app o'z ViewSet'ini shu yerga ro'yxatdan o'tkazadi (docs/02 §5).
"""

from rest_framework.routers import DefaultRouter

from apps.accounts.views import PermissionViewSet, RoleViewSet, UserViewSet
from apps.attendance.views import AbsenceClaimViewSet, AttendanceViewSet, HolidayViewSet
from apps.audit.views import AuditLogViewSet
from apps.branches.views import BranchViewSet
from apps.children.views import ChildViewSet, GroupViewSet, GuardianViewSet
from apps.core.deployment import is_saas
from apps.expenses.views import ExpenseCategoryViewSet, ExpenseViewSet
from apps.finance.views import (
    DebtorViewSet,
    DiscountViewSet,
    InvoiceViewSet,
    LedgerViewSet,
    PaymentViewSet,
    TariffPlanViewSet,
)
from apps.hr.views import EmployeeViewSet, PositionViewSet
from apps.intelligence.views import InsightViewSet
from apps.inventory.views import (
    ProductCategoryViewSet,
    ProductViewSet,
    StockMovementViewSet,
    SupplierViewSet,
    WarehouseViewSet,
)
from apps.notifications.views import NotificationTemplateViewSet, NotificationViewSet
from apps.payroll.views import EmployeeAdvanceViewSet, PayrollRunViewSet
from apps.platform.views import PlatformConsoleViewSet
from apps.reports.views import DashboardViewSet, ReportViewSet
from apps.settings_app.views import SettingsViewSet
from apps.subscriptions.views import BillingViewSet

router = DefaultRouter(trailing_slash=False)

router.register("users", UserViewSet, basename="user")
router.register("roles", RoleViewSet, basename="role")
router.register("permissions", PermissionViewSet, basename="permission")
router.register("branches", BranchViewSet, basename="branch")
router.register("children", ChildViewSet, basename="child")
router.register("guardians", GuardianViewSet, basename="guardian")
router.register("groups", GroupViewSet, basename="group")
router.register("attendance", AttendanceViewSet, basename="attendance")
# Kelmagan kunlar uchun qaytarish va bayram kalendari (ADR-19).
router.register("absence-claims", AbsenceClaimViewSet, basename="absence-claim")
router.register("holidays", HolidayViewSet, basename="holiday")
router.register("tariffs", TariffPlanViewSet, basename="tariff")
router.register("discounts", DiscountViewSet, basename="discount")
router.register("invoices", InvoiceViewSet, basename="invoice")
router.register("ledger", LedgerViewSet, basename="ledger")
router.register("payments", PaymentViewSet, basename="payment")
router.register("debtors", DebtorViewSet, basename="debtor")
router.register("employees", EmployeeViewSet, basename="employee")
router.register("positions", PositionViewSet, basename="position")
router.register("payroll/runs", PayrollRunViewSet, basename="payroll-run")
router.register("payroll/advances", EmployeeAdvanceViewSet, basename="payroll-advance")
router.register("warehouses", WarehouseViewSet, basename="warehouse")
router.register("product-categories", ProductCategoryViewSet, basename="product-category")
router.register("products", ProductViewSet, basename="product")
router.register("suppliers", SupplierViewSet, basename="supplier")
router.register("stock-movements", StockMovementViewSet, basename="stock-movement")
router.register("expense-categories", ExpenseCategoryViewSet, basename="expense-category")
router.register("expenses", ExpenseViewSet, basename="expense")
router.register("notifications", NotificationViewSet, basename="notification")
router.register(
    "notification-templates", NotificationTemplateViewSet, basename="notification-template"
)
router.register("settings", SettingsViewSet, basename="setting")
router.register("dashboard", DashboardViewSet, basename="dashboard")
router.register("reports", ReportViewSet, basename="report")
router.register("audit-logs", AuditLogViewSet, basename="audit-log")
router.register("insights", InsightViewSet, basename="insight")

# Obuna va vendor konsoli — FAQAT SaaS nusxasida (ADR-13). Standalone'da
# obuna ob'ekti umuman yaratilmaydi, ya'ni bu yo'llar bo'sh yoki chalkash
# javob berardi.
if is_saas():
    router.register("billing", BillingViewSet, basename="billing")
    router.register("platform", PlatformConsoleViewSet, basename="platform")

__all__ = ["router"]
