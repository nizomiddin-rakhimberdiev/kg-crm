"""
Demo ma'lumotini to'ldiradi — ko'rsatish va qo'lda sinash uchun.

Ma'lumot **servis qatlami orqali** yaratiladi, to'g'ridan-to'g'ri model
yozish bilan emas. Bu ataylab: shunda seed ham biznes qoidalaridan
o'tadi (ledger, balans, guruh sig'imi, stok qoldig'i) va natija haqiqiy
tizim holatiga aynan o'xshaydi. To'g'ridan-to'g'ri yozilgan demo esa
"chiroyli, lekin mumkin bo'lmagan" holat yaratardi — va aynan shunday
holatda qilingan demo keyin ishlab chiqarishda takrorlanmasdi.

**Bog'cha OCHILGAN kun** — oynaning boshi (`--months`). Undan oldin
na bola yoziladi, na xodim ishga olinadi: "olti oylik bog'cha"da ikki
yil oldin kelgan bola birinchi qarashdayoq yolg'on ko'rinadi. Shu
kuni ega boshlang'ich pul kiritadi (`owner_contribution`) — usiz
birinchi oyning oyligi va kommunali tushumdan oldin to'lanib, kassa
manfiyga ketardi (ADR-29).

Bog'chaning KATTALIGI hamma narsani belgilaydi: shtat guruhlar soniga
qarab o'sadi, kommunal va ombor xaridi bolalar soniga ko'paytiriladi.
Qat'iy raqamlar kichik bog'chada oylik fondini tushumdan katta qilib,
demo o'zini o'zi inkor qilardi.

Natija ichki ziddiyatsizligini `close_month` tekshiradi: oy faqat
tenglik "yashil" bo'lsa yopiladi, ya'ni yopilgan oylar soni —
raqamlar bir-biriga mos kelganining dalili.

Ishlatish::

    python manage.py seed_demo --email ranizomiddin@gmail.com
    python manage.py seed_demo --slug analiz --children 120 --months 6
    python manage.py seed_demo --slug ... --reset   # avval tozalaydi

⚠️ Mijozning HAQIQIY tashkilotiga ishlatilmaydi — bu bir marta sodir
bo'lgan va demo ma'lumoti mijozning ishi bilan aralashib qolgan.
Nishonni doim `--slug` bilan ANIQ ko'rsating; `--reset` tashkilotning
BARCHA operatsion ma'lumotini o'chiradi.
"""

from __future__ import annotations

import logging
import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.core.tenancy import organization_context, platform_context

logger = logging.getLogger(__name__)

# Aniq urug': har safar bir xil demo. Ko'rsatishda "kecha boshqacha edi"
# degan holat bo'lmasligi kerak.
SEED = 20260804

FAMILIYALAR = [
    "Valiyev",
    "Karimov",
    "Rahimov",
    "Yusupov",
    "Tursunov",
    "Ergashev",
    "Sobirov",
    "Nazarov",
    "Qodirov",
    "Ibragimov",
    "Xolmatov",
    "Sultonov",
    "Jo'rayev",
    "Mirzayev",
    "Abdullayev",
    "Toshmatov",
    "Sharipov",
    "Umarov",
]
O_ISMLAR = [
    "Ali",
    "Vali",
    "Sardor",
    "Jasur",
    "Bekzod",
    "Doston",
    "Aziz",
    "Otabek",
    "Shohruh",
    "Mirshod",
    "Javohir",
    "Islom",
    "Diyor",
    "Amir",
    "Sanjar",
]
Q_ISMLAR = [
    "Nodira",
    "Malika",
    "Zilola",
    "Sevara",
    "Dilnoza",
    "Madina",
    "Kamola",
    "Zarina",
    "Nigora",
    "Shahzoda",
    "Gulnoza",
    "Oysha",
    "Robiya",
    "Laylo",
]
ONA_ISMLAR = ["Nodira", "Dilfuza", "Zulfiya", "Gulnora", "Mavluda", "Shahnoza", "Nasiba"]
OTA_ISMLAR = ["Rustam", "Bahodir", "Farrux", "Ulug'bek", "Sanjar", "Alisher", "Nodir"]

# Guruh: nomi, yosh oralig'i, sig'imi.
#
# Jami sig'im bolalar sonidan KATTA bo'lishi kerak: bog'cha 100 %
# to'lgan holatda ishlamaydi — bitta bola chiqib ketsa joy ochiladi,
# navbat esa doim bor. Sig'im aniq bolalar soniga teng bo'lsa, har bir
# guruh kartasi "to'lgan" bo'lib qolardi va bo'sh joy ko'rsatkichi
# hech qachon ko'rinmasdi.
GURUHLAR = [
    ("Chaqaloq", 2, 3, 18),
    ("Quyoshcha", 3, 4, 22),
    ("Kamalak", 3, 4, 22),
    ("Yulduzcha", 4, 5, 22),
    ("Gulchehra", 4, 5, 20),
    ("Bilimdon", 5, 6, 22),
    ("Maktabgacha", 6, 7, 18),
]

TARIFLAR = [
    ("To'liq kun", Decimal("1500000")),
    ("Yarim kun", Decimal("950000")),
    ("Qisqartirilgan", Decimal("700000")),
]

LAVOZIMLAR = [
    ("Tarbiyachi", "Ta'lim", Decimal("4200000")),
    ("Tarbiyachi yordamchisi", "Ta'lim", Decimal("2800000")),
    ("Oshpaz", "Oshxona", Decimal("3500000")),
    ("Hamshira", "Tibbiyot", Decimal("3800000")),
    ("Farrosh", "Xo'jalik", Decimal("2400000")),
    ("Metodist", "Ta'lim", Decimal("5000000")),
]

MAHSULOTLAR = [
    ("Guruch", "Oziq-ovqat", "kg", Decimal("30"), Decimal("14000")),
    ("Kartoshka", "Oziq-ovqat", "kg", Decimal("40"), Decimal("6500")),
    ("Sabzi", "Oziq-ovqat", "kg", Decimal("20"), Decimal("5000")),
    ("Tuxum", "Oziq-ovqat", "pcs", Decimal("200"), Decimal("1400")),
    ("Sut", "Oziq-ovqat", "l", Decimal("50"), Decimal("12000")),
    ("Yuvish vositasi", "Xo'jalik", "l", Decimal("10"), Decimal("28000")),
    ("Qo'lqop", "Xo'jalik", "pack", Decimal("15"), Decimal("35000")),
    ("A4 qog'oz", "Kanselyariya", "pack", Decimal("10"), Decimal("55000")),
]

# Chiqim: toifa, izoh, 64 bolalik bog'cha uchun summa, qaysi hisobdan.
#
# To'lov usuli O'YLANGAN: kommunal va internet bankdan o'tkaziladi
# (shartnoma bo'yicha, hisob-raqamga), tozalash vositasi va mayda
# ta'mir esa naqd. Hammasini naqd qilish kassani bo'shatib yuborardi
# va "naqd kassa −2 mln" degan mumkin bo'lmagan holat chiqardi.
CHIQIMLAR = [
    ("Kommunal", "Elektr energiyasi", Decimal("2400000"), "bank"),
    ("Kommunal", "Suv va kanalizatsiya", Decimal("650000"), "bank"),
    ("Kommunal", "Gaz", Decimal("1100000"), "bank"),
    ("Xo'jalik", "Tozalash vositalari", Decimal("480000"), "cash"),
    ("Ta'mirlash", "Oshxona jihozi ta'miri", Decimal("1750000"), "cash"),
    ("Boshqa", "Internet va aloqa", Decimal("390000"), "bank"),
]

