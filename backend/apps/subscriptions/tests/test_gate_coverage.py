"""
Yozish darvozasi HAR BIR endpointda borligini tekshiradi.

Bu test cross-tenant sweep bilan bir xil falsafada: qoidani odam
yodida saqlashiga tayanmaslik. `SubscriptionWriteGate` ni yangi
viewset'ga qo'shishni unutish "bu endpoint to'lamagan mijozga ham
ishlaydi" degani bo'lardi — va buni hech kim sezmasdi, chunki hamma
narsa normal ishlab turardi.

Nega global `DEFAULT_PERMISSION_CLASSES` yetarli emas: DRF'da view
`permission_classes` ni e'lon qilishi bilan default BUTUNLAY qoplanadi,
va bu loyihada har bir viewset uni e'lon qiladi. Sozlamaga yozish
"himoya bor" degan tuyg'u berardi, aslida esa hech qayerda ishlamasdi —
bu aynan shu sprintda topilgan xato.
"""

from __future__ import annotations

from typing import Any

from api.v1.router import router
from apps.subscriptions.permissions import SubscriptionWriteGate

# Darvozasiz qoladigan endpointlar — har biri sabab bilan.
GATE_EXEMPT: dict[str, str] = {
    "billing": "Hisobni koʻrish va toʻlash yoʻli ochiq qolishi shart.",
    "platform": "Vendor tekisligi — mijoz obunasiga umuman bogʻliq emas (ADR-10).",
}


def test_write_gate_is_everywhere():
    missing = []
    for _prefix, viewset, basename in router.registry:
        if basename in GATE_EXEMPT:
            continue
        classes = getattr(viewset, "permission_classes", [])
        if SubscriptionWriteGate not in classes:
            missing.append(basename)

    assert not missing, (
        f"Bu endpointlarda obuna darvozasi yoʻq: {sorted(missing)}. "
        f"Yaʼni toʻlamagan mijoz ularga yozishda davom etadi. "
        f"`permission_classes` ga `SubscriptionWriteGate` qoʻshing yoki "
        f"GATE_EXEMPT ga sabab yozing."
    )


def test_exemptions_are_still_real():
    """Kerak boʻlmay qolgan istisno roʻyxatda qolib ketmasin."""
    basenames = {basename for _p, _v, basename in router.registry}
    stale = set(GATE_EXEMPT) - basenames
    assert not stale, f"GATE_EXEMPT da mavjud boʻlmagan endpointlar: {sorted(stale)}"


# --- Routerdan TASHQARIDAGI yozuv endpointlari ---------------------
#
# Yuqoridagi test faqat `router.registry` ni koʻradi, yaʼni oddiy
# `APIView` undan butunlay chetda qoladi. Bu — cross-tenant sweep va
# RLS roʻyxati bilan bir xil koʻr nuqta: qoida bor, lekin u faqat
# qoidani ESLAGAN odam yozgan joyda ishlaydi.
#
# Istisnolar roʻyxati ataylab qoʻlda va sabab bilan. Invariant 11
# aytadi: toʻxtatilgan obuna YOZISHNI toʻxtatadi, KIRISHNI emas —
# demak toʻlamagan mijoz tizimga kira olishi, parolini tiklay olishi
# va hisobini toʻlay olishi SHART, aks holda u toʻlash yoʻlidan ham
# mahrum boʻlardi.

