"""
Narx hisoblash (docs/01 §4.2–4.3).

Bu fayl ataylab **sof**: bazaga ham, so'rovga ham, vaqtga ham bog'liq
emas. Sabab oddiy — bu yerdagi xato mijozga noto'g'ri hisob yuboradi, va
noto'g'ri hisob bitta xatodan ko'ra ko'proq narsani buzadi: u ishonchni
buzadi. Sof funksiyani esa har bir chegara qiymatida sinash arzon.

Formula:

    hisoblanadigan bolalar = MAX(eng yuqori son, planga kiritilgan son)
    ortiqcha qadamlar      = TEPAGA(( hisoblanadigan − kiritilgan ) / qadam)
    baza                   = plan bazasi × oylar
    ortiqcha               = qadamlar × qadam narxi × oylar
    chegirma               = (baza + ortiqcha) × foiz
    jami                   = baza + ortiqcha − chegirma

**Nega 10 talik qadam, har bola uchun emas:** mijozlar yuridik shaxs va
schyot-faktura asosida bank orqali to'laydi. Har oy bir necha ming so'mga
o'zgaradigan hisob buxgalteriyada ishqalanish va bahs tug'diradi. Qadam
hisobni chegara kesib o'tilmaguncha barqaror ushlab turadi.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

__all__ = ["Quote", "billable_children", "overage_steps", "quote"]

CENT = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    """Pulni ikki xonagacha yaxlitlaydi (yarmi yuqoriga)."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Quote:
    """Bitta hisob-faktura uchun hisoblangan summalar."""

    billable_children: int
    included_children: int
    overage_steps: int
    months: int
    base_amount: Decimal
    overage_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    currency: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "billable_children": self.billable_children,
            "included_children": self.included_children,
            "overage_steps": self.overage_steps,
            "months": self.months,
            "base_amount": f"{self.base_amount:.2f}",
            "overage_amount": f"{self.overage_amount:.2f}",
            "discount_amount": f"{self.discount_amount:.2f}",
            "total_amount": f"{self.total_amount:.2f}",
            "currency": self.currency,
        }


def billable_children(*, peak: int, included: int) -> int:
    """
    Hisoblanadigan bolalar soni.

    Kiritilgan son bir vaqtning o'zida **eng past chegara**: 12 ta bolasi
    bor bog'cha ham bazani to'laydi. Bu chegirma emas, daromad poli —
    xizmatning o'zi bolalar soniga qarab arzonlashmaydi (docs/01 §4.2).
    """
    return max(int(peak), int(included))


def overage_steps(*, billable: int, included: int, step: int) -> int:
    """
    Ortiqcha qadamlar soni — TEPAGA yaxlitlanadi.

    Bitta ortiqcha bola ham to'liq qadamni yoqadi. Aks holda 51 va 59 bola
    bir xil pul to'lardi, keyin 60-bolada hisob birdan sakrardi va bu
    mijozga tushunarsiz ko'rinardi.
    """
    if step <= 0:
        raise ValueError("Qadam noldan katta bo'lishi kerak.")
    extra = max(0, int(billable) - int(included))
    return -(-extra // step)  # tepaga bo'lish


def quote(
    *,
    plan: Any,
    peak_children: int,
    discount_percent: Decimal = Decimal("0"),
    months: int = 1,
    include_base: bool = True,
    covered_children: int | None = None,
) -> Quote:
    """
    Berilgan plan va bolalar soni uchun summalarni hisoblaydi.

    `include_base=False` — oldindan to'langan muddat ichidagi OYLIK
    ortiqcha hisobi uchun: baza allaqachon to'langan, faqat o'sish
    hisoblanadi (docs/01 §4.3).

    `covered_children` — mijoz ALLAQACHON to'lagan bolalar soni.
    Oldindan to'lovda (yarim yillik / yillik) mijoz `committed_children`
    uchun pul to'lagan, ya'ni ortiqcha faqat SHU SONDAN oshgani uchun
    olinadi. Ko'rsatilmasa plandagi `included_children` ishlatiladi —
    oylik muddat uchun bu ikkisi bir xil.

    Busiz ikkita zarar bor edi:
      * prognoz har oy mavjud bo'lmagan hisobni ko'rsatardi —
        "kutilmagan hisob yo'q" va'dasining teskarisi;
      * o'sgan prepaid mijozdan ortiqcha pul olinardi. 64 tadan 71 ga
        o'sgan mijozdan bitta qadam emas, uchta qadam undirilardi.

    Chegirma bazaga ham, ortiqchaga ham bir xil foizda qo'llanadi:
    hujjatda "ortiqcha qadamlar ... o'sha chegirma stavkasida" deb
    yozilgan.
    """
    if months < 1:
        raise ValueError("Oylar soni kamida 1 bo'lishi kerak.")

    included = int(plan.included_children)
    # Bepul chegara: oldindan to'langan son plandagi sondan kam
    # bo'la olmaydi — baza baribir 50 tagacha qamrab oladi.
    covered = max(int(covered_children), included) if covered_children is not None else included
    billable = billable_children(peak=peak_children, included=included)
    steps = overage_steps(billable=billable, included=covered, step=int(plan.overage_step_children))

    base = _money(Decimal(plan.base_price) * months) if include_base else Decimal("0.00")
    overage = _money(Decimal(plan.overage_step_price) * steps * months)

    percent = Decimal(discount_percent or 0)
    discount = _money((base + overage) * percent / Decimal("100"))
    total = _money(base + overage - discount)

    return Quote(
        billable_children=billable,
        included_children=included,
        overage_steps=steps,
        months=months,
        base_amount=base,
        overage_amount=overage,
        discount_amount=discount,
        total_amount=total,
        currency=plan.currency,
    )
