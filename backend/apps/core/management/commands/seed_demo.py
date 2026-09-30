"""
Demo ma'lumotini to'ldiradi — ko'rsatish va qo'lda sinash uchun.

Ma'lumot **servis qatlami orqali** yaratiladi, to'g'ridan-to'g'ri model
yozish bilan emas. Bu ataylab: shunda seed ham biznes qoidalaridan
o'tadi (ledger, balans, guruh sig'imi, stok qoldig'i) va natija haqiqiy
tizim holatiga aynan o'xshaydi. To'g'ridan-to'g'ri yozilgan demo esa
"chiroyli, lekin mumkin bo'lmagan" holat yaratardi — va aynan shunday
holatda qilingan demo keyin ishlab chiqarishda takrorlanmasdi.

Ishlatish::

    python manage.py seed_demo --email ranizomiddin@gmail.com
    python manage.py seed_demo --email ... --reset   # avval tozalaydi

⚠️ Bu buyruq ishlab chiqarishda ishlatilmasligi kerak. `--reset`
tashkilotning BARCHA operatsion ma'lumotini o'chiradi.
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

GURUHLAR = [
    ("Chaqaloq", 2, 3, 16),
    ("Quyoshcha", 3, 4, 18),
    ("Kamalak", 3, 4, 18),
    ("Yulduzcha", 4, 5, 18),
    ("Gulchehra", 4, 5, 16),
    ("Bilimdon", 5, 6, 18),
    ("Maktabgacha", 6, 7, 16),
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

CHIQIMLAR = [
    ("Kommunal", "Elektr energiyasi", Decimal("2400000")),
    ("Kommunal", "Suv va kanalizatsiya", Decimal("650000")),
    ("Kommunal", "Gaz", Decimal("1100000")),
    ("Xo'jalik", "Tozalash vositalari", Decimal("480000")),
    ("Ta'mirlash", "Oshxona jihozi ta'miri", Decimal("1750000")),
    ("Boshqa", "Internet va aloqa", Decimal("390000")),
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
        Operatsion ma'lumotni o'chiradi — tashkilot, foydalanuvchi va
        obunani QOLDIRADI.

        Tartib `purge.py` dagi bilan bir xil mantiqda: bolalardan otaga.
        """
        from apps.attendance.models import AttendanceRecord
        from apps.children.models import Child, ChildGuardian, Enrollment, Group, Guardian
        from apps.expenses.models import Expense, ExpenseCategory
        from apps.finance.models import (
            ChildLedgerEntry,
            Discount,
            Invoice,
            InvoiceLine,
            Payment,
            TariffPlan,
        )
        from apps.hr.models import Employee, Position
        from apps.inventory.models import (
            Product,
            ProductCategory,
            StockMovement,
            Supplier,
            Warehouse,
        )
        from apps.notifications.models import Notification
        from apps.payroll.models import PayrollItem, PayrollRun

        # Tartib QAT'IY: `Child.tariff` `RESTRICT`, ya'ni bolalarni
        # tariflardan OLDIN o'chirish kerak. Xuddi shunday, bildirishnoma
        # vasiyga, davomat bolaga ishora qiladi. Bu tartib
        # `platform/purge.py` dagi bilan bir xil mantiqda: chekkadan
        # markazga.
        InvoiceLine.objects.filter(invoice__organization_id=organization.id).delete()
        for model in (
            Payment,
            ChildLedgerEntry,
            Invoice,
            Discount,
            AttendanceRecord,
            Enrollment,
            ChildGuardian,
            Notification,
            Child,
            Guardian,
            Group,
            TariffPlan,
            PayrollItem,
            PayrollRun,
            Employee,
            Position,
            StockMovement,
            Product,
            ProductCategory,
            Supplier,
            Warehouse,
            Expense,
            ExpenseCategory,
        ):
            manager = getattr(model, "all_objects", None) or model._default_manager
            manager.all().delete()
        self.stdout.write(self.style.WARNING("  eski ma'lumot o'chirildi"))

    # --- To'ldirish ---

    @transaction.atomic
    def _seed(self, organization: Any, child_count: int, months: int) -> None:
        branch = self._branch(organization)
        owner = self._owner(organization)

        groups = self._groups(organization, branch)
        tariffs = self._tariffs(organization, branch)
        children = self._children(organization, branch, groups, tariffs, child_count)
        self._finance(children, months, owner)
        self._attendance(organization, branch, groups, owner, months)
        employees = self._staff(organization, branch)
        self._payroll(organization, branch, owner, months, employees)
        self._inventory(organization, branch)
        self._expenses(organization, branch, owner, months)
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
        self, organization: Any, branch: Any, groups: list[Any], tariffs: list[Any], count: int
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

            child = Child.objects.create(
                organization=organization,
                branch=branch,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=birth,
                gender="male" if is_boy else "female",
                # Tarif taqsimoti realistik: ko'pchilik to'liq kunda.
                tariff=random.choices(tariffs, weights=[70, 22, 8])[0],
                enrolled_on=today - timedelta(days=random.randint(30, 700)),
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

            # Guruhga yoshiga qarab — sig'im to'lgan bo'lsa keyingisiga.
            for group in sorted(groups, key=lambda g: abs((g.age_min or 4) - age_years)):
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
                    full_chance = 0.96 if not is_current else 0.70
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
                paid_at = timezone.make_aware(
                    datetime(
                        period.year,
                        period.month,
                        random.randint(1, max(1, last_day)),
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
                    invoice=invoice,
                    paid_at=paid_at,
                    received_by=owner,
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
                    )
                    marked += len(records)
                except Exception as exc:
                    logger.warning("Davomat yozilmadi (%s, %s): %s", group.name, day, exc)
                    continue

        self.stdout.write(f"  davomat yozuvlari: {marked}")

    def _staff(self, organization: Any, branch: Any) -> list[Any]:
        from apps.hr.models import Employee, Position

        employees = []
        for title, department, salary in LAVOZIMLAR:
            position, _ = Position.objects.get_or_create(
                organization=organization,
                branch=branch,
                title=title,
                defaults={"department": department},
            )
            # Tarbiyachilar bir nechta, qolganlari bittadan.
            headcount = 4 if title == "Tarbiyachi" else (2 if "yordamchisi" in title else 1)
            for _ in range(headcount):
                employees.append(
                    Employee.objects.create(
                        organization=organization,
                        branch=branch,
                        first_name=random.choice(ONA_ISMLAR + OTA_ISMLAR),
                        last_name=random.choice(FAMILIYALAR),
                        phone=f"+9989{random.randint(0, 9)}{random.randint(1000000, 9999999)}",
                        position=position,
                        hire_date=timezone.localdate() - timedelta(days=random.randint(120, 1500)),
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

                # Oylikdan OLDIN terminaldan kassaga pul o'tkaziladi —
                # haqiqiy bog'cha aynan shunday qiladi (ADR-17).
                #
                # Usiz demo ma'lumoti "Naqd kassa: −1 750 500" ko'rsatardi:
                # tushum asosan terminalga tushadi, naqd maosh esa kassadan
                # chiqadi. Raqam TO'G'RI edi, lekin bog'chaning haqiqiy
                # ish tartibini aks ettirmasdi.
                terminal = account_for_method(branch=branch, method="terminal")
                till = account_for_method(branch=branch, method="cash")
                need = run.total_net
                if need > 0 and terminal.kind == CashAccountKind.TERMINAL:
                    transfer(
                        source=terminal,
                        target=till,
                        amount=need,
                        description="Oylik uchun kassaga o'tkazma",
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

    def _inventory(self, organization: Any, branch: Any) -> None:
        from apps.inventory.models import Product, ProductCategory, Supplier, Warehouse
        from apps.inventory.services import record_movement

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
            incoming = min_stock * Decimal(random.randint(3, 6))
            record_movement(
                product=product,
                warehouse=warehouse,
                movement_type="purchase",
                quantity=incoming,
                supplier=supplier,
                unit_cost=price,
                occurred_at=timezone.now() - timedelta(days=random.randint(20, 40)),
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
                amount = base + Decimal(random.randint(-15, 20) * 10000)
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
                approve_expense(expense=expense, approved_by=owner, note="Byudjetda bor")
                if back > 0:
                    mark_expense_paid(expense=expense)

        self.stdout.write(f"  chiqimlar: {created}")

    def _notifications(self, organization: Any) -> None:
        """Qarzdorlarga eslatma — jurnalda yozuv paydo bo'lsin."""
        from apps.notifications.services import dispatch_notification, queue_debt_reminders

        queued = queue_debt_reminders(organization=organization)
        for notification in queued[:12]:
            dispatch_notification(notification)
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
