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