UNGATED_VIEWS: dict[str, str] = {
    # Kirish yoʻli — usiz mijoz toʻlash sahifasiga ham yetib bormaydi.
    "LoginView": "Kirish — toʻxtatilgan obunada ham ochiq (invariant 11).",
    "LogoutView": "Chiqish hech qachon toʻsilmaydi.",
    "RefreshView": "Token yangilash — kirishning davomi.",
    "SelectOrganizationView": "Bir nechta tashkilotdan birini tanlash — kirish qadami.",
    # Hisobni tiklash va himoyalash.
    "PasswordResetRequestView": "Parolni tiklash — toʻlovdan oldin kerak boʻlishi mumkin.",
    "PasswordResetConfirmView": "Parolni tiklash — toʻlovdan oldin kerak boʻlishi mumkin.",
    "PasswordChangeView": "Oʻz parolini oʻzgartirish hech qachon toʻsilmaydi.",
    "TwoFactorSetupView": "2FA — xavfsizlik, obunaga bogʻliq emas (ADR-24).",
    "TwoFactorConfirmView": "2FA — xavfsizlik, obunaga bogʻliq emas (ADR-24).",
    "TwoFactorDisableView": "2FA — xavfsizlik, obunaga bogʻliq emas (ADR-24).",
    "TwoFactorBackupCodesView": "2FA — xavfsizlik, obunaga bogʻliq emas (ADR-24).",
    # Taklif YARATISH `/users` orqali va u darvozali; bu yerda esa
    # boshlangan ishni tugatish. Toʻsish odamni yarim yoʻlda qoldirardi.
    "InviteAcceptView": "Taklifni qabul qilish — yaratilishi allaqachon darvozadan oʻtgan.",
    # Oʻz profili — pul bilan bogʻliq emas, toʻsish faqat gʻashlik.
    "MeView": "Oʻz profili.",
    "ProfilePhotoView": "Oʻz rasmi.",
    "TelegramLinkView": "Oʻz Telegram ulanishi — xavfsizlik va xabarlar, obunaga bogʻliq emas.",
    # Vendor tekisligi (ADR-10).
    "PlatformLoginView": "Vendor tekisligi — mijoz obunasiga bogʻliq emas.",
    # Ommaviy yoʻllar: tenant hali yoʻq yoki PUL KIRIB kelyapti.
    # Toʻlov webhook'ini darvozaga qoʻyish toʻxtatilgan mijozning
    # toʻlovini rad etardi — yaʼni darvoza oʻzini oʻzi yopib qoʻyardi.
    "PublicLeadCreateView": "Ommaviy forma — tenant hali yoʻq.",
    "SignupRequestView": "Roʻyxatdan oʻtish — tenant hali yoʻq (ADR-28).",
    "SignupConfirmView": "Roʻyxatdan oʻtish — tenant shu yerda tugʻiladi (ADR-28).",
    "PaymeWebhookView": "PUL KIRYAPTI — toʻxtatilgan mijoz aynan shu yoʻl bilan toʻlaydi.",
    "ClickWebhookView": "PUL KIRYAPTI — toʻxtatilgan mijoz aynan shu yoʻl bilan toʻlaydi.",
    "SubscriptionPaymeWebhookView": "Obuna toʻlovi — darvoza buni toʻsmasligi SHART.",
    "SubscriptionClickWebhookView": "Obuna toʻlovi — darvoza buni toʻsmasligi SHART.",
    "TelegramWebhookView": "Ota-ona boti — kiruvchi xabar, mijoz yozuvi emas.",
}

WRITE_METHODS = ("post", "put", "patch", "delete")


def _standalone_write_views() -> dict[str, Any]:
    """Routerdan tashqaridagi, yozish usuli bor view'lar."""
    from django.urls import get_resolver

    def walk(resolver: Any, prefix: str = "") -> Any:
        for pattern in resolver.url_patterns:
            if hasattr(pattern, "url_patterns"):
                yield from walk(pattern, prefix + str(pattern.pattern))
            else:
                yield prefix + str(pattern.pattern), pattern.callback

    found: dict[str, Any] = {}
    for path, callback in walk(get_resolver()):
        if "api/v1" not in path:
            continue
        view = getattr(callback, "cls", None) or getattr(callback, "view_class", None)
        if view is None:
            continue
        # ViewSet'lar routerdan keladi — ular yuqoridagi testda.
        if "suffix" in (getattr(callback, "initkwargs", None) or {}):
            continue
        if any(hasattr(view, method) for method in WRITE_METHODS):
            found[view.__name__] = view
    return found


def test_every_standalone_write_view_is_gated_or_explained():
    """
    `APIView` ham qoidadan chetda qolmasin.

    Yangi yozuv endpointi qoʻshilsa, muallif ikki narsadan birini
    tanlashi kerak: yo darvozani qoʻyish, yo bu yerga SABAB yozish.
    Jimgina oʻtib ketish yoʻli yoʻq.
    """
    missing = [
        name
        for name, view in _standalone_write_views().items()
        if name not in UNGATED_VIEWS
        and SubscriptionWriteGate not in getattr(view, "permission_classes", [])
    ]
    assert not missing, (
        f"Bu yozuv endpointlarida obuna darvozasi ham, sabab ham yoʻq: {sorted(missing)}. "
        f"`permission_classes` ga `SubscriptionWriteGate` qoʻshing yoki "
        f"`UNGATED_VIEWS` ga sabab yozing."
    )


def test_the_ungated_list_has_no_leftovers():
    """Oʻchirilgan view roʻyxatda qolib ketmasin."""
    live = set(_standalone_write_views())
    stale = set(UNGATED_VIEWS) - live
    assert not stale, f"UNGATED_VIEWS da mavjud boʻlmagan view'lar: {sorted(stale)}"
