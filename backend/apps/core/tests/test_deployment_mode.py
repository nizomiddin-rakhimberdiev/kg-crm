"""
Standalone rejimi — bitta bog'cha uchun sotiladigan nusxa (ADR-13).

Bu testlar bitta savolga javob beradi: bayroq YOQILGANDA mahsulot
haqiqatan boshqacha ishlaydimi, yoki faqat UI da shunday ko'rinadimi.
Ikkinchisi xavfli bo'lardi — yashiringan, lekin javob beradigan yo'l
ochiq yo'ldir.
"""

from __future__ import annotations

import pytest
from django.test import override_settings

from apps.core.deployment import is_saas, is_standalone
from apps.core.tenant_address import tenant_base_url

pytestmark = pytest.mark.django_db


# --- Bayroqning o'zi ---


def test_default_is_saas():
    """Bayroq berilmasa — SaaS. Mavjud oʻrnatmalar oʻzgarmasligi kerak."""
    assert is_saas()
    assert not is_standalone()


@override_settings(DEPLOYMENT_MODE="standalone")
def test_standalone_flag_reads_settings():
    assert is_standalone()
    assert not is_saas()


# --- Manzil ---


@override_settings(PUBLIC_BASE_URL="https://bogcha.uz", TENANT_URL_STYLE="path")
def test_saas_address_keeps_tenant_prefix():
    assert tenant_base_url("quyosh") == "https://bogcha.uz/t/quyosh"


@override_settings(
    PUBLIC_BASE_URL="https://bogcha.uz", TENANT_URL_STYLE="path", DEPLOYMENT_MODE="standalone"
)
def test_standalone_address_is_the_root():
    """Bitta bogʻcha — prefiks hech narsani ajratmaydi."""
    assert tenant_base_url("quyosh") == "https://bogcha.uz"


# --- Sinov muddati ---


@override_settings(DEPLOYMENT_MODE="standalone")
def test_standalone_registration_creates_no_subscription():
    from apps.accounts.services import register_organization
    from apps.core.tenancy import organization_context
    from apps.subscriptions.models import Subscription

    result = register_organization(
        organization_name="Yakka bogʻcha",
        contact_email="ega@example.com",
        full_name="Ega Egayev",
        password="parol-12345",  # noqa: S106
    )

    with organization_context(result.organization.id):
        assert not Subscription.objects.filter(organization=result.organization).exists()


def test_saas_registration_starts_a_trial():
    """Teskari tomoni ham qotirilgan: SaaSʼda sinov ochilishi SHART."""
    from apps.accounts.services import register_organization
    from apps.core.tenancy import organization_context
    from apps.subscriptions.models import Subscription

    result = register_organization(
        organization_name="Obunali bogʻcha",
        contact_email="ega2@example.com",
        full_name="Ega Egayev",
        password="parol-12345",  # noqa: S106
    )

    with organization_context(result.organization.id):
        assert Subscription.objects.filter(organization=result.organization).exists()


# --- Yozish darvozasi ---


@override_settings(DEPLOYMENT_MODE="standalone")
def test_gate_opens_even_for_a_suspended_subscription():
    """
    Standalone'da darvoza obunaga UMUMAN qaramaydi.

    Ataylab eng yomon holat olingan: baza SaaS'dan ko'chirilgan va
    unda `suspended` obuna qolib ketgan. Mijoz tizimni sotib olgan —
    eski obuna yozuvi uni yozishdan to'xtatmasligi kerak.
    """
    from apps.subscriptions.permissions import SubscriptionWriteGate

    class _Request:
        method = "POST"
        path = "/api/v1/children"
        user = None

    # Foydalanuvchi ham, obuna ham o'qilmaydi — darvoza undan oldin ochiladi.
    assert SubscriptionWriteGate().has_permission(_Request(), view=None) is True


# --- Marshrutlar ---


def test_saas_routes_include_billing_and_platform():
    from api.v1.router import router

    basenames = {basename for _p, _v, basename in router.registry}
    assert {"billing", "platform"} <= basenames
