"""
Tip yordamchilari.

django-stubs `request.user` ni `User | AnonymousUser` deb biladi, lekin
bizda `DEFAULT_PERMISSION_CLASSES = [IsAuthenticated]` — ya'ni view tanasiga
yetib borgan har qanday so'rovda foydalanuvchi mavjud. Bu yordamchi shu
kafilnomani bir joyda, aniq ifodalaydi (har bir chaqiruvda `# type: ignore`
sochib yurish o'rniga).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework.request import Request

if TYPE_CHECKING:
    from apps.accounts.models import User

__all__ = ["request_user"]


def request_user(request: Request) -> User:
    """Autentifikatsiya qilingan foydalanuvchini qaytaradi."""
    user = request.user
    if user is None or not user.is_authenticated:  # pragma: no cover — himoya
        raise AssertionError(
            "request_user() faqat autentifikatsiya talab qiladigan view'da "
            "chaqiriladi (IsAuthenticated)."
        )
    return user