#: `CHIQIMLAR` va `LAVOZIMLAR` shuncha bolalik bog'cha uchun yozilgan.
BAZAVIY_BOLALAR = 64


# Oila bog'chani qayerdan eshitgan (Bosqich 14).
#
# Taqsimot O'YLANGAN: Toshkentdagi bog'cha uchun eng ko'p manba —
# Instagram va tanish tavsiyasi, keyin "yonidan o'tib ketayotib ko'rdim".
# Teng taqsimlangan tasodif "har bir kanal bir xil ishlaydi" degan
# yolg'on manzara berardi va marketing hisoboti ma'nosiz bo'lardi.
QAYERDAN = [
    ("instagram", 30),
    ("referral", 24),
    ("walk_by", 15),
    ("sibling", 10),
    ("telegram", 8),
    ("outdoor", 6),
    ("website", 4),
    ("other", 3),
]


def _month_start(value: date, back: int = 0) -> date:
    total = value.year * 12 + (value.month - 1) - back
    return date(total // 12, total % 12 + 1, 1)


class Command(BaseCommand):
    help = "Tashkilotni demo ma'lumoti bilan to'ldiradi (ko'rsatish uchun)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--email", help="Tashkilot kontakt emaili")
        parser.add_argument("--slug", help="Tashkilot slug'i — aniq nishon")
        parser.add_argument("--children", type=int, default=64, help="Bolalar soni")
        parser.add_argument("--months", type=int, default=4, help="Necha oylik tarix")
        parser.add_argument(
            "--reset", action="store_true", help="Avval mavjud ma'lumotni o'chiradi"
        )

    def handle(self, *args: Any, **options: Any) -> None:
        random.seed(SEED)

        organization = self._resolve_organization(options)
        self.stdout.write(f"Tashkilot: {organization.name} ({organization.slug})")

        with organization_context(organization.id):
            if options["reset"]:
                self._reset(organization)
            self._seed(organization, options["children"], options["months"])

    # --- Nishonni aniqlash ---

    def _resolve_organization(self, options: dict[str, Any]) -> Any:
        """
        Qaysi tashkilot to'ldirilishini ANIQ aniqlaydi.

        Email tashkilotlar bo'ylab unikal EMAS (u faqat tashkilot ichida
        unikal) — bitta odam bir nechta bog'cha ochishi mumkin. Shu sababli
        email bo'yicha "birinchisini olish" jimgina noto'g'ri tashkilotni
        to'ldirib qo'yishi mumkin edi. Endi bir nechta moslik topilsa,
        buyruq ishlamaydi va `--slug` so'raydi.
        """
        from apps.organizations.models import Organization

        email, slug = options.get("email"), options.get("slug")
        if not email and not slug:
            raise CommandError("`--email` yoki `--slug` ko'rsating.")

        with platform_context():
            if slug:
                organization = Organization.objects.filter(slug=slug).first()
                if organization is None:
                    raise CommandError(f"'{slug}' slug'i bilan tashkilot topilmadi.")
                return organization

            matches = list(Organization.objects.filter(contact_email__iexact=email))

        if not matches:
            raise CommandError(f"'{email}' bilan tashkilot topilmadi.")
        if len(matches) > 1:
            options_text = "\n".join(f"  --slug {o.slug}   ({o.name})" for o in matches)
            raise CommandError(
                f"'{email}' bilan {len(matches)} ta tashkilot bor. Qaysi biri kerakligini "
                f"aniq ko'rsating:\n{options_text}"
            )
        return matches[0]

    # --- Tozalash ---

    def _reset(self, organization: Any) -> None:
        """
        Operatsion ma'lumotni o'chiradi — nishon va tartib
        `reset_organization_data` dagi BIR XIL ro'yxatdan olinadi
        (`RESET_ORDER` = `PURGE_ORDER` minus `KEEP`), ya'ni tashkilot,
        egasi, filial, obuna, qoplar va sozlamalar qoladi.

        Avval bu yerda o'z qisqa ro'yxati bor edi va u asta orqada
        qoldi: `payment_allocation` unga hech qachon qo'shilmadi, va
        jonli bazada bitta taqsimot butun tozalashni `RestrictedError`
        bilan yiqitdi. Ikkita ro'yxat yuritilsa, ulardan biri doim
        eskiradi — shuning uchun endi bittasi bor.
        """
        from apps.platform.purge import DERIVED_PURGE, _model, allow_frozen_deletes

        from .reset_organization_data import KEEP, RESET_ORDER

        allow_frozen_deletes()
        for path, lookup in DERIVED_PURGE.items():
            if path in KEEP:
                continue
            self._wipe(_model(path), **{lookup: organization.id})
        for path in RESET_ORDER:
            self._wipe(_model(path), organization_id=organization.id)
        self.stdout.write(self.style.WARNING("  eski ma'lumot o'chirildi"))

    @staticmethod
    def _wipe(model: Any, **lookup: Any) -> None:
        manager = getattr(model, "all_objects", None) or model._default_manager
        manager.filter(**lookup).delete()

    # --- To'ldirish ---

    @transaction.atomic
    def _seed(self, organization: Any, child_count: int, months: int) -> None:
        branch = self._branch(organization)
        owner = self._owner(organization)

        # Bog'cha OCHILGAN kun — oynaning boshi. Hamma narsa shunga
        # bog'lanadi: undan oldin yozilgan bola ham, ishga olingan
        # xodim ham bo'lishi mumkin emas, aks holda "6 oylik bog'cha"
        # degan manzara birinchi qarashdayoq buziladi.
        opening = _month_start(timezone.localdate(), months - 1)

        groups = self._groups(organization, branch)
        tariffs = self._tariffs(organization, branch)
        self._opening_capital(branch, owner, opening, child_count)
        children = self._children(organization, branch, groups, tariffs, child_count, opening)
        employees = self._staff(organization, branch, opening, child_count)
        self._benefits(children, employees, owner, opening)
        self._finance(children, months, owner)
        self._claims(children, owner, months)
        self._attendance(organization, branch, groups, owner, months)
        self._staff_attendance(branch, owner, months)
        self._payroll(organization, branch, owner, months, employees)
        self._inventory(organization, branch, owner, child_count)
        self._expenses(organization, branch, owner, months, child_count)
        self._deposit_cash(branch, owner, months)
        self._owner_draws(branch, owner, months)
        self._close_months(branch, owner, months)
        self._cash_day(branch, owner)
        self._notifications(organization)

        self._summary(organization)

    def _branch(self, organization: Any) -> Any:
        from apps.branches.models import Branch

        branch = Branch.objects.filter(organization=organization).first()
        if branch is None:
            branch = Branch.objects.create(
                organization=organization, name=organization.name, code="MAIN"
            )
        return branch

    def _owner(self, organization: Any) -> Any:
        from apps.accounts.models import User

        return User.objects.filter(organization=organization).order_by("created_at").first()

    def _groups(self, organization: Any, branch: Any) -> list[Any]:
        from apps.children.models import Group

        created = []
        for name, age_min, age_max, capacity in GURUHLAR:
            group, _ = Group.objects.get_or_create(
                organization=organization,
                branch=branch,
                name=name,
                defaults={"age_min": age_min, "age_max": age_max, "capacity": capacity},
            )
            created.append(group)
        self.stdout.write(f"  guruhlar: {len(created)}")
        return created

    def _tariffs(self, organization: Any, branch: Any) -> list[Any]:
        from apps.finance.models import TariffPlan

        created = []
        for name, amount in TARIFLAR:
            tariff, _ = TariffPlan.objects.get_or_create(
                organization=organization,
                branch=branch,
                name=name,
                defaults={"amount": amount},
            )
            created.append(tariff)
        self.stdout.write(f"  tariflar: {len(created)}")
        return created

    def _children(
        self,
        organization: Any,
        branch: Any,
        groups: list[Any],
        tariffs: list[Any],
        count: int,
        opening: date,
    ) -> list[Any]:
        from apps.children.models import Child, Guardian
        from apps.children.services import attach_guardian, enroll_child

        today = timezone.localdate()
        children = []

        # Guruh bandligi XOTIRADA hisoblanadi.
        #
        # `group.enrolled_count` — bazadagi kesh ustuni, va `enroll_child`
        # uni bazada yangilaydi. Lekin qo'limizdagi Python obyekti
        # yangilanmaydi: u seed boshida bir marta o'qilgan. Shu sababli
        # sikl to'lib bo'lgan guruhni ham "bo'sh" deb ko'rib, unga yana
        # yozishga urinardi va `enroll_child` "guruh to'lgan" deb
        # yiqilardi. Kam bolada bu yuzaga chiqmasdi — sig'im hech qachon
        # to'lmasdi — va aynan shuning uchun uzoq vaqt sezilmay qoldi.
        capacity_left = {group.id: group.capacity - group.enrolled_count for group in groups}

        for index in range(count):
            is_boy = random.random() < 0.52
            last_name = random.choice(FAMILIYALAR)
            first_name = random.choice(O_ISMLAR if is_boy else Q_ISMLAR)
            age_years = random.randint(2, 6)
            birth = today - timedelta(days=age_years * 365 + random.randint(0, 300))

            # Qabul sanasi OCHILISH kunidan keyin.
            #
            # Ilgari u 30–700 kun orqaga tasodifiy qo'yilardi va olti
            # oylik bog'chada ikki yil oldin yozilgan bola chiqardi.
            # Haqiqiy manzara boshqacha: ko'pchilik ochilishda keladi,
            # qolgani oylar davomida qo'shiladi — va aynan shu
            # taqsimot birinchi oy proratsiyasini ham ko'rsatadi.
            if random.random() < 0.62:
                enrolled = opening + timedelta(days=random.randint(0, 6))
            else:
                # Bir oylik oynada oraliq 7 kundan qisqa boʻlishi
                # mumkin — oʻshanda hammasi ochilish kuniga tushadi.
                span = max((today - opening).days - 10, 0)
                enrolled = opening + timedelta(days=random.randint(min(7, span), span))

            source, note = self._heard_from()
            child = Child.objects.create(
                organization=organization,
                branch=branch,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=birth,
                gender="male" if is_boy else "female",
                # Tarif taqsimoti realistik: ko'pchilik to'liq kunda.
                tariff=random.choices(tariffs, weights=[70, 22, 8])[0],
                enrolled_on=enrolled,
                # Qayerdan eshitgan (Bosqich 14) — yangi bolada bu maydon
                # majburiy, ya'ni ishlab turgan bog'chada u to'la bo'ladi.
                heard_from=source,
                heard_from_note=note,
                # Shartnoma raqami: bog'chalar uni qo'lda, ketma-ket yuritadi.
                contract_number=f"SH-{enrolled.year}-{index + 1:04d}",
            )

            guardian = Guardian.objects.create(
                organization=organization,
                branch=branch,
                first_name=random.choice(ONA_ISMLAR if random.random() < 0.75 else OTA_ISMLAR),
                last_name=last_name + ("a" if random.random() < 0.75 else ""),
                # Telefon indeksdan: `uq_guardian_branch_phone` — bir filialda
                # ikki vasiy bir raqamda bo'lolmaydi, tasodifiy raqam esa
                # 100+ bolada to'qnashib seed'ni yiqitardi.
                phone=f"+9989{index % 10}{1000000 + (index * 7919) % 8999999:07d}",
            )
            attach_guardian(
                child=child,
                guardian=guardian,
                relation="mother" if guardian.first_name in ONA_ISMLAR else "father",
                is_primary=True,
            )

            # Guruhga YOSHIGA qarab, teng taqsimlab.
            #
            # Ilgari faqat yosh yaqinligi hisobga olinardi va sikl
            # birinchi mos guruhni oxirigacha to'ldirib, keyingisiga
            # o'tardi. Natijada bir xil yoshdagi ikki guruhdan biri
            # 22/22, ikkinchisi 5/20 bo'lib qolardi — bog'cha bolalarni
            # bunday taqsimlamaydi. Endi mos guruhlar ichidan eng
            # BO'SHI tanlanadi.
            for group in sorted(
                groups,
                key=lambda g: (abs((g.age_min or 4) - age_years), -capacity_left[g.id]),
            ):
                if capacity_left[group.id] > 0:
                    enroll_child(child=child, group=group)
                    capacity_left[group.id] -= 1
                    break
            else:
                # Guruhsiz bola davomatga ham, guruh hisobotiga ham
                # tushmaydi — ya'ni demo jimgina chala bo'lardi.
                raise CommandError(
                    f"Guruhlar sig'imi yetmadi: {count} bola so'ralgan, jami sig'im "
                    f"{sum(g.capacity for g in groups)}. `GURUHLAR` ro'yxatini kengaytiring."
                )

            children.append(child)

        self.stdout.write(f"  bolalar: {len(children)} (vasiylari bilan)")
        return children

    @staticmethod
    def _heard_from() -> tuple[str, str]:
        """Manba va — faqat «boshqa» uchun — aniqlashtiruvchi izoh."""
        codes = [code for code, _ in QAYERDAN]
        weights = [weight for _, weight in QAYERDAN]
        code = random.choices(codes, weights=weights)[0]
        if code != "other":
            return code, ""
        return code, random.choice(
            ["Poliklinika doskasida", "Mahalla yig'ilishida", "Ish joyidagi e'londan"]
        )

    def _opening_capital(self, branch: Any, owner: Any, opening: date, child_count: int) -> None:
        """
        Egasining boshlang'ich kiritmasi — bog'cha ochilgan kuni.

        Usiz demo mumkin bo'lmagan holatga tushardi: birinchi oyning
        oyligi va kommunali tushumdan OLDIN to'lanadi, ya'ni kassa
        manfiyga ketardi va `ADR-29` (qopda yo'q pul chiqmaydi) ni
        buzardi. Haqiqiy bog'cha ham aynan shunday boshlanadi — ega
        ishga tushirish uchun pul qo'yadi, va bu pul "boshqa daromad"
        emas, `owner_contribution` hujjati.

        Summa O'YLANGAN: ikki oylik oylik fondi va kommunal uchun
        yetadigan zaxira — ko'proq qo'yish kassani sun'iy "boy"
        qilardi, kamrog'i esa birinchi oyni o'tkaza olmasdi.
        """
        from apps.cash.services import account_for_method, record_operation

        bank = account_for_method(branch=branch, method="bank_transfer")
        till = account_for_method(branch=branch, method="cash")
        scale = max(Decimal("0.35"), Decimal(child_count) / Decimal(BAZAVIY_BOLALAR))
        for account, amount, note in (
            (bank, Decimal("45000000") * scale, "Ishga tushirish uchun — bank hisobiga"),
            (till, Decimal("6000000") * scale, "Kassaga aylanma pul"),
        ):
            try:
                record_operation(
                    kind="owner_contribution",
                    account=account,
                    amount=amount.quantize(Decimal("1")),
                    occurred_on=opening,
                    reason=note,
                    created_by=owner,
                )
            except Exception as exc:
                logger.warning("Boshlang'ich kiritma yozilmadi: %s", exc)
        self.stdout.write("  egadan boshlang'ich kiritma: 2 ta hujjat")

    def _benefits(
        self, children: list[Any], employees: list[Any], owner: Any, opening: date
    ) -> None:
        """
        Imtiyozlar — bir nechta oilada, SABABI bilan.

        Aka-uka chegirmasi avtomatik (umumiy vasiy bo'yicha), shuning
        uchun bu yerda faqat QO'LDA beriladiganlari: xodim farzandi va
        kam ta'minlangan oila. Ularsiz "Imtiyozlar" hisoboti bo'm-bo'sh
        turardi, holbuki har bir bog'chada bunday bolalar bor.

        Qiymat yozuvda EMAS, sozlamada (`benefits.*`) — shuning uchun
        `value` nol: tur o'zi qancha ekanini aytadi (Bosqich 12.2).
        """
        from apps.finance.models import BenefitKind, Discount, DiscountType

        if not children:
            return
        count = max(2, len(children) * 6 // 100)
        chosen = random.sample(children, min(count, len(children)))
        created = 0
        for position, child in enumerate(chosen):
            staff_child = position < max(1, len(chosen) // 2) and employees
            kind = BenefitKind.STAFF_CHILD if staff_child else BenefitKind.LOW_INCOME
            reason = (
                f"{random.choice(employees).full_name} — bog'cha xodimi"
                if staff_child
                else "Mahalla ma'lumotnomasi asosida"
            )
            Discount.objects.create(
                organization=child.organization,
                branch=child.branch,
                child=child,
                kind=kind,
                discount_type=DiscountType.PERCENT,
                value=Decimal("0"),
                reason=reason,
                valid_from=max(opening, child.enrolled_on or opening),
                created_by=owner,
            )
            created += 1
        self.stdout.write(f"  imtiyozlar: {created}")

    def _claims(self, children: list[Any], owner: Any, months: int) -> None:
        """
        Kelmagan kunlar uchun qayta hisob — TASDIQLANGAN da'volar.

        Pul faqat hujjatdan harakatlanadi (ADR-19): davomat jadvalidagi
        "kelmadi" o'z-o'zidan hech narsani qaytarmaydi. Shuning uchun
        demoda ham da'vo yoziladi va tasdiqlanadi — "Qayta hisob" tabi
        aynan shu oqimni ko'rsatishi kerak.

        Oraliqlar o'tgan oylarda: yopilgan oyning fakturasi qayta
        hisoblanadi va bu hisobotda ko'rinadi.
        """
        from apps.attendance.services_absence import approve_claim, create_claim

        if not children or months < 2:
            return
        today = timezone.localdate()
        made = 0
        for child in random.sample(children, min(6, len(children))):
            back = random.randint(1, months - 1)
            period = _month_start(today, back)
            start = period + timedelta(days=random.randint(3, 12))
            # Dam olish kunidan boshlanmasin — ish kuni sanaladi.
            while start.weekday() >= 5:
                start += timedelta(days=1)
            end = start + timedelta(days=random.randint(2, 6))
            medical = random.random() < 0.7
            try:
                claim = create_claim(
                    child=child,
                    kind="medical" if medical else "parental",
                    date_from=start,
                    date_to=end,
                    document_no=f"M-{random.randint(1000, 9999)}" if medical else "",
                    note="Shifokor maʼlumotnomasi" if medical else "Ota-ona arizasi",
                    created_by=owner,
                )
                approve_claim(claim=claim, approved_by=owner, note="Hujjat tekshirildi")
                made += 1
            except Exception as exc:
                logger.warning("Daʼvo yozilmadi (%s): %s", child.full_name, exc)
                continue
        self.stdout.write(f"  qayta hisob daʼvolari: {made}")

    def _staff_attendance(self, branch: Any, owner: Any, months: int) -> None:
        """
        Xodimlar tabeli — bolalar davomati bilan BIR XIL oynada.

        Usiz "Xodimlar → Davomat" tabi olti oylik bog'chada bo'm-bo'sh
        turardi, oylik esa to'liq ish kuni bo'yicha hisoblanardi — ya'ni
        ikki ekran bir-biriga zid ma'lumot ko'rsatardi.
        """
        from apps.attendance.services_staff import mark_bulk as mark_staff
        from apps.hr.models import Employee

        today = timezone.localdate()
        staff = list(Employee.objects.filter(branch=branch, is_active=True))
        if not staff:
            return

        cursor = _month_start(today, months - 1)
        marked = 0
        while cursor <= today:
            if cursor.weekday() < 5:
                rows = []
                for employee in staff:
                    if employee.hire_date and employee.hire_date > cursor:
                        continue
                    roll = random.random()
                    if roll < 0.93:
                        status = "present"
                    elif roll < 0.97:
                        status = "sick"
                    else:
                        status = "leave"
                    rows.append({"employee_id": employee.id, "status": status, "note": ""})
                if rows:
                    try:
                        mark_staff(
                            organization=branch.organization,
                            branch_id=branch.id,
                            attendance_date=cursor,
                            records=rows,
                            recorded_by=owner,
                        )
                        marked += len(rows)
                    except Exception as exc:
                        logger.warning("Xodim davomati yozilmadi (%s): %s", cursor, exc)
            cursor += timedelta(days=1)
        self.stdout.write(f"  xodimlar tabeli: {marked} yozuv")

    def _deposit_cash(self, branch: Any, owner: Any, months: int) -> None:
        """
        Naqd pulni bankka topshirish — har oy, aylanma puldan tashqarisi.

        Usiz kassada bir yarim yuz million naqd yigʻilib qolardi: tushumning
        qariyb yarmi naqd keladi, kassadan esa faqat mayda chiqim va
        oylikning naqd qismi chiqadi. Haqiqiy bogʻcha pulni bankka
        topshiradi va kassada faqat kunlik aylanma qoldiradi — bu ham
        xavfsizlik, ham hisob masalasi.
        """
        from django.db.models import Sum

        from apps.cash.models import CashMovement, MovementDirection
        from apps.cash.selectors import account_balance
        from apps.cash.services import account_for_method, transfer

        today = timezone.localdate()
        bank = account_for_method(branch=branch, method="bank_transfer")
        till = account_for_method(branch=branch, method="cash")
        # Kassada qoladigan aylanma — bir kunlik mayda chiqim uchun.
        float_amount = Decimal("4000000")

        made = 0
        for back in range(months - 1, -1, -1):
            period = _month_start(today, back)
            # Oyning oxirgi kuni; joriy oyda — bugun.
            day = min(_month_start(today, back - 1) - timedelta(days=1), today) if back else today
            # Shu OYDA kassaga tushgan va undan chiqqan pul.
            #
            # Umumiy qoldiqdan emas: aks holda butun olti oylik naqd
            # bitta kunda topshirilgandek ko'rinardi va kassa jurnali
            # bitta ulkan qatordan iborat bo'lib qolardi.
            month_end = _month_start(today, back - 1) if back else today + timedelta(days=1)
            flow = CashMovement.objects.filter(
                cash_account=till, occurred_at__date__gte=period, occurred_at__date__lt=month_end
            )
            came_in = flow.filter(direction=MovementDirection.IN).aggregate(total=Sum("amount"))[
                "total"
            ] or Decimal("0")
            went_out = flow.filter(direction=MovementDirection.OUT).aggregate(total=Sum("amount"))[
                "total"
            ] or Decimal("0")
            surplus = came_in - went_out - float_amount
            # Qolgan haqiqiy qoldiqdan ko'p topshirib bo'lmaydi (ADR-29).
            amount = min(surplus, account_balance(account_id=till.id) - float_amount)
            if amount <= 0:
                continue
            # Topshiriladigan summa yumaloq: bankka "aniq 7 431 500" emas.
            amount = (amount / Decimal("100000")).to_integral_value(
                rounding="ROUND_FLOOR"
            ) * Decimal("100000")
            if amount <= 0:
                continue
            try:
                transfer(
                    source=till,
                    target=bank,
                    amount=amount,
                    description="Naqd tushum bankka topshirildi",
                    occurred_at=timezone.make_aware(datetime.combine(day, time(hour=17))),
                    created_by=owner,
                )
                made += 1
            except Exception as exc:
                logger.warning("Inkassatsiya yozilmadi (%s): %s", period, exc)
                continue
        self.stdout.write(f"  bankka topshirish: {made} marta")

    def _owner_draws(self, branch: Any, owner: Any, months: int) -> None:
        """
        Ega har oy foydadan oladi — dividend sifatida, solig'i bilan.

        Usiz bank hisobida olti oyda 190 million yigʻilib qolardi:
        bogʻcha daromad qiladi, lekin egasi hech narsa olmaydi. Bunday
        bogʻcha yoʻq, va "qancha pul olsa boʻladi" ekrani ham maʼnosiz
        boʻlib qolardi — unda taqqoslaydigan tarix yoʻq.

        Summa O'YLANGAN: oy yopilgandan keyin, bankdagi qoldiqning
        taxminan uchdan biri, lekin zaxira (ikki oylik oylik fondi)
        tegilmaydi. Joriy oydan OLINMAYDI — u hali yigʻilmoqda.
        """
        from apps.cash.selectors import account_balance
        from apps.cash.services import account_for_method, record_operation

        today = timezone.localdate()
        bank = account_for_method(branch=branch, method="bank_transfer")
        reserve = Decimal("40000000")
        made = 0
        for back in range(months - 1, 0, -1):
            period = _month_start(today, back)
            day = _month_start(today, back - 1) - timedelta(days=1)
            spare = account_balance(account_id=bank.id) - reserve
            if spare <= 0:
                continue
            amount = (spare / Decimal("3") / Decimal("1000000")).to_integral_value(
                rounding="ROUND_FLOOR"
            ) * Decimal("1000000")
            if amount <= 0:
                continue
            try:
                record_operation(
                    kind="owner_draw",
                    subtype="dividend",
                    account=bank,
                    amount=amount,
                    occurred_on=day,
                    reason=f"{period.year}-{period.month:02d} oyi foydasidan",
                    created_by=owner,
                )
                made += 1
            except Exception as exc:
                logger.warning("Egaga toʻlov yozilmadi (%s): %s", period, exc)
                continue
        self.stdout.write(f"  egaga toʻlov: {made} marta")

    def _close_months(self, branch: Any, owner: Any, months: int) -> None:
        """
        Tugagan oylarni yopadi — ishlab turgan bog'chada shunday bo'ladi.

        Yopish faqat tenglik "yashil" bo'lsa o'tadi, ya'ni bu seed
        ma'lumotining O'ZINI tekshiradi: raqamlar bir-biriga mos
        kelmasa, oy yopilmaydi va buni ogohlantirish aytadi.
        """
        from apps.finance.services import close_month

        today = timezone.localdate()
        closed = 0
        for back in range(months - 1, 0, -1):
            period = _month_start(today, back)
            try:
                close_month(branch=branch, year=period.year, month=period.month, closed_by=owner)
                closed += 1
            except Exception as exc:
                logger.warning("Oy yopilmadi (%s): %s", period, exc)
                continue
        self.stdout.write(f"  yopilgan oylar: {closed}")

    def _cash_day(self, branch: Any, owner: Any) -> None:
        """
        Bugungi kunni yopish — kupyuralar bo'yicha sanoq bilan.

        `close_day` ataylab faqat BUGUNGI kunni yopadi, shuning uchun
        tarixiy sanoqlar yozilmaydi: ularni model darajasida yozish
        servis qatlamini chetlab o'tish bo'lardi. Bitta haqiqiy sanoq
        esa "Nazorat" tekshiruvini jonlantiradi va kupyura jadvali
        qanday ko'rinishini ko'rsatadi.
        """
        from apps.cash.selectors import account_balance
        from apps.cash.services import cash_pot, close_day

        try:
            pot = cash_pot(branch=branch)
        except Exception as exc:
            logger.warning("Naqd kassa topilmadi: %s", exc)
            return

        balance = account_balance(account_id=pot.id)
        if balance <= 0:
            self.stdout.write("  kassa sanogʻi: kassa boʻsh, oʻtkazib yuborildi")
            return

        # Kupyuralarga ajratamiz — qoldiq tangagacha emas, eng yirikdan.
        left = int(balance)
        notes: dict[str, int] = {}
        for note in (200000, 100000, 50000, 20000, 10000, 5000, 1000):
            if left < note:
                continue
            count = left // note
            notes[str(note)] = count
            left -= note * count
        if left:
            # Qolgani kupyuraga bo'linmadi — sanoqni summa bilan yopamiz.
            notes = {}

        try:
            close_day(
                account=pot,
                counted=balance if not notes else None,
                denominations=notes or None,
                reason="Kun yakuni",
                created_by=owner,
            )
            self.stdout.write(f"  kassa sanogʻi: {balance:,.0f} soʻm")
        except Exception as exc:
            logger.warning("Kun yopilmadi: %s", exc)

    def _finance(self, children: list[Any], months: int, owner: Any) -> None:
        """
        Hisob-faktura va to'lovlar — servis orqali, ya'ni ledger va
        balans ham to'g'ri to'ladi.

        Qarzdorlik ataylab **bir necha oilada to'plangan**, hamma bo'ylab
        sochilgan emas: haqiqiy bog'chada ham shunday — aksariyat o'z
        vaqtida to'laydi, bir nechtasi surunkali qarzdor. Tasodifiy
        sochilgan qarz "hamma biroz qarzdor" degan ishonarsiz manzara
        berardi.

        Qarz **CHEGARALANGAN**: qarzdor oila faqat eng so'nggi yopiq oyda
        to'lamasligi mumkin, undan oldingilari yopilgan. Avval har oy
        mustaqil ehtimol bilan hisoblanardi va 6 oylik oynada bu ba'zi
        bolalarga 4-5 oy ketma-ket to'lovsiz qolish imkonini berardi —
        natijada demoda 8 mln so'mlik, ya'ni deyarli yarim yillik qarz
        paydo bo'ldi. Haqiqiy bog'chada bunday oila allaqachon
        ogohlantirilgan yoki chiqib ketgan bo'lardi, ya'ni raqam
        ishonchsiz ko'rinardi.
        """
        from apps.finance.models import PaymentMethod
        from apps.finance.services import issue_invoice, record_payment

        today = timezone.localdate()
        invoices = 0
        payments = 0

        # Surunkali qarzdorlar — ~9 %. Ular bir necha oy to'lamaydi.
        chronic = set(random.sample(range(len(children)), max(1, len(children) * 9 // 100)))

        for back in range(months - 1, -1, -1):
            period = _month_start(today, back)
            is_current = back == 0
            for index, child in enumerate(children):
                if child.tariff is None:
                    continue
                try:
                    invoice = issue_invoice(
                        child=child,
                        period_year=period.year,
                        period_month=period.month,
                        created_by=owner,
                    )
                except Exception as exc:
                    # Jimgina o'tkazib yubormaymiz: seed kam ma'lumot
                    # yaratsa, sabab ko'rinib tursin.
                    logger.warning("Faktura yozilmadi (%s): %s", child.full_name, exc)
                    continue
                invoices += 1

                # `back == 1` — eng so'nggi YOPIQ oy. Qarzdor oilaning
                # qarzi faqat shu yerdan boshlanadi, ya'ni eng katta
                # qarz = bitta yopiq oy + hali yig'ilayotgan joriy oy.
                if index in chronic and not is_current and back == 1:
                    if random.random() >= 0.3:
                        continue
                    share = Decimal(str(round(random.uniform(0.2, 0.6), 2)))
                else:
                    roll = random.random()
                    # Eski oylar deyarli yopilgan; joriy oy hali yig'ilmoqda.
                    #
                    # Joriy oyda ehtimol OY KUNIGA bog'liq: oyning 5-kuni
                    # kam oila to'lagan bo'ladi, 25-kuni esa deyarli
                    # hammasi. Qat'iy 70 % demo qachon ishga tushirilishiga
                    # qarab goh juda yaxshi, goh juda yomon manzara berardi.
                    if is_current:
                        progress = min(1.0, today.day / 25)
                        full_chance = 0.25 + 0.65 * progress
                    else:
                        full_chance = 0.96
                    if roll < full_chance:
                        share = Decimal("1")
                    elif roll < full_chance + 0.08:
                        share = Decimal(str(round(random.uniform(0.4, 0.8), 2)))
                    else:
                        continue

                amount = (invoice.amount_due * share).quantize(Decimal("1"))
                if amount <= 0:
                    continue

                # To'lov sanasi HECH QACHON kelajakda bo'lmaydi.
                #
                # Birinchi urinishda joriy oy uchun tasodifiy kun
                # olingan edi va 48 ta to'lov kelajakka tushdi —
                # dashboard ularni (to'g'ri qilib) hisobga olmadi va
                # "shu oy tushum" haqiqatdan uch baravar past ko'rindi.
                last_day = today.day if is_current else 28
                # Qabul oyida to'lov qabuldan OLDIN bo'lmaydi (A6, audit
                # 2026-11-12): bog'cha bunday to'lovni rad etadi.
                first_day = 1
                arrived = child.enrolled_on
                if arrived and (arrived.year, arrived.month) == (period.year, period.month):
                    first_day = arrived.day
                last_day = max(last_day, first_day)
                paid_at = timezone.make_aware(
                    datetime(
                        period.year,
                        period.month,
                        random.randint(first_day, max(first_day, last_day)),
                        random.randint(9, 17),
                        random.randint(0, 59),
                    )
                )
                record_payment(
                    child=child,
                    amount=amount,
                    # `bank_transfer` — `PaymentMethod` dagi AYNAN shu kod. Ilgari
                    # bu yerda "transfer" yozilardi: `TextChoices` bazada
                    # tekshirilmaydi, shuning uchun noto'g'ri qiymat jimgina
                    # yozilib, ro'yxatda yorliqsiz "transfer" bo'lib ko'rinardi.
                    method=random.choices(
                        [PaymentMethod.CASH, PaymentMethod.TERMINAL, PaymentMethod.BANK_TRANSFER],
                        weights=[45, 40, 15],
                    )[0],
                    # Faktura KO'RSATILMAYDI: pul eng eski qarzga tushadi
                    # (13-invariant, FIFO). Avval har to'lov o'z oyiga
                    # mixlanardi va demo'da yangi oy yopilib, eskisi ochiq
                    # qolardi — haqiqiy kassada bunday bo'lmaydi (G5).
                    paid_at=paid_at,
                    received_by=owner,
                    # Demo tarixi oylar orqaga ketadi (Bosqich 12.4 qoidalari).
                    backdate_reason="Demo maʼlumot",
                )
                payments += 1

        self.stdout.write(f"  hisob-fakturalar: {invoices}, to'lovlar: {payments}")

    def _attendance(
        self, organization: Any, branch: Any, groups: list[Any], owner: Any, months: int
    ) -> None:
        """
        Moliya bilan BIR XIL oynadagi ish kunlari davomati.

        Avval qat'iy 20 kun edi va bu hisobotlarda yarim manzara
        berardi: "oylik davomat" grafigi 6 oylik hisob-faktura yonida
        bitta ustundan iborat bo'lib chiqardi. Oyna endi `--months`
        bilan bir xil.
        """
        from apps.attendance.services import mark_bulk
        from apps.children.models import Enrollment, EnrollmentState

        today = timezone.localdate()
        days: list[date] = []
        cursor = _month_start(today, months - 1)
        while cursor <= today:
            if cursor.weekday() < 5:  # dam olish kunlarisiz
                days.append(cursor)
            cursor += timedelta(days=1)

        marked = 0
        for group in groups:
            member_ids = list(
                Enrollment.objects.filter(
                    group=group, status=EnrollmentState.ACTIVE, end_date__isnull=True
                ).values_list("child_id", flat=True)
            )
            if not member_ids:
                continue
            for day in days:
                records = []
                for child_id in member_ids:
                    roll = random.random()
                    if roll < 0.90:
                        status = "present"
                    elif roll < 0.96:
                        status = "absent"
                    else:
                        status = "excused"
                    records.append({"child_id": child_id, "status": status})
                try:
                    mark_bulk(
                        organization=organization,
                        branch=branch,
                        group=group,
                        attendance_date=day,
                        records=records,
                        recorded_by=owner,
                        # O'tgan kunni belgilash SABAB talab qiladi
                        # (tahrirlash oynasi). Sababsiz har bir o'tgan kun
                        # jimgina rad etilib, faqat ogohlantirish qolardi —
                        # demo davomati bitta kundan iborat bo'lib chiqardi.
                        reason="Demo maʼlumoti",
                    )
                    marked += len(records)
                except Exception as exc:
                    logger.warning("Davomat yozilmadi (%s, %s): %s", group.name, day, exc)
                    continue

        self.stdout.write(f"  davomat yozuvlari: {marked}")

    @staticmethod
    def _headcount(title: str, child_count: int) -> int:
        """
        Lavozim bo'yicha shtat — guruhlar soniga bog'langan.

        Bir guruhga bir tarbiyachi, har ikki guruhga bir yordamchi.
        Oshpaz va farrosh — har 40 bolaga bittadan. Hamshira 25
        boladan, metodist esa 40 boladan boshlab paydo bo'ladi:
        kichik bog'chada bunday shtat birligi bo'lmaydi.
        """
        groups = max(1, -(-child_count // 18))  # 18 — guruhning o'rtacha sig'imi
        if title == "Tarbiyachi":
            return groups
        if "yordamchisi" in title:
            return max(1, groups // 2)
        if title in ("Oshpaz", "Farrosh"):
            return max(1, child_count // 40)
        if title == "Hamshira":
            return 1 if child_count >= 25 else 0
        if title == "Metodist":
            return 1 if child_count >= 40 else 0
        return 1

    def _staff(self, organization: Any, branch: Any, opening: date, child_count: int) -> list[Any]:
        from apps.hr.models import Employee, Position

        today = timezone.localdate()
        employees = []
        for title, department, salary in LAVOZIMLAR:
            position, _ = Position.objects.get_or_create(
                organization=organization,
                branch=branch,
                title=title,
                defaults={"department": department},
            )
            # Jamoa BOLALAR SONIGA qarab.
            #
            # Ilgari u qat'iy edi: 12 bolalik bog'chada ham 4 tarbiyachi,
            # metodist va hamshira. Natijada oylik fondi tushumdan katta
            # chiqib, "bankda pul yetmaydi" deb oylik hisoblanmasdi —
            # ya'ni demo o'zini o'zi inkor qilardi. Haqiqiy bog'chada
            # shtat guruhlar soniga qarab o'sadi.
            headcount = self._headcount(title, child_count)
            if headcount == 0:
                continue
            for _ in range(headcount):
                employees.append(
                    Employee.objects.create(
                        organization=organization,
                        branch=branch,
                        first_name=random.choice(ONA_ISMLAR + OTA_ISMLAR),
                        last_name=random.choice(FAMILIYALAR),
                        phone=f"+9989{random.randint(0, 9)}{random.randint(1000000, 9999999)}",
                        position=position,
                        # Ishga olingan kun ham OCHILISHDAN keyin: ilgari u
                        # 120–1500 kun orqaga ketardi va olti oylik
                        # bog'chada to'rt yil ishlagan xodim chiqardi.
                        # Jamoaning ko'pi ochilishda yig'iladi, bir-ikkitasi
                        # keyin qo'shiladi.
                        hire_date=(
                            opening + timedelta(days=random.randint(0, 3))
                            if random.random() < 0.8
                            else opening
                            + timedelta(
                                days=random.randint(20, max(21, (today - opening).days - 5))
                            )
                        ),
                        base_salary=salary + Decimal(random.randint(-2, 4) * 100000),
                    )
                )
        self.stdout.write(f"  xodimlar: {len(employees)}")
        return employees

    def _payroll(
        self, organization: Any, branch: Any, owner: Any, months: int, employees: list[Any]
    ) -> None:
        from apps.cash.models import CashAccountKind
        from apps.cash.services import account_for_method, transfer
        from apps.payroll.services import create_run, finalize_run, mark_run_paid

        today = timezone.localdate()
        runs = 0
        for back in range(months - 1, 0, -1):  # joriy oy qoralama qoladi
            period = _month_start(today, back)
            try:
                run = create_run(
                    organization=organization,
                    branch=branch,
                    period_year=period.year,
                    period_month=period.month,
                )
                finalize_run(run=run, finalized_by=owner)

                # Oylikdan OLDIN bankdan kassaga pul yechiladi — haqiqiy
                # bog'cha aynan shunday qiladi (ADR-17).
                #
                # Usiz demo ma'lumoti "Naqd kassa: −1 750 500" ko'rsatardi:
                # tushum asosan terminal orqali — ya'ni bankka — keladi,
                # naqd maosh esa kassadan chiqadi. Raqam TO'G'RI edi, lekin
                # bog'chaning haqiqiy ish tartibini aks ettirmasdi.
                bank = account_for_method(branch=branch, method="bank_transfer")
                till = account_for_method(branch=branch, method="cash")
                need = run.total_net
                if need > 0 and bank.kind == CashAccountKind.BANK:
                    transfer(
                        source=bank,
                        target=till,
                        amount=need,
                        description="Oylik uchun bankdan naqd yechildi",
                        occurred_at=timezone.make_aware(datetime.combine(period, time(hour=9))),
                        created_by=owner,
                    )

                mark_run_paid(run=run)
                runs += 1
            except Exception as exc:
                logger.warning("Oylik hisoblash o'tkazib yuborildi (%s): %s", period, exc)
                continue

        # Joriy oy — qoralama, ya'ni ekranda tahrirlash mumkin bo'ladi.
        try:
            create_run(
                organization=organization,
                branch=branch,
                period_year=today.year,
                period_month=today.month,
            )
        except Exception as exc:
            logger.warning("Joriy oy qoralamasi yaratilmadi: %s", exc)

        self.stdout.write(f"  oylik hisoblash: {runs} ta yopilgan + 1 qoralama")

    def _inventory(self, organization: Any, branch: Any, owner: Any, child_count: int) -> None:
        from apps.cash.services import account_for_method
        from apps.inventory.models import Product, ProductCategory, Supplier, Warehouse
        from apps.inventory.services import record_movement

        # Xarid ham bog'chaning KATTALIGIGA bog'liq: 12 bolaga 200 ta
        # tuxum olinmaydi. Ilgari miqdor qat'iy edi va kichik bog'chada
        # bitta xarid butun kassani bo'shatib yuborardi.
        scale = max(Decimal("0.35"), Decimal(child_count) / Decimal(BAZAVIY_BOLALAR))
        accounts = {
            "bank": account_for_method(branch=branch, method="bank_transfer"),
            "cash": account_for_method(branch=branch, method="cash"),
        }

        warehouse, _ = Warehouse.objects.get_or_create(
            organization=organization, branch=branch, name="Asosiy ombor"
        )
        supplier, _ = Supplier.objects.get_or_create(
            organization=organization,
            branch=branch,
            name="Oziq-ovqat Savdo MChJ",
            defaults={"phone": "+998712001020"},
        )

        movements = 0
        for name, category_name, unit, min_stock, price in MAHSULOTLAR:
            category, _ = ProductCategory.objects.get_or_create(
                organization=organization, branch=branch, name=category_name
            )
            product, _ = Product.objects.get_or_create(
                organization=organization,
                branch=branch,
                name=name,
                defaults={"category": category, "unit": unit, "min_stock": min_stock},
            )

            # Kirim, keyin bir necha chiqim — qoldiq tabiiy shakllanadi.
            incoming = (min_stock * Decimal(random.randint(3, 6)) * scale).quantize(
                Decimal("0.001")
            )
            if incoming <= 0:
                continue
            purchased_on = timezone.now() - timedelta(days=random.randint(20, 40))
            self._top_up(accounts, "cash", incoming * price, purchased_on.date(), owner)
            record_movement(
                product=product,
                warehouse=warehouse,
                movement_type="purchase",
                quantity=incoming,
                supplier=supplier,
                unit_cost=price,
                occurred_at=purchased_on,
                reference=f"NAK-{random.randint(1000, 9999)}",
            )
            movements += 1

            remaining = incoming
            for _ in range(random.randint(2, 5)):
                use = (remaining * Decimal(str(round(random.uniform(0.1, 0.3), 2)))).quantize(
                    Decimal("0.001")
                )
                if use <= 0 or use > remaining:
                    break
                record_movement(
                    product=product,
                    warehouse=warehouse,
                    movement_type="consumption",
                    quantity=use,
                    occurred_at=timezone.now() - timedelta(days=random.randint(1, 18)),
                )
                remaining -= use
                movements += 1

        self.stdout.write(f"  ombor harakatlari: {movements}")

    def _expenses(
        self, organization: Any, branch: Any, owner: Any, months: int, child_count: int
    ) -> None:
        from apps.cash.services import account_for_method
        from apps.expenses.models import Expense, ExpenseCategory
        from apps.expenses.services import approve_expense, mark_expense_paid

        today = timezone.localdate()
        # Chiqim bog'chaning KATTALIGIGA bog'liq: 12 bolalik bog'cha
        # 64 bolalikcha elektr ishlatmaydi. Pastki chegara bor —
        # bino baribir isitiladi va yoritiladi.
        scale = max(Decimal("0.35"), Decimal(child_count) / Decimal(BAZAVIY_BOLALAR))
        accounts = {
            "bank": account_for_method(branch=branch, method="bank_transfer"),
            "cash": account_for_method(branch=branch, method="cash"),
        }
        created = 0
        for back in range(months):
            period = _month_start(today, back)
            for category_name, description, base, source in CHIQIMLAR:
                category, _ = ExpenseCategory.objects.get_or_create(
                    organization=organization, branch=branch, name=category_name
                )
                amount = (base * scale).quantize(Decimal("1")) + Decimal(
                    random.randint(-15, 20) * 10000
                )
                if amount <= 0:
                    continue
                expense = Expense.objects.create(
                    organization=organization,
                    branch=branch,
                    category=category,
                    amount=amount,
                    expense_date=period + timedelta(days=random.randint(2, 25)),
                    description=description,
                )
                created += 1
                # Joriy oyda bittasi tasdiqlanmagan qoladi — tasdiqlash
                # oqimini ekranda ko'rsatish uchun.
                if back == 0 and category_name == "Ta'mirlash":
                    continue
                # Naqd chiqim uchun kassada pul yetmasa — avval bankdan
                # yechiladi. Bog'cha ham shunday qiladi: ADR-29 "qopda
                # yo'q pul chiqmaydi" deydi, ya'ni yechish HODISA bo'lib
                # yozilishi kerak, chiqim esa o'z vaqtida qolishi.
                self._top_up(accounts, source, expense.amount, expense.expense_date, owner)
                approve_expense(
                    expense=expense,
                    approved_by=owner,
                    note="Byudjetda bor",
                    cash_account=accounts[source],
                )
                if back > 0:
                    mark_expense_paid(expense=expense)

        self.stdout.write(f"  chiqimlar: {created}")

    @staticmethod
    def _top_up(
        accounts: dict[str, Any], source: str, need: Decimal, day: date, owner: Any
    ) -> None:
        """Kassada pul yetmasa — bankdan yechib qo'yadi, yumaloq summada."""
        from apps.cash.selectors import account_balance
        from apps.cash.services import transfer

        if source != "cash":
            return
        account = accounts["cash"]
        balance = account_balance(account_id=account.id)
        if balance >= need:
            return
        # Yumaloq summa: bog'chada ham "aniq 84 500" yechilmaydi.
        short = need - balance
        amount = (short / Decimal("500000")).to_integral_value(rounding="ROUND_CEILING") * Decimal(
            "500000"
        )
        try:
            transfer(
                source=accounts["bank"],
                target=account,
                amount=amount,
                description="Kassaga naqd yechildi",
                occurred_at=timezone.make_aware(datetime.combine(day, time(hour=10))),
                created_by=owner,
            )
        except Exception as exc:
            logger.warning("Kassaga yechib boʻlmadi: %s", exc)

    def _notifications(self, organization: Any) -> None:
        """
        Qarzdorlarga eslatma — jurnalda yozuv paydo bo'lsin.

        Soat ATAYLAB berilgan: demo kechqurun yoki tunda yaratilsa,
        yuborish oynasi (Q9) xabarlarni navbatda qoldirardi va demo
        jurnali bo'sh ko'rinardi.

        Demo vasiylari Telegramga ULANMAGAN — ataylab: aynan shu
        holat yangi bog'chada bo'ladi va ekran uni qanday ko'rsatishi
        demoda ko'rinishi kerak.
        """
        from datetime import time

        from apps.notifications.services import dispatch_notification, queue_debt_reminders

        queued = queue_debt_reminders(organization=organization)
        for notification in queued[:12]:
            dispatch_notification(notification, now_time=time(10, 0))
        self.stdout.write(f"  bildirishnomalar: {len(queued)} (12 tasi yuborilgan)")

    # --- Xulosa ---

    def _summary(self, organization: Any) -> None:
        from apps.reports.selectors import debtor_report
        from apps.reports.services import dashboard_kpis, invalidate_dashboard

        invalidate_dashboard(organization_id=organization.id)
        kpis = dashboard_kpis(organization_id=organization.id)
        debtors = debtor_report(organization_id=organization.id)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Demo tayyor:"))
        self.stdout.write(f"  faol bolalar        {kpis['active_children']}")
        self.stdout.write(f"  shu oy tushum       {Decimal(kpis['month_revenue']):,.0f} so'm")
        self.stdout.write(
            f"  qarzdorlik          {Decimal(debtors['total_outstanding']):,.0f} so'm "
            f"({debtors['debtor_count']} bola)"
        )
        self.stdout.write(f"  davomat (shu oy)    {kpis['attendance_month_pct']} %")
        self.stdout.write(f"  kam qolgan mahsulot {kpis['low_stock_count']}")
