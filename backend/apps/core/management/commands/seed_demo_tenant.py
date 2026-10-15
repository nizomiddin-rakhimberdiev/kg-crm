"""
Namoyish bog'chasi — `/t/demo` (PLAN 5.10).

Sotuv suhbatida "mana shunday ishlaydi" deb ko'rsatiladigan alohida
tenant. `seed_demo` dan farqi — NISHON: u istalgan tashkilotni
to'ldira olardi (va bir marta haqiqiy mijozning — Oriental
Kinderland'ning — tashkilotini to'ldirib qo'ygan). Bu buyruq esa
**faqat `demo` slug'i bilan ishlaydi** va boshqa nishonni qabul
qilmaydi: argument ham yo'q, qidiruv ham yo'q.

Tarkib (brief, 5.10):

* 3 guruh, 45 bola — jinsiga mos o'zbekcha ism, familiya va ota ismi,
  takrorsiz;
* 6 oylik faktura va to'lov, qarzdorlik 10–15 % (45 boladan 6 tasi);
* chiqimlar: oziq-ovqat, kommunal, ijara, xo'jalik;
* ombor mahsulotlari va harakatlari;
* 8 xodim va oyligi, 3 oylik davomat;
* SMS o'chirilgan (`notifications.sms_enabled = False`).

Ma'lumot `seed_demo` dagi kabi **servis qatlami orqali** yoziladi —
ledger, kassa va balans haqiqiy tizim holatiga mos keladi.

Ishlatish::

    DEMO_OWNER_PASSWORD=… python manage.py seed_demo_tenant
    python manage.py seed_demo_tenant --reset --dry-run   # nima bo'lishini ko'rsatadi
    python manage.py seed_demo_tenant --reset             # kechasi qayta tiklash

Parol faqat `.env` dan (`DEMO_OWNER_PASSWORD`) — buyruq satrida emas:
u shell tarixiga va `ps` chiqishiga tushardi.

`--reset` — `platform/purge.py` dagi audit qilinadigan to'liq
o'chirish (`force=True`, faqat `demo` uchun) va qaytadan yaratish.
O'chirish tartibi o'sha yerda yuritiladi va testda tekshiriladi —
bu yerda alohida ro'yxat yuritish ertami-kechmi undan ajralib qolardi.
"""

from __future__ import annotations

import os
import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from django.core.management.base import CommandError
from django.db import transaction
from django.utils import timezone

from apps.core.management.commands.seed_demo import Command as SeedDemo
from apps.core.management.commands.seed_demo import _month_start
from apps.core.tenancy import organization_context, platform_context

#: Yagona nishon. O'zgartirib bo'lmaydi — argument yo'q.
DEMO_SLUG = "demo"
DEMO_NAME = "Radix Demo Bogʻchasi"

SEED = 20261002

CHILDREN = 45
MONTHS = 6
ATTENDANCE_MONTHS = 3
#: 45 boladan 6 tasi — 13,3 % (brief: 10–15 %).
DEBTORS = 6

FAMILIYALAR = [
    "Abdullayev", "Aliyev", "Azimov", "Bakirov", "Ergashev", "Fayzullayev",
    "Hamidov", "Ibragimov", "Jalolov", "Karimov", "Latipov", "Mahmudov",
    "Nazarov", "Normatov", "Qodirov", "Rahimov", "Rasulov", "Saidov",
    "Sobirov", "Sultonov", "Tursunov", "Umarov", "Usmonov", "Valiyev",
    "Xolmatov", "Yusupov", "Zokirov",
]  # fmt: skip

O_ISMLAR = [
    "Abdulloh", "Akbar", "Ali", "Amir", "Aziz", "Bekzod", "Bobur", "Diyor",
    "Doston", "Elyor", "Farrux", "Islom", "Jasur", "Javohir", "Muhammad",
    "Otabek", "Sardor", "Sanjar", "Shohruh", "Temur", "Umid", "Yahyo",
    "Zafar", "Asadbek", "Imron",
]  # fmt: skip

Q_ISMLAR = [
    "Asal", "Dilnoza", "Durdona", "Gulnoza", "Hilola", "Kamola", "Laylo",
    "Madina", "Malika", "Mohinur", "Nigora", "Nodira", "Oysha", "Robiya",
    "Sabina", "Sevara", "Shahzoda", "Soliha", "Zarina", "Zilola", "Ziyoda",
    "Muslima", "Maftuna", "Fotima", "Ruxshona",
]  # fmt: skip

