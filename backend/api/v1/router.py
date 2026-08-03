"""
API kompozitsiya ildizi — barcha modul router'lari shu yerda yig'iladi.

Har bir yangi app o'z ViewSet'ini shu yerga ro'yxatdan o'tkazadi (docs/02 §5).
"""

from rest_framework.routers import DefaultRouter

from apps.accounts.views import PermissionViewSet, RoleViewSet, UserViewSet
from apps.branches.views import BranchViewSet
from apps.children.views import ChildViewSet, GroupViewSet, GuardianViewSet

router = DefaultRouter(trailing_slash=False)

router.register("users", UserViewSet, basename="user")
router.register("roles", RoleViewSet, basename="role")
router.register("permissions", PermissionViewSet, basename="permission")
router.register("branches", BranchViewSet, basename="branch")
router.register("children", ChildViewSet, basename="child")
router.register("guardians", GuardianViewSet, basename="guardian")
router.register("groups", GroupViewSet, basename="group")

__all__ = ["router"]
