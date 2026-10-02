"""
Narx testlari (docs/01 §4.2–4.3).

Bu fayl loyihadagi eng qimmat testlar to'plami: bu yerdagi xato mijozga
noto'g'ri hisob yuboradi. Noto'g'ri hisob bitta xatodan ko'ra ko'proq
narsani buzadi — u ishonchni buzadi, va ishonch qaytmaydi.

Shuning uchun HAR BIR chegara qiymati alohida sinaladi: 49, 50, 51, 59,
60, 61. Aynan chegaralarda "tepaga yaxlitlash" va "eng past chegara"
qoidalari to'qnashadi.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import pytest

from apps.subscriptions import pricing


@dataclass(frozen=True)
class FakePlan:
    """Bazasiz plan — narx mantiqi bazaga bogʻliq emasligini koʻrsatadi."""

    base_price: Decimal = Decimal("500000.00")
    included_children: int = 50
    overage_step_children: int = 10
    overage_step_price: Decimal = Decimal("80000.00")
    currency: str = "UZS"


PLAN = FakePlan()


class TestDocumentedExamples:
    """Hujjatda yozilgan raqamlar (docs/01 §4.2) — aynan shu qiymatlar."""

    @pytest.mark.parametrize(
        "children,expected",
        [
            (50, "500000.00"),
            (80, "740000.00"),
            (150, "1300000.00"),
            (300, "2500000.00"),
        ],
    )
    def test_worked_examples(self, children, expected):
        assert pricing.quote(plan=PLAN, peak_children=children).total_amount == Decimal(expected)


class TestFloor:
    """Kiritilgan son — daromad poli, taxmin emas."""

    @pytest.mark.parametrize("children", [0, 1, 12, 49])
    def test_fewer_children_still_pay_the_base(self, children):
        """
        50 tadan kam bolasi bor bog'cha ham bazani to'laydi.

        Xizmatning o'zi bolalar soniga qarab arzonlashmaydi: server ham,
        yordam ham, yangilanish ham bir xil. Bu chegirma emas, pol
        (docs/01 §4.2).
        """
        quote = pricing.quote(plan=PLAN, peak_children=children)
        assert quote.total_amount == Decimal("500000.00")
        assert quote.billable_children == 50
        assert quote.overage_steps == 0

    def test_zero_children_is_not_zero_money(self):
        """Boʻsh bogʻcha ham bazani toʻlaydi — obuna toʻxtatilmaguncha."""
        assert pricing.quote(plan=PLAN, peak_children=0).total_amount == Decimal("500000.00")


class TestTierBoundaries:
    """
    Chegaralar — narx mantiqidagi eng xavfli nuqtalar.

    Bitta ortiqcha bola ham to'liq qadamni yoqadi. Aks holda 51 va 59
    bola bir xil pul to'lardi, keyin 60-bolada hisob birdan ikki qadamga
    sakrardi — va mijoz buni "tizim adashdi" deb ko'rardi.
    """

    @pytest.mark.parametrize(
        "children,steps,total",
        [
            (49, 0, "500000.00"),
            (50, 0, "500000.00"),
            (51, 1, "580000.00"),
            (59, 1, "580000.00"),
            (60, 1, "580000.00"),
            (61, 2, "660000.00"),
            (69, 2, "660000.00"),
            (70, 2, "660000.00"),
            (71, 3, "740000.00"),
        ],
    )
    def test_each_boundary(self, children, steps, total):
        quote = pricing.quote(plan=PLAN, peak_children=children)
        assert quote.overage_steps == steps, f"{children} bola uchun qadamlar notoʻgʻri"
        assert quote.total_amount == Decimal(total)

    def test_price_never_goes_down_as_children_increase(self):
        """
        Bola qo'shilishi hisobni HECH QACHON kamaytirmaydi.

        Bu oddiy ko'rinadi, lekin yaxlitlash yoki chegirma mantiqidagi
        xato aynan shu xossani buzadi va uni ko'z bilan sezish qiyin.
        """
        previous = Decimal("0")
        for children in range(0, 320):
            total = pricing.quote(plan=PLAN, peak_children=children).total_amount
            assert total >= previous, f"{children} bolada narx tushib ketdi"
            previous = total


class TestDiscounts:
    """Chegirma bazaga ham, ortiqchaga ham bir xil foizda (docs/01 §4.3)."""

    def test_annual_is_25_percent(self):
        quote = pricing.quote(
            plan=PLAN, peak_children=50, discount_percent=Decimal("25"), months=12
        )
        assert quote.base_amount == Decimal("6000000.00")  # 500 000 × 12
        assert quote.discount_amount == Decimal("1500000.00")
        assert quote.total_amount == Decimal("4500000.00")

    def test_semiannual_is_15_percent(self):
        quote = pricing.quote(plan=PLAN, peak_children=50, discount_percent=Decimal("15"), months=6)
        assert quote.base_amount == Decimal("3000000.00")
        assert quote.discount_amount == Decimal("450000.00")
        assert quote.total_amount == Decimal("2550000.00")

    def test_monthly_has_no_discount(self):
        quote = pricing.quote(plan=PLAN, peak_children=50, discount_percent=Decimal("0"))
        assert quote.discount_amount == Decimal("0.00")
        assert quote.total_amount == Decimal("500000.00")

    def test_overage_carries_the_same_discount(self):
        """
        Ortiqcha ham chegirma stavkasida hisoblanadi.

        Hujjat: "ortiqcha qadamlar ... o'sha chegirma stavkasida
        hisoblanadi". Agar chegirma faqat bazaga qo'llansa, yillik
        to'lagan mijoz o'sish uchun to'liq narx to'lardi va bu
        kelishuvning ruhiga zid bo'lardi.
        """
        quote = pricing.quote(plan=PLAN, peak_children=80, discount_percent=Decimal("25"), months=1)
        # baza 500 000 + ortiqcha 240 000 = 740 000; 25 % = 185 000
        assert quote.overage_amount == Decimal("240000.00")
        assert quote.discount_amount == Decimal("185000.00")
        assert quote.total_amount == Decimal("555000.00")


class TestOverageOnly:
    """Oldindan toʻlangan muddat ichidagi oylik oʻsish hisobi."""

    def test_base_is_excluded_when_already_prepaid(self):
        """
        Baza ikki marta olinmaydi.

        Yillik to'lagan mijozdan har oy yana baza olish — eng og'ir
        turdagi xato: u mijozning pulini ikki marta oladi va buni
        payqash uchun mijoz o'zi hisob-kitob qilishi kerak bo'ladi.
        """
        quote = pricing.quote(
            plan=PLAN,
            peak_children=80,
            discount_percent=Decimal("25"),
            include_base=False,
        )
        assert quote.base_amount == Decimal("0.00")
        assert quote.overage_amount == Decimal("240000.00")
        assert quote.total_amount == Decimal("180000.00")  # 240 000 − 25 %

    def test_no_growth_means_nothing_to_bill(self):
        quote = pricing.quote(plan=PLAN, peak_children=50, include_base=False)
        assert quote.total_amount == Decimal("0.00")


class TestRounding:
    def test_amounts_always_have_two_decimals(self):
        """Sxema `NUMERIC(12,2)` — natija ham shunday boʻlishi kerak."""
        quote = pricing.quote(plan=PLAN, peak_children=73, discount_percent=Decimal("15"), months=6)
        for amount in (
            quote.base_amount,
            quote.overage_amount,
            quote.discount_amount,
            quote.total_amount,
        ):
            assert amount == amount.quantize(Decimal("0.01"))

    def test_total_always_equals_the_parts(self):
        """
        Bu ayniyat bazadagi `CHECK` bilan bir xil.

        Kod va baza kelishmasa, hisob-faktura umuman yozilmaydi — lekin
        bu xato ishlab chiqarishda emas, shu yerda topilishi kerak.
        """
        for children in (0, 50, 51, 137, 300):
            for percent in (Decimal("0"), Decimal("15"), Decimal("25")):
                for months in (1, 6, 12):
                    quote = pricing.quote(
                        plan=PLAN,
                        peak_children=children,
                        discount_percent=percent,
                        months=months,
                    )
                    assert (
                        quote.total_amount
                        == quote.base_amount + quote.overage_amount - quote.discount_amount
                    )


class TestGuards:
    def test_zero_step_is_rejected(self):
        """Nol qadam — cheksiz tsikl yoki nolga boʻlish; oldindan toʻxtatiladi."""
        with pytest.raises(ValueError, match="Qadam"):
            pricing.overage_steps(billable=60, included=50, step=0)

    def test_zero_months_is_rejected(self):
        with pytest.raises(ValueError, match="Oylar"):
            pricing.quote(plan=PLAN, peak_children=50, months=0)


class TestPlanVersioning:
    def test_a_new_price_does_not_touch_the_old_quote(self):
        """
        Eski plan versiyasi eski narxni beradi.

        Mijozning narxi uning ostidan jimgina o'zgarib ketmasligi kerak —
        UZS inflyatsiyasi sharoitida bu ayniqsa muhim (docs/01 §10).
        """
        old = FakePlan(base_price=Decimal("500000.00"))
        new = FakePlan(base_price=Decimal("650000.00"))
        assert pricing.quote(plan=old, peak_children=50).total_amount == Decimal("500000.00")
        assert pricing.quote(plan=new, peak_children=50).total_amount == Decimal("650000.00")


class TestPrepaidCoverage:
    """
    Oldindan to'langan mijozdan ikki marta pul olinmasligi kerak.

    Yarim yillik yoki yillik to'lovda mijoz `committed_children` uchun
    oldindan to'laydi — baza ham, o'sha sondagi ortiqcha ham. Keyingi
    oylarda faqat SHU SONDAN oshgani hisoblanadi.

    Avval `quote()` har doim plandagi 50 dan hisoblardi, ya'ni:
      * prognoz har oy hech qachon kelmaydigan hisobni ko'rsatardi;
      * o'sgan mijozdan uch barobar ko'p pul undirilardi.
    """

    def test_no_growth_means_nothing_to_bill(self):
        """64 bolaga toʻlagan mijozda 64 bola qolsa — hisob nol."""
        quote = pricing.quote(
            plan=PLAN,
            peak_children=64,
            covered_children=64,
            discount_percent=Decimal("15"),
            include_base=False,
        )
        assert quote.overage_steps == 0
        assert quote.total_amount == Decimal("0.00")

    def test_only_growth_beyond_the_committed_count_is_billed(self):
        """
        64 → 71 bola: BITTA qadam, uchta emas.

        Eski mantiq (50 dan hisoblash) uchta qadam bergan bo'lardi —
        ya'ni mijoz o'zi allaqachon to'lagan 14 ta bola uchun qayta
        pul to'lardi.
        """
        quote = pricing.quote(
            plan=PLAN,
            peak_children=71,
            covered_children=64,
            discount_percent=Decimal("15"),
            include_base=False,
        )
        assert quote.overage_steps == 1
        assert quote.overage_amount == Decimal("80000.00")
        assert quote.total_amount == Decimal("68000.00")  # 80 000 − 15 %

    def test_shrinking_below_the_committed_count_bills_nothing(self):
        """Bolalar kamaysa ham qaytarilmaydi, lekin qoʻshimcha ham olinmaydi."""
        quote = pricing.quote(plan=PLAN, peak_children=40, covered_children=64, include_base=False)
        assert quote.total_amount == Decimal("0.00")

    def test_covered_below_the_plan_floor_is_ignored(self):
        """
        Kelishilgan son plandagi 50 dan kam bo'lsa, pol baribir 50.

        Aks holda 20 bolaga "kelishgan" mijoz 21-boladan boshlab
        ortiqcha to'lardi — holbuki baza 50 tagacha qamrab oladi.
        """
        quote = pricing.quote(plan=PLAN, peak_children=55, covered_children=20)
        assert quote.overage_steps == 1  # 50 dan hisoblanadi, 20 dan emas
        assert quote.total_amount == Decimal("580000.00")

    def test_monthly_term_is_unchanged(self):
        """`covered_children` berilmasa, eski xatti-harakat aynan saqlanadi."""
        with_arg = pricing.quote(plan=PLAN, peak_children=80, covered_children=50)
        without = pricing.quote(plan=PLAN, peak_children=80)
        assert with_arg.total_amount == without.total_amount == Decimal("740000.00")


class TestFrontendAgrees:
    """
    Konsol taxmini backenddagi plan bilan bir xil raqamlarda turishi kerak.

    Vendor konsoli ro'yxatdagi o'nlab bog'chaning har biri uchun server
    so'rovini kutolmaydi, shuning uchun u formulani frontendda takrorlaydi
    (`frontend/src/lib/pricing.ts`). Takror bor joyda ajralish ham bor —
    auditda aynan shu bo'lgan: konsol ADR-12 dan oldingi 500 000 / +80 000
    ni ko'rsatib turgan edi. Bu test ikkalasini bog'lab qo'yadi.
    """

    def test_the_console_constants_match_the_seeded_plan(self, db):
        import re
        from pathlib import Path

        from django.conf import settings

        from apps.core.tenancy import platform_context
        from apps.subscriptions.services import current_plan

        source = (
            Path(settings.BASE_DIR).parent / "frontend" / "src" / "lib" / "pricing.ts"
        ).read_text()
        found = {
            key: int(value.replace("_", ""))
            for key, value in re.findall(r"(\w+):\s*([\d_]+),", source)
        }

        # AMALDAGI plan — eskisi tarixiy hisoblar uchun bazada qoladi
        # (ADR-12: 500 000 / +80 000 faqat 2026-09-14 gacha to'g'ri).
        with platform_context():
            plan = current_plan()
        assert found["basePrice"] == int(plan.base_price)
        assert found["includedChildren"] == plan.included_children
        assert found["overageStepChildren"] == plan.overage_step_children
        assert found["overageStepPrice"] == int(plan.overage_step_price)
