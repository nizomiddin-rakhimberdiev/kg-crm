"""
Parol siyosati (PLAN 11.10).

Minimal uzunlik Django sukuti (8) emas, 12 — tizim bolalarning
shaxsiy maʼlumotini va pulni saqlaydi, OWASP ASVS esa shunday ilova
uchun 12 ni talab qiladi.

Mavjud parollar tegilmaydi: validator faqat parol OʻRNATILGANDA
ishlaydi. Bu test shuni ham qoʻriqlaydi — siyosat kuchaysa-yu,
mavjud foydalanuvchilar kira olmay qolsa, bu tuzatish emas, avariya
boʻlardi.
"""

from __future__ import annotations

from typing import Any

import pytest
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from apps.core.tenancy import organization_context

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]


@pytest.mark.parametrize("password", ["Qisqa1!", "11 belgi!!", "bahor2026b"])
def test_a_short_password_is_refused(password: str):
    with pytest.raises(ValidationError):
        validate_password(password)


def test_a_long_passphrase_passes_without_complexity_rules():
    """
    Murakkablik qoidasi yoʻq — uzunlik yetarli.

    Aynan murakkablik xodimni parolni qogʻozga yozishga majbur
    qiladi; "bahorbogchasi2026" esa oson eslanadi.
    """
    validate_password("bahorbogchasi2026")


def test_a_long_but_common_password_is_still_refused():
    """Uzunlikning oʻzi yetarli emas — roʻyxatdagi parol baribir rad etiladi."""
    with pytest.raises(ValidationError):
        validate_password("password1234")


def test_existing_users_can_still_sign_in(tenant_a: Any):
    """
    Siyosat kuchayishi hech kimni tizimdan chiqarib yubormaydi:
    validator faqat yangi parolga qoʻllanadi.
    """
    from apps.accounts.models import User

    short = "Qisqa-1!"  # noqa: S105 — test maʼlumoti, 12 dan kalta
    with organization_context(tenant_a.organization.id):
        user = User.objects.get(pk=tenant_a.owner.pk)
        # Validatorni chetlab oʻtib oʻrnatamiz — "eskidan qolgan" parol.
        user.set_password(short)
        user.save(update_fields=["password"])
        assert user.check_password(short)
