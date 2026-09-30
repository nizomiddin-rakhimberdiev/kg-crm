"""
Filialga bog'langan har bir endpoint qator YARATA olishini tekshiradi.

`TenantViewSet.perform_create` faqat `organization` ni qo'yadi. `branch`
esa modelda `NOT NULL`, ya'ni viewset o'z `perform_create` ini yozmasa
(yoki `BranchCreateMixin` dan meros olmasa) yaratish bazadagi `NULL`
cheklovga uriladi va mijoz tushunarsiz `409` oladi.

Aynan shu holat `GuardianViewSet` da bor edi: **vasiy qo'shish
endpointi umuman ishlamasdi.** Seed va testlar vasiylarni servis
qatlami orqali yaratgani uchun buni hech narsa ko'rsatmagan — va bu
asosiy oqim, chunki vasiysiz SMS eslatma yuborib bo'lmaydi.

Bu test statik: u har bir viewsetdan "sen filialni qo'yasanmi?" deb
so'raydi. Yangi endpoint qo'shilganda javob "yo'q" bo'lsa, build shu
yerda qizaradi.
"""

from __future__ import annotations

import pytest

from api.v1.router import router
from apps.core.viewsets import BranchScopedMixin, TenantViewSet

# Filial qo'ymaydigan, lekin buni O'ZI hal qiladigan viewsetlar:
# ular `create()` ni to'liq qayta yozgan va servis qatlamini chaqiradi.
CUSTOM_CREATE = {
    "payment": "record_payment() servisi filialni bolasidan oladi",
    "stock-movement": "record_movement() servisi filialni mahsulotdan oladi",
    "payroll-run": "create_run() servisi filialni argument sifatida oladi",
    "payroll-advance": "record_advance() servisi filialni xodimdan oladi",
    "attendance": "mark_bulk() servisi filialni guruhdan oladi",
    "absence-claim": "create_claim() servisi filialni bolasidan oladi",
}


def _branch_scoped_viewsets():
    for _prefix, viewset, basename in router.registry:
        if issubclass(viewset, BranchScopedMixin) and issubclass(viewset, TenantViewSet):
            yield basename, viewset


def test_every_branch_scoped_viewset_sets_the_branch():
    naked = []
    for basename, viewset in _branch_scoped_viewsets():
        if basename in CUSTOM_CREATE:
            continue
        # Bazaviy `perform_create` filialni qo'ymaydi — uni meros qilib
        # olgan viewset yaratishda `NULL` beradi.
        if viewset.perform_create is TenantViewSet.perform_create:
            naked.append(basename)

    assert not naked, (
        f"Bu endpointlar filialni qo'ymaydi va yaratishda 409 beradi: {sorted(naked)}. "
        f"`BranchCreateMixin` dan meros oling yoki o'z `perform_create` ingizni yozing."
    )


def test_custom_create_list_is_still_accurate():
    """Ro'yxatdagi viewset haqiqatan `create()` ni qayta yozgan bo'lsin."""
    registry = dict(_branch_scoped_viewsets())
    stale = set(CUSTOM_CREATE) - set(registry)
    assert not stale, f"CUSTOM_CREATE da mavjud bo'lmagan endpointlar: {sorted(stale)}"

    for basename in CUSTOM_CREATE:
        viewset = registry[basename]
        assert "create" in viewset.__dict__ or any(
            "create" in klass.__dict__ for klass in viewset.__mro__[:3]
        ), f"{basename}: `create()` qayta yozilmagan, lekin istisno ro'yxatida"


@pytest.mark.django_db
def test_guardian_can_actually_be_created(tenant_a):
    """
    Regressiya: vasiy qo'shish HTTP orqali ishlashi kerak.

    Statik tekshiruv yetarli emas — bu test haqiqiy so'rov yuboradi.
    """
    from django.urls import reverse

    response = tenant_a.client().post(
        reverse("v1:guardian-list"),
        {"first_name": "Nodira", "last_name": "Valiyeva", "phone": "+998901234567"},
        format="json",
    )
    assert response.status_code == 201, response.json()
    assert response.json()["data"]["full_name"] == "Valiyeva Nodira"


@pytest.mark.django_db
def test_guardian_created_this_way_can_receive_sms(tenant_a):
    """
    Yaratilgan vasiy bildirishnoma oqimida ishlatilishi mumkin.

    Vasiy — SMS eslatmaning yagona manzili. U yaratilmasa, mahsulotning
    pul keltiradigan qismi ishlamaydi.
    """
    from django.urls import reverse

    created = tenant_a.client().post(
        reverse("v1:guardian-list"),
        {"first_name": "Dilnoza", "last_name": "Karimova", "phone": "+998901112244"},
        format="json",
    )
    guardian_id = created.json()["data"]["id"]

    sent = tenant_a.client().post(
        reverse("v1:notification-send"),
        {
            "template_code": "debt_reminder",
            "guardian_ids": [guardian_id],
            "variables": {
                "guardian": "Dilnoza",
                "child": "Ali",
                "amount": "500000",
                "organization": "Alfa",
            },
        },
        format="json",
    )
    assert sent.status_code == 201
    assert sent.json()["data"]["queued"] == 1