#: Ota ismlari — ota ismi (`… oʻgʻli` / `… qizi`) va otalar uchun.
OTA_ISMLAR = [
    "Alisher", "Bahodir", "Botir", "Dilshod", "Farhod", "Jamshid", "Komil",
    "Nodir", "Olim", "Rustam", "Sherzod", "Ulugʻbek", "Shavkat", "Anvar",
    "Hasan", "Husan",
]  # fmt: skip

ONA_ISMLAR = [
    "Dilfuza", "Feruza", "Gulnora", "Mavluda", "Nasiba", "Shahnoza", "Umida",
    "Zulfiya", "Barno", "Nilufar",
]  # fmt: skip

GURUHLAR = [
    ("Quyoshcha", 3, 4, 16),
    ("Yulduzcha", 4, 5, 16),
    ("Bilimdon", 5, 6, 16),
]

XODIMLAR = [
    # (lavozim, bo'lim, oylik, soni) — jami 8.
    ("Tarbiyachi", "Taʼlim", Decimal("4200000"), 3),
    ("Tarbiyachi yordamchisi", "Taʼlim", Decimal("2800000"), 2),
    ("Oshpaz", "Oshxona", Decimal("3500000"), 1),
    ("Hamshira", "Tibbiyot", Decimal("3800000"), 1),
    ("Farrosh", "Xoʻjalik", Decimal("2400000"), 1),
]

CHIQIMLAR = [
    ("Oziq-ovqat", "Bozor xaridi — sabzavot va meva", Decimal("3200000")),
    ("Kommunal", "Elektr energiyasi", Decimal("2400000")),
    ("Kommunal", "Gaz va suv", Decimal("1300000")),
    ("Ijara", "Bino ijarasi", Decimal("8000000")),
    ("Xoʻjalik", "Tozalash vositalari", Decimal("480000")),
]


def female_surname(surname: str) -> str:
    """`Karimov` → `Karimova`: o'zbek familiyasining ayol shakli."""
    return surname + "a"


def patronymic(father: str, *, is_boy: bool) -> str:
    """Ota ismi o'zbekcha shaklda: `Rustam oʻgʻli` / `Rustam qizi`."""
    return f"{father} {'oʻgʻli' if is_boy else 'qizi'}"


class Command(SeedDemo):
    help = "Namoyish bog'chasini (/t/demo) yaratadi va to'ldiradi. Boshqa tenantlarga tegmaydi."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Demo bog'chani to'liq o'chirib, qaytadan yaratadi (kechki tiklash)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Hammasini bajaradi va natijani ko'rsatadi, lekin bazaga YOZMAYDI",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        random.seed(SEED)
        dry_run = options["dry_run"]

        try:
            with transaction.atomic():
                self._run(reset=options["reset"])
                if dry_run:
                    raise _DryRun
        except _DryRun:
            self.stdout.write(self.style.WARNING("\n[dry-run] Hech narsa yozilmadi."))

    def _run(self, *, reset: bool) -> None:
        from apps.organizations.models import Organization

        with platform_context():
            existing = Organization.objects.filter(slug=DEMO_SLUG).first()

        if existing is not None and reset:
            self._purge(existing)
            existing = None

        if existing is None:
            organization = self._create()
        else:
            organization = existing
            with organization_context(organization.id):
                from apps.children.models import Child

                if Child.objects.exists():
                    raise CommandError(f"'{DEMO_SLUG}' allaqachon to'ldirilgan. Qaytadan: --reset")

        self.stdout.write(f"Tashkilot: {organization.name} (/t/{organization.slug})")
        with organization_context(organization.id):
            self._disable_sms(organization)
            self._seed(organization, CHILDREN, MONTHS)

    # --- Yaratish va o'chirish ---

    def _create(self) -> Any:
        from apps.accounts.services import register_organization

        password = os.environ.get("DEMO_OWNER_PASSWORD", "")
        if not password:
            raise CommandError(
                "DEMO_OWNER_PASSWORD .env da yo'q. Demo egasining paroli faqat muhitdan "
                "olinadi — buyruq satrida u shell tarixida qolardi."
            )
        email = os.environ.get("DEMO_OWNER_EMAIL", "demo@radix-crm.uz")
        result = register_organization(
            organization_name=DEMO_NAME,
            contact_email=email,
            full_name="Demo Rahbar",
            password=password,
            slug=DEMO_SLUG,
        )
        self.stdout.write(f"  yaratildi, kirish: {email}")
        return result.organization

    def _purge(self, organization: Any) -> None:
        from apps.platform.purge import purge_organization

        # Ikkinchi qulf: nishon `DEMO_SLUG` dan boshqa bo'lishi
        # mumkin emas, lekin `force=True` dan oldin buni yana bir bor
        # tekshirish arzon, xatosi esa qaytarib bo'lmaydi.
        if organization.slug != DEMO_SLUG:
            raise CommandError(f"Faqat '{DEMO_SLUG}' tiklanadi.")
        deleted = purge_organization(
            organization_id=organization.id, confirm_slug=DEMO_SLUG, force=True
        )
        self.stdout.write(
            self.style.WARNING(f"  eski demo o'chirildi: {sum(deleted.values())} qator")
        )

    def _disable_sms(self, organization: Any) -> None:
        from apps.settings_app.services import set_setting

        set_setting(organization=organization, key="notifications.sms_enabled", value=False)

    # --- seed_demo qadamlarining demo shakli ---

    def _groups(self, organization: Any, branch: Any) -> list[Any]:
        from apps.children.models import Group

        groups = [
            Group.objects.create(
                organization=organization,
                branch=branch,
                name=name,
                age_min=age_min,
                age_max=age_max,
                capacity=capacity,
            )
            for name, age_min, age_max, capacity in GURUHLAR
        ]
        self.stdout.write(f"  guruhlar: {len(groups)}")
        return groups

    def _children(
        self, organization: Any, branch: Any, groups: list[Any], tariffs: list[Any], count: int
    ) -> list[Any]:
        """Har guruhga 15 bola; to'liq ism (F.I.Sh.) takrorlanmaydi."""
        from apps.children.models import Child, Guardian
        from apps.children.services import attach_guardian, enroll_child

        today = timezone.localdate()
        used: set[tuple[str, str]] = set()
        children = []
        per_group = count // len(groups)

        for index in range(count):
            group = groups[min(index // per_group, len(groups) - 1)]
            is_boy = index % 2 == 0
            while True:
                surname = random.choice(FAMILIYALAR)
                last_name = surname if is_boy else female_surname(surname)
                first_name = random.choice(O_ISMLAR if is_boy else Q_ISMLAR)
                # Takrorsiz — ism+familiya juftligi bo'yicha: ota ismi
                # farq qilsa ham ro'yxatda ikki "Karimov Ali" chalkash.
                if (last_name, first_name) not in used:
                    used.add((last_name, first_name))
                    break
            father = random.choice(OTA_ISMLAR)
            age = random.randint(group.age_min, group.age_max - 1)

            child = Child.objects.create(
                organization=organization,
                branch=branch,
                first_name=first_name,
                last_name=last_name,
                middle_name=patronymic(father, is_boy=is_boy),
                date_of_birth=today.replace(year=today.year - age)
                - timedelta(days=random.randint(0, 300)),
                gender="male" if is_boy else "female",
                tariff=random.choices(tariffs, weights=[70, 22, 8])[0],
                # 6 oylik tarix bo'lishi uchun hammasi oynadan OLDIN.
                enrolled_on=_month_start(today, MONTHS) - timedelta(days=index),
            )
            mother = random.random() < 0.7
            guardian = Guardian.objects.create(
                organization=organization,
                branch=branch,
                first_name=random.choice(ONA_ISMLAR) if mother else father,
                last_name=female_surname(surname) if mother else surname,
                phone=f"+99890{1000000 + index * 7919 % 8999999:07d}",
            )
            attach_guardian(
                child=child,
                guardian=guardian,
                relation="mother" if mother else "father",
                is_primary=True,
            )
            enroll_child(child=child, group=group)
            children.append(child)

        self.stdout.write(f"  bolalar: {len(children)} (vasiylari bilan)")
        return children

    def _finance(self, children: list[Any], months: int, owner: Any) -> None:
        """
        6 oy faktura va to'lov; qarz ANIQ 6 oilada (13,3 %).

        Qarzdorlar so'nggi yopiq oyni qisman, joriy oyni umuman
        to'lamagan — haqiqiy bog'chadagi kabi qarz bir-ikki oydan
        oshmaydi. Qolganlar hamma oyni to'liq to'laydi: aks holda
        joriy oyning hali yig'ilayotgan to'lovlari "qarzdorlar" sonini
        tasodifiy oshirib, 10–15 % chegarasini buzardi.
        """
        from apps.finance.models import PaymentMethod
        from apps.finance.services import issue_invoice, record_payment

        today = timezone.localdate()
        debtors = set(random.sample(range(len(children)), DEBTORS))
        invoices = payments = 0

        for back in range(months - 1, -1, -1):
            period = _month_start(today, back)
            is_current = back == 0
            for index, child in enumerate(children):
                invoice = issue_invoice(
                    child=child,
                    period_year=period.year,
                    period_month=period.month,
                    created_by=owner,
                )
                invoices += 1

                share = Decimal("1")
                if index in debtors:
                    if is_current:
                        continue
                    if back == 1:
                        share = Decimal("0.5")
                amount = (invoice.amount_due * share).quantize(Decimal("1"))
                if amount <= 0:
                    continue

                last_day = today.day if is_current else 28
                record_payment(
                    child=child,
                    amount=amount,
                    method=random.choices(
                        [PaymentMethod.CASH, PaymentMethod.TERMINAL, PaymentMethod.BANK_TRANSFER],
                        weights=[45, 40, 15],
                    )[0],
                    invoice=invoice,
                    paid_at=timezone.make_aware(
                        datetime(
                            period.year,
                            period.month,
                            random.randint(1, max(1, last_day)),
                            random.randint(9, 17),
                            random.randint(0, 59),
                        )
                    ),
                    received_by=owner,
                    # Demo tarixi oylar orqaga ketadi (Bosqich 12.4 qoidalari).
                    backdate_reason="Demo maʼlumot",
                    allocation_reason="Demo maʼlumot",
                )
                payments += 1

        self.stdout.write(f"  hisob-fakturalar: {invoices}, to'lovlar: {payments}")

    def _attendance(
        self, organization: Any, branch: Any, groups: list[Any], owner: Any, months: int
    ) -> None:
        # Davomat 3 oy (brief) — moliya 6 oy bo'lsa ham.
        super()._attendance(organization, branch, groups, owner, ATTENDANCE_MONTHS)

    def _staff(self, organization: Any, branch: Any) -> list[Any]:
        from apps.hr.models import Employee, Position

        employees = []
        index = 0
        for title, department, salary, headcount in XODIMLAR:
            position = Position.objects.create(
                organization=organization, branch=branch, title=title, department=department
            )
            for _ in range(headcount):
                is_man = title == "Oshpaz" or index % 3 == 2
                employees.append(
                    Employee.objects.create(
                        organization=organization,
                        branch=branch,
                        first_name=random.choice(OTA_ISMLAR if is_man else ONA_ISMLAR),
                        last_name=(
                            random.choice(FAMILIYALAR)
                            if is_man
                            else female_surname(random.choice(FAMILIYALAR))
                        ),
                        phone=f"+99891{2000000 + index * 104729 % 7999999:07d}",
                        position=position,
                        hire_date=timezone.localdate() - timedelta(days=400 + index * 37),
                        base_salary=salary,
                    )
                )
                index += 1
        self.stdout.write(f"  xodimlar: {len(employees)}")
        return employees

    def _expenses(self, organization: Any, branch: Any, owner: Any, months: int) -> None:
        from apps.expenses.models import Expense, ExpenseCategory
        from apps.expenses.services import approve_expense, mark_expense_paid

        today = timezone.localdate()
        created = 0
        for back in range(months):
            period = _month_start(today, back)
            for category_name, description, base in CHIQIMLAR:
                category, _ = ExpenseCategory.objects.get_or_create(
                    organization=organization, branch=branch, name=category_name
                )
                # Ijara o'zgarmaydi; qolganlari oydan oyga biroz farq qiladi.
                drift = 0 if category_name == "Ijara" else random.randint(-15, 20) * 10000
                expense_date = period + timedelta(days=random.randint(2, 25))
                if expense_date > today:
                    expense_date = today
                expense = Expense.objects.create(
                    organization=organization,
                    branch=branch,
                    category=category,
                    amount=base + Decimal(drift),
                    expense_date=expense_date,
                    description=description,
                )
                created += 1
                approve_expense(expense=expense, approved_by=owner, note="Byudjetda bor")
                if back > 0:
                    mark_expense_paid(expense=expense)
        self.stdout.write(f"  chiqimlar: {created}")


class _DryRun(Exception):
    """`--dry-run` tranzaksiyani shu bilan orqaga qaytaradi."""
