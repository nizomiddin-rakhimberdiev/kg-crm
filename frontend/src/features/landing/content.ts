/**
 * Test-redesign sahifasi matnlari (UZ / RU).
 *
 * Bu sahifa `/test-redesign` da yashaydi va asosiy landing'ga tegmaydi.
 * Narx raqamlari ADR-12 bilan bir xil (400 000 / 50 bola, +50 000 / 10,
 * yillik −25 %) — kalkulyator esa raqamni backend'dan oladi.
 *
 * Uydirma narsa yo'q: mijoz, statistika, mukofot, sharh — hech biri.
 * UI ichidagi raqamlar NAMUNAVIY va sahifada shunday deb yozilgan.
 */

export type Locale = 'uz' | 'ru'

export interface ModuleCopy {
  id: 'children' | 'payments' | 'attendance' | 'staff' | 'inventory' | 'reports'
  title: string
  text: string
  caption: string
}

export interface RoleCopy {
  id: 'owner' | 'director' | 'cashier' | 'admin'
  title: string
  text: string
  focus: string
}

export interface FragmentCopy {
  kind: string
  title: string
  lines: string[]
}

export interface StepCopy {
  time: string
  title: string
  text: string
}

export interface Copy {
  nav: {
    product: string
    capabilities: string
    pricing: string
    faq: string
    login: string
    demo: string
    menu: string
    close: string
    lang: Record<Locale, string>
  }
  hero: {
    eyebrow: string
    title: string
    subtitle: string
    cta: string
    secondary: string
    priceFrom: string
    scroll: string
  }
  demo: {
    note: string
    kpis: { label: string; value: number; suffix?: string; hint: string }[]
    sidebar: string[]
    org: string
    today: string
    chartTitle: string
    months: string[]
  }
  problem: {
    eyebrow: string
    title: string
    text: string
    fragments: FragmentCopy[]
    resolved: string
  }
  oneSystem: {
    eyebrow: string
    title: string
    text: string
    modules: string[]
    /** Bog'liqlik misollari: [sabab, natija] — panel ostida ko'rsatiladi. */
    links: [string, string][]
  }
  modules: {
    eyebrow: string
    title: string
    items: ModuleCopy[]
  }
  deepDive: {
    eyebrow: string
    title: string
    text: string
    steps: string[]
  }
  roles: { eyebrow: string; title: string; text: string; items: RoleCopy[] }
  workflow: { eyebrow: string; title: string; text: string; steps: StepCopy[] }
  finance: {
    eyebrow: string
    title: string
    text: string
    metrics: { id: string; label: string; value: number; tone: 'in' | 'out' | 'neutral' | 'warn' }[]
    equation: string
  }
  pricing: {
    eyebrow: string
    title: string
    text: string
    childrenLabel: string
    childrenUnit: string
    monthly: string
    annual: string
    annualBadge: string
    perMonth: string
    perYear: string
    effective: string
    includes: string[]
    examplesTitle: string
    examples: { children: number; monthly: number }[]
    annualFormula: string
    first3: string
    note: string
    cta: string
    error: string
    /** Ikkinchi yetkazib berish modeli — alohida o'rnatma (ADR-13). */
    standalone: { badge: string; title: string; text: string; points: string[]; cta: string }
  }
  faq: { eyebrow: string; title: string; items: { q: string; a: string }[] }
  lead: {
    eyebrow: string
    title: string
    text: string
    name: string
    phone: string
    kindergarten: string
    children: string
    city: string
    message: string
    consent: string
    privacy: string
    submit: string
    sending: string
    success: string
    error: string
  }
  final: { title: string; text: string; cta: string; secondary: string }
  footer: { privacy: string; terms: string; login: string; copyright: string }
  seo: { title: string; description: string }
}

const uz: Copy = {
  nav: {
    product: 'Mahsulot',
    capabilities: 'Imkoniyatlar',
    pricing: 'Narxlar',
    faq: 'Savollar',
    login: 'CRM’ga kirish',
    demo: 'Demo olish',
    menu: 'Menyu',
    close: 'Yopish',
    lang: { uz: 'UZ', ru: 'RU' },
  },
  hero: {
    eyebrow: 'Xususiy bog‘chalar uchun boshqaruv platformasi',
    title: 'Bog‘changizni boshqarishning barchasi — bitta tizimda.',
    subtitle: 'Bolalar, to‘lovlar, davomat, xodimlar va moliyaviy nazorat — hammasi Radix CRM’da.',
    cta: 'Demo olish',
    secondary: 'Radix qanday ishlaydi',
    priceFrom: '400 000 so‘m / oy dan',
    scroll: 'Pastga',
  },
  demo: {
    note: 'Ekranlardagi raqamlar — namunaviy ma’lumot.',
    kpis: [
      { label: 'Faol bolalar', value: 128, hint: 'ro‘yxatda' },
      { label: 'Bugungi davomat', value: 94, suffix: '%', hint: '120 / 128 belgilangan' },
      { label: 'Qarzdorlik', value: 12_450_000, hint: '9 ta bola bo‘yicha' },
      { label: 'Oylik tushum', value: 86_400_000, hint: 'sentabr' },
      { label: 'Xodimlar', value: 24, hint: '6 guruh' },
    ],
    sidebar: [
      'Boshqaruv paneli',
      'Bolalar',
      'Guruhlar',
      'To‘lovlar',
      'Qarzdorlar',
      'Davomat',
      'Xodimlar',
      'Ombor',
      'Hisobotlar',
    ],
    org: 'Quyosh bog‘chasi',
    today: '18-sentabr, payshanba',
    chartTitle: 'Tushum dinamikasi',
    months: ['Apr', 'May', 'Iyn', 'Iyl', 'Avg', 'Sen'],
  },
  problem: {
    eyebrow: 'Tanish holat',
    title: 'Rahbar nazorat qilishi kerak bo‘lgan ishlar turli joylarga sochilib ketmasin.',
    text: 'Telegram’dagi xabar, Excel’dagi jadval, daftardagi yozuv, kassadagi chek. Har biri to‘g‘ri — lekin umumiy manzara yo‘q.',
    fragments: [
      {
        kind: 'chat',
        title: 'Tarbiyachilar guruhi',
        lines: ['Bugun 3 bola kelmadi', 'Kimlar? — keyin yozaman'],
      },
      {
        kind: 'sheet',
        title: 'tolovlar_sentabr_final2.xlsx',
        lines: ['Karimov A. · 1 500 000 · ?', 'Rasulova M. · 1 500 000 · to‘landi'],
      },
      { kind: 'note', title: 'Daftar', lines: ['Yusupov — 600 ming qarz', 'Oshpaz — avans 400'] },
      { kind: 'receipt', title: 'Kassa cheki', lines: ['Naqd · 1 500 000', '12.09 · imzo yo‘q'] },
      {
        kind: 'attendance',
        title: 'Davomat varag‘i',
        lines: ['Quyosh guruhi · 18/20', 'Sana yozilmagan'],
      },
      {
        kind: 'staff',
        title: 'Xodimlar',
        lines: ['24 kishi · 3 ta shartnoma yo‘q', 'Ish haqi — Excel’da'],
      },
      { kind: 'expense', title: 'Xarajat', lines: ['Oziq-ovqat · 2 300 000', 'Chek — telefonda'] },
    ],
    resolved: 'Bitta tizim',
  },
  oneSystem: {
    eyebrow: 'Bitta tizim',
    title: 'Operatsion ish va moliyaviy nazorat — bir tizimda.',
    text: 'Har bir modul o‘z ishini qiladi va bir-biri bilan bog‘langan: davomat belgilansa — hisobot yangilanadi, to‘lov kirsa — qarzdorlik kamayadi.',
    modules: ['Bolalar', 'To‘lovlar', 'Davomat', 'Xodimlar', 'Ombor', 'Xarajatlar', 'Hisobotlar'],
    links: [
      ['Davomat belgilandi', 'Hisobot 94 %'],
      ['To‘lov kirdi', 'Qarz −1,5 mln'],
      ['Ombor chiqimi', 'Xarajat +2,3 mln'],
    ],
  },
  modules: {
    eyebrow: 'Imkoniyatlar',
    title: 'Har kuni kerak bo‘ladigan olti modul.',
    items: [
      {
        id: 'children',
        title: 'Bolalar va guruhlar',
        text: 'Har bir bola — profil, guruh, vasiy va tarif bilan. Guruhlar bo‘yicha filtr, tez qidiruv, bir zumda ochiladigan karta.',
        caption: 'Bolalar ro‘yxati → guruh filtri → profil',
      },
      {
        id: 'payments',
        title: 'To‘lovlar va qarzdorlik',
        text: 'Hisob-faktura, to‘lov, qoldiq. Qarzdorlar ro‘yxati ledger’dan hisoblanadi — u hech qachon haqiqatdan ajralmaydi.',
        caption: 'To‘langan → kutilmoqda → qarz',
      },
      {
        id: 'attendance',
        title: 'Davomat',
        text: 'Tarbiyachi bir chertishda belgilaydi, rahbar foizni ko‘radi. Yozilmagan kun — «yo‘q» emas, «belgilanmagan».',
        caption: 'Guruh davomati va kunlik foiz',
      },
      {
        id: 'staff',
        title: 'Xodimlar va ish haqi',
        text: 'Lavozim, rol, stavka, avans va oylik hisob-kitob — bitta joyda. Kim nimaga kirishini tashkilot egasi belgilaydi.',
        caption: 'Xodimlar ro‘yxati · ish haqi',
      },
      {
        id: 'inventory',
        title: 'Ombor va xarajatlar',
        text: 'Kirim, chiqim, qoldiq. Xarajat kategoriyalar bo‘yicha — oziq-ovqat, kommunal, ta’mir — va u hisobotga o‘zi tushadi.',
        caption: 'Qoldiq kamayadi → xarajat paydo bo‘ladi',
      },
      {
        id: 'reports',
        title: 'Hisobotlar va nazorat',
        text: 'Tushum, xarajat, ish haqi, qarzdorlik — bir ekranda. Har bir raqamni bosib, uning qayerdan kelganini ko‘rasiz.',
        caption: 'Barcha ko‘rsatkichlar bitta panelda',
      },
    ],
  },
  deepDive: {
    eyebrow: 'Boshqaruv paneli',
    title: 'Rahbar ko‘rishi kerak bo‘lgan barcha raqamlar — bir ekranda.',
    text: 'Bugungi davomat, oylik tushum, qarzdorlik va xodimlar — kirishingiz bilan. Har bir raqam jonli ma’lumotdan hisoblanadi.',
    steps: ['Umumiy holat', 'Davomat', 'Qarzdorlik', 'Tushum'],
  },
  roles: {
    eyebrow: 'Radix kimlar uchun?',
    title: 'Har bir rol o‘ziga kerak narsani ko‘radi.',
    text: 'Ruxsatlar rollarga asoslangan va tashkilot egasi tomonidan boshqariladi.',
    items: [
      {
        id: 'owner',
        title: 'Bog‘cha egasi',
        text: 'Biznesingizning umumiy holatini nazorat qiling.',
        focus: 'Tushum, qarzdorlik, xarajat — barcha filiallar bo‘yicha',
      },
      {
        id: 'director',
        title: 'Direktor',
        text: 'Kunlik operatsiyalarni bitta tizimdan boshqaring.',
        focus: 'Davomat, guruhlar, xodimlar, bugungi vazifalar',
      },
      {
        id: 'cashier',
        title: 'Kassir',
        text: 'To‘lovlar va qarzdorlikni aniq yuriting.',
        focus: 'Hisob-faktura, to‘lov qabul, qarzdorlar',
      },
      {
        id: 'admin',
        title: 'Administrator',
        text: 'Bolalar, guruhlar va davomatni tartibli boshqaring.',
        focus: 'Ro‘yxat, profil, guruhga biriktirish, davomat',
      },
    ],
  },
  workflow: {
    eyebrow: 'Radix bilan bir kun',
    title: 'Bir kun. Bitta tizim. Aniq nazorat.',
    text: 'Ertalabdan kechgacha — har bir amal o‘z joyida yoziladi va kechqurun hisobotga aylanadi.',
    steps: [
      {
        time: '08:00',
        title: 'Davomat',
        text: 'Tarbiyachi guruhni belgilaydi — 120 / 128 bola keldi.',
      },
      {
        time: '09:30',
        title: 'Guruhlar',
        text: 'Yangi bola «Yulduzcha» guruhiga biriktirildi. Sig‘im — 19 / 20.',
      },
      {
        time: '12:00',
        title: 'To‘lovlar',
        text: 'Kassir 3 ta to‘lov qabul qildi — qarzdorlik 12 450 000 ga tushdi.',
      },
      {
        time: '15:00',
        title: 'Xodimlar',
        text: 'Oshpazga avans yozildi. Oylik hisob-kitob o‘zi yangilandi.',
      },
      {
        time: '17:00',
        title: 'Hisobotlar',
        text: 'Rahbar kun yakunini ko‘radi: davomat 94 %, tushum, xarajat.',
      },
    ],
  },
  finance: {
    eyebrow: 'Moliyaviy nazorat',
    title: 'Pul qayerdan kelayotganini va qayerga ketayotganini biling.',
    text: 'Har bir so‘m — hisob-fakturadan to‘lovgacha, xarajatdan ish haqigacha — bitta jurnalda. Balans hisoblanadi, qo‘lda yozilmaydi.',
    metrics: [
      { id: 'revenue', label: 'Hisoblangan tushum', value: 86_400_000, tone: 'neutral' },
      { id: 'payments', label: 'Qabul qilingan to‘lovlar', value: 73_950_000, tone: 'in' },
      { id: 'debt', label: 'Qarzdorlik', value: 12_450_000, tone: 'warn' },
      { id: 'expenses', label: 'Xarajatlar', value: 18_300_000, tone: 'out' },
      { id: 'salaries', label: 'Ish haqi', value: 31_500_000, tone: 'out' },
      { id: 'balance', label: 'Balans', value: 24_150_000, tone: 'in' },
    ],
    equation: 'To‘lovlar − Xarajatlar − Ish haqi = Balans',
  },
  pricing: {
    eyebrow: 'Narxlar',
    title: '50 tagacha bola uchun — 400 000 so‘m / oy.',
    text: 'Narx faqat bolalar soniga bog‘liq. Filiallar va xodimlar soni cheklanmagan.',
    childrenLabel: 'Bolalar soni',
    childrenUnit: 'bola',
    monthly: 'Oylik',
    annual: 'Yillik',
    annualBadge: '25 % tejang',
    perMonth: '/ oy',
    perYear: '/ yil',
    effective: 'oyiga {amount} ga teng',
    includes: [
      'Barcha modullar',
      'Cheksiz filial va xodim',
      'Yangilanishlar bepul',
      'Zaxira nusxa va texnik xizmat',
    ],
    examplesTitle: 'Misollar',
    examples: [
      { children: 50, monthly: 400_000 },
      { children: 60, monthly: 450_000 },
      { children: 70, monthly: 500_000 },
      { children: 80, monthly: 550_000 },
    ],
    annualFormula: 'Yillik = oylik × 12 × 0,75',
    first3: 'Ilk 3 oy — amaldagi narx.',
    note: 'Radix rivojlanishi va yangi imkoniyatlar qo‘shilishi bilan narxlar kelajakda o‘zgarishi mumkin.',
    cta: 'Demo olish',
    error: 'Narxni yuklab bo‘lmadi — qayta urinib ko‘ring.',
    standalone: {
      badge: 'Bir martalik to‘lov',
      title: 'Alohida o‘rnatma — kelishuv asosida',
      text: 'Tizim to‘liq sizniki: o‘z serveringizda, o‘z domeningizda, oylik obunasiz.',
      points: [
        'Ma’lumot sizning serveringizda qoladi',
        'O‘rnatish va sozlashni biz bajaramiz',
        'Yangilanishlar kelishuvga muvofiq',
      ],
      cta: 'Narx so‘rash',
    },
  },
  faq: {
    eyebrow: 'Savollar',
    title: 'Qaror qabul qilish uchun kerakli javoblar.',
    items: [
      {
        q: 'Radix nima?',
        a: 'Xususiy bog‘chalar uchun boshqaruv platformasi: bolalar, guruhlar, davomat, to‘lovlar, qarzdorlik, xodimlar, ish haqi, xarajatlar, ombor va hisobotlar — bitta tizimda.',
      },
      {
        q: 'Kimlar uchun mo‘ljallangan?',
        a: 'O‘zbekistondagi xususiy bog‘chalar va bir nechta filiali bo‘lgan tashkilotlar uchun. Rollar — bog‘cha egasi, direktor, kassir, administrator, tarbiyachi.',
      },
      {
        q: 'Qancha turadi?',
        a: '50 tagacha bola uchun oyiga 400 000 so‘m. Filiallar va xodimlar soni narxga ta’sir qilmaydi.',
      },
      {
        q: '50 tadan ko‘p bola bo‘lsa nima bo‘ladi?',
        a: 'Har boshlangan 10 bola uchun oyiga 50 000 so‘m qo‘shiladi: 60 bola — 450 000, 70 bola — 500 000, 80 bola — 550 000 so‘m.',
      },
      {
        q: 'Yillik to‘lov qanday hisoblanadi?',
        a: 'Oylik narx × 12 × 0,75 — ya’ni 25 % chegirma. 50 bola uchun yillik to‘lov 3 600 000 so‘m.',
      },
      {
        q: 'Demo olish mumkinmi?',
        a: 'Ha. Pastdagi formani to‘ldiring — biz bog‘lanib, tizimni sizning bog‘changiz misolida ko‘rsatamiz.',
      },
      {
        q: 'Ma’lumotlar xavfsizligi qanday ta’minlanadi?',
        a: 'Rollarga asoslangan kirish, tashkilotlar izolyatsiyasi — ilova va ma’lumotlar bazasi darajasida — hamda o‘zgartirib bo‘lmaydigan audit jurnali. Zaxira nusxa muntazam olinadi.',
      },
    ],
  },
  lead: {
    eyebrow: 'Demo',
    title: 'Radix CRM bilan ishlashni boshlang.',
    text: 'Bog‘changiz boshqaruvini soddalashtirish uchun biz bilan bog‘laning.',
    name: 'Ism',
    phone: 'Telefon raqami',
    kindergarten: 'Bog‘cha nomi',
    children: 'Bolalar soni',
    city: 'Shahar / viloyat',
    message: 'Izoh (ixtiyoriy)',
    consent: 'Shaxsiy ma’lumotlarimga Maxfiylik siyosatiga muvofiq ishlov berilishiga roziman.',
    privacy: 'Maxfiylik siyosati',
    submit: 'Demo olish',
    sending: 'Yuborilmoqda…',
    success: 'Rahmat. So‘rovingiz qabul qilindi — tez orada bog‘lanamiz.',
    error: 'So‘rovni yuborib bo‘lmadi. Maydonlarni tekshirib, qayta urinib ko‘ring.',
  },
  final: {
    title: 'Bog‘changizni boshqarishning yangi usuli.',
    text: 'Bitta tizim. To‘liq nazorat.',
    cta: 'Demo olish',
    secondary: 'CRM’ga kirish',
  },
  footer: {
    privacy: 'Maxfiylik siyosati',
    terms: 'Foydalanish shartlari',
    login: 'CRM’ga kirish',
    copyright: '© 2026 Radix CRM',
  },
  seo: {
    title: 'Radix CRM — bog‘changizni boshqarishning barchasi bitta tizimda',
    description:
      'Xususiy bog‘chalar uchun boshqaruv platformasi: bolalar, to‘lovlar, davomat, xodimlar va moliyaviy nazorat. 400 000 so‘m / oy dan.',
  },
}

const ru: Copy = {
  nav: {
    product: 'Продукт',
    capabilities: 'Возможности',
    pricing: 'Цены',
    faq: 'Вопросы',
    login: 'Войти в CRM',
    demo: 'Получить демо',
    menu: 'Меню',
    close: 'Закрыть',
    lang: { uz: 'UZ', ru: 'RU' },
  },
  hero: {
    eyebrow: 'Платформа управления для частных детских садов',
    title: 'Всё управление детским садом — в одной системе.',
    subtitle: 'Дети, оплаты, посещаемость, сотрудники и финансовый контроль — всё в Radix CRM.',
    cta: 'Получить демо',
    secondary: 'Как работает Radix',
    priceFrom: 'от 400 000 сум / мес',
    scroll: 'Вниз',
  },
  demo: {
    note: 'Цифры на экранах — демонстрационные.',
    kpis: [
      { label: 'Активные дети', value: 128, hint: 'в списке' },
      { label: 'Посещаемость сегодня', value: 94, suffix: '%', hint: '120 / 128 отмечено' },
      { label: 'Задолженность', value: 12_450_000, hint: 'по 9 детям' },
      { label: 'Выручка за месяц', value: 86_400_000, hint: 'сентябрь' },
      { label: 'Сотрудники', value: 24, hint: '6 групп' },
    ],
    sidebar: [
      'Панель',
      'Дети',
      'Группы',
      'Оплаты',
      'Должники',
      'Посещаемость',
      'Сотрудники',
      'Склад',
      'Отчёты',
    ],
    org: 'Детский сад «Куёш»',
    today: '18 сентября, четверг',
    chartTitle: 'Динамика выручки',
    months: ['Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен'],
  },
  problem: {
    eyebrow: 'Знакомая ситуация',
    title:
      'То, что руководитель должен контролировать, не должно быть разбросано по разным местам.',
    text: 'Сообщение в Telegram, таблица в Excel, запись в тетради, чек в кассе. Каждое по отдельности верно — но общей картины нет.',
    fragments: [
      {
        kind: 'chat',
        title: 'Группа воспитателей',
        lines: ['Сегодня не пришли 3 ребёнка', 'Кто? — напишу позже'],
      },
      {
        kind: 'sheet',
        title: 'oplaty_sentyabr_final2.xlsx',
        lines: ['Каримов А. · 1 500 000 · ?', 'Расулова М. · 1 500 000 · оплачено'],
      },
      { kind: 'note', title: 'Тетрадь', lines: ['Юсупов — долг 600 тыс.', 'Повар — аванс 400'] },
      {
        kind: 'receipt',
        title: 'Кассовый чек',
        lines: ['Наличные · 1 500 000', '12.09 · без подписи'],
      },
      {
        kind: 'attendance',
        title: 'Лист посещаемости',
        lines: ['Группа «Куёш» · 18/20', 'Дата не указана'],
      },
      {
        kind: 'staff',
        title: 'Сотрудники',
        lines: ['24 человека · 3 без договора', 'Зарплата — в Excel'],
      },
      { kind: 'expense', title: 'Расход', lines: ['Продукты · 2 300 000', 'Чек — в телефоне'] },
    ],
    resolved: 'Одна система',
  },
  oneSystem: {
    eyebrow: 'Одна система',
    title: 'Операционная работа и финансовый контроль — в одной системе.',
    text: 'Каждый модуль делает своё дело и связан с остальными: отметили посещаемость — обновился отчёт, пришла оплата — уменьшился долг.',
    modules: ['Дети', 'Оплаты', 'Посещаемость', 'Сотрудники', 'Склад', 'Расходы', 'Отчёты'],
    links: [
      ['Посещаемость отмечена', 'Отчёт 94 %'],
      ['Оплата принята', 'Долг −1,5 млн'],
      ['Расход со склада', 'Расход +2,3 млн'],
    ],
  },
  modules: {
    eyebrow: 'Возможности',
    title: 'Шесть модулей, которые нужны каждый день.',
    items: [
      {
        id: 'children',
        title: 'Дети и группы',
        text: 'Каждый ребёнок — с профилем, группой, опекуном и тарифом. Фильтр по группам, быстрый поиск, карточка открывается мгновенно.',
        caption: 'Список детей → фильтр по группе → профиль',
      },
      {
        id: 'payments',
        title: 'Оплаты и задолженность',
        text: 'Счёт, оплата, остаток. Список должников считается из леджера — он никогда не расходится с реальностью.',
        caption: 'Оплачено → ожидает → долг',
      },
      {
        id: 'attendance',
        title: 'Посещаемость',
        text: 'Воспитатель отмечает одним касанием, руководитель видит процент. Неотмеченный день — не «отсутствовал», а «не отмечен».',
        caption: 'Посещаемость группы и дневной процент',
      },
      {
        id: 'staff',
        title: 'Сотрудники и зарплата',
        text: 'Должность, роль, ставка, аванс и расчёт за месяц — в одном месте. Кто к чему имеет доступ, решает владелец.',
        caption: 'Список сотрудников · зарплата',
      },
      {
        id: 'inventory',
        title: 'Склад и расходы',
        text: 'Приход, расход, остаток. Расходы по категориям — продукты, коммунальные, ремонт — и они сами попадают в отчёт.',
        caption: 'Остаток уменьшается → появляется расход',
      },
      {
        id: 'reports',
        title: 'Отчёты и контроль',
        text: 'Выручка, расходы, зарплата, задолженность — на одном экране. Нажмите на любую цифру и увидите, откуда она.',
        caption: 'Все показатели на одной панели',
      },
    ],
  },
  deepDive: {
    eyebrow: 'Панель управления',
    title: 'Все цифры, которые должен видеть руководитель, — на одном экране.',
    text: 'Посещаемость сегодня, выручка за месяц, задолженность и сотрудники — сразу после входа. Каждая цифра считается из живых данных.',
    steps: ['Общая картина', 'Посещаемость', 'Задолженность', 'Выручка'],
  },
  roles: {
    eyebrow: 'Для кого Radix?',
    title: 'Каждая роль видит то, что нужно именно ей.',
    text: 'Права основаны на ролях и управляются владельцем организации.',
    items: [
      {
        id: 'owner',
        title: 'Владелец',
        text: 'Контролируйте общее состояние бизнеса.',
        focus: 'Выручка, долги, расходы — по всем филиалам',
      },
      {
        id: 'director',
        title: 'Директор',
        text: 'Управляйте ежедневными операциями из одной системы.',
        focus: 'Посещаемость, группы, сотрудники, задачи на сегодня',
      },
      {
        id: 'cashier',
        title: 'Кассир',
        text: 'Ведите оплаты и задолженность точно.',
        focus: 'Счета, приём оплат, должники',
      },
      {
        id: 'admin',
        title: 'Администратор',
        text: 'Упорядоченно ведите детей, группы и посещаемость.',
        focus: 'Список, профиль, зачисление в группу, посещаемость',
      },
    ],
  },
  workflow: {
    eyebrow: 'Один день с Radix',
    title: 'Один день. Одна система. Точный контроль.',
    text: 'С утра до вечера — каждое действие записывается на своём месте и к вечеру превращается в отчёт.',
    steps: [
      {
        time: '08:00',
        title: 'Посещаемость',
        text: 'Воспитатель отмечает группу — пришли 120 / 128 детей.',
      },
      {
        time: '09:30',
        title: 'Группы',
        text: 'Новый ребёнок зачислен в группу «Юлдузча». Заполненность — 19 / 20.',
      },
      {
        time: '12:00',
        title: 'Оплаты',
        text: 'Кассир принял 3 оплаты — задолженность снизилась до 12 450 000.',
      },
      {
        time: '15:00',
        title: 'Сотрудники',
        text: 'Повару записан аванс. Расчёт за месяц обновился сам.',
      },
      {
        time: '17:00',
        title: 'Отчёты',
        text: 'Руководитель видит итог дня: посещаемость 94 %, выручка, расходы.',
      },
    ],
  },
  finance: {
    eyebrow: 'Финансовый контроль',
    title: 'Знайте, откуда приходят деньги и куда уходят.',
    text: 'Каждый сум — от счёта до оплаты, от расхода до зарплаты — в одном журнале. Баланс считается, а не записывается вручную.',
    metrics: [
      { id: 'revenue', label: 'Начислено', value: 86_400_000, tone: 'neutral' },
      { id: 'payments', label: 'Принятые оплаты', value: 73_950_000, tone: 'in' },
      { id: 'debt', label: 'Задолженность', value: 12_450_000, tone: 'warn' },
      { id: 'expenses', label: 'Расходы', value: 18_300_000, tone: 'out' },
      { id: 'salaries', label: 'Зарплата', value: 31_500_000, tone: 'out' },
      { id: 'balance', label: 'Баланс', value: 24_150_000, tone: 'in' },
    ],
    equation: 'Оплаты − Расходы − Зарплата = Баланс',
  },
  pricing: {
    eyebrow: 'Цены',
    title: 'До 50 детей — 400 000 сум / мес.',
    text: 'Цена зависит только от числа детей. Филиалы и сотрудники — без ограничений.',
    childrenLabel: 'Количество детей',
    childrenUnit: 'детей',
    monthly: 'Ежемесячно',
    annual: 'За год',
    annualBadge: 'экономия 25 %',
    perMonth: '/ мес',
    perYear: '/ год',
    effective: 'равно {amount} в месяц',
    includes: [
      'Все модули',
      'Без ограничений по филиалам и сотрудникам',
      'Обновления бесплатно',
      'Резервные копии и поддержка',
    ],
    examplesTitle: 'Примеры',
    examples: [
      { children: 50, monthly: 400_000 },
      { children: 60, monthly: 450_000 },
      { children: 70, monthly: 500_000 },
      { children: 80, monthly: 550_000 },
    ],
    annualFormula: 'Год = месяц × 12 × 0,75',
    first3: 'Первые 3 месяца — по действующей цене.',
    note: 'По мере развития Radix и появления новых возможностей цены могут измениться.',
    cta: 'Получить демо',
    error: 'Не удалось загрузить цену — попробуйте ещё раз.',
    standalone: {
      badge: 'Разовая оплата',
      title: 'Отдельная установка — по договорённости',
      text: 'Система полностью ваша: на вашем сервере, на вашем домене, без ежемесячной подписки.',
      points: [
        'Данные остаются на вашем сервере',
        'Установку и настройку выполняем мы',
        'Обновления — по договорённости',
      ],
      cta: 'Запросить цену',
    },
  },
  faq: {
    eyebrow: 'Вопросы',
    title: 'Ответы, которые нужны для решения.',
    items: [
      {
        q: 'Что такое Radix?',
        a: 'Платформа управления для частных детских садов: дети, группы, посещаемость, оплаты, задолженность, сотрудники, зарплата, расходы, склад и отчёты — в одной системе.',
      },
      {
        q: 'Для кого она предназначена?',
        a: 'Для частных детских садов в Узбекистане и организаций с несколькими филиалами. Роли — владелец, директор, кассир, администратор, воспитатель.',
      },
      {
        q: 'Сколько стоит?',
        a: 'До 50 детей — 400 000 сум в месяц. Число филиалов и сотрудников на цену не влияет.',
      },
      {
        q: 'Что, если детей больше 50?',
        a: 'За каждые начатые 10 детей добавляется 50 000 сум в месяц: 60 детей — 450 000, 70 — 500 000, 80 — 550 000 сум.',
      },
      {
        q: 'Как считается годовая оплата?',
        a: 'Месячная цена × 12 × 0,75 — то есть скидка 25 %. Для 50 детей год стоит 3 600 000 сум.',
      },
      {
        q: 'Можно получить демо?',
        a: 'Да. Заполните форму ниже — мы свяжемся и покажем систему на примере вашего сада.',
      },
      {
        q: 'Как обеспечивается безопасность данных?',
        a: 'Доступ по ролям, изоляция организаций — на уровне приложения и базы данных — и неизменяемый журнал аудита. Резервные копии делаются регулярно.',
      },
    ],
  },
  lead: {
    eyebrow: 'Демо',
    title: 'Начните работать с Radix CRM.',
    text: 'Свяжитесь с нами, чтобы упростить управление вашим детским садом.',
    name: 'Имя',
    phone: 'Номер телефона',
    kindergarten: 'Название детского сада',
    children: 'Количество детей',
    city: 'Город / область',
    message: 'Комментарий (необязательно)',
    consent:
      'Согласен на обработку персональных данных в соответствии с Политикой конфиденциальности.',
    privacy: 'Политика конфиденциальности',
    submit: 'Получить демо',
    sending: 'Отправляем…',
    success: 'Спасибо. Заявка принята — скоро свяжемся.',
    error: 'Не удалось отправить. Проверьте поля и попробуйте ещё раз.',
  },
  final: {
    title: 'Новый способ управлять детским садом.',
    text: 'Одна система. Полный контроль.',
    cta: 'Получить демо',
    secondary: 'Войти в CRM',
  },
  footer: {
    privacy: 'Политика конфиденциальности',
    terms: 'Условия использования',
    login: 'Войти в CRM',
    copyright: '© 2026 Radix CRM',
  },
  seo: {
    title: 'Radix CRM — всё управление детским садом в одной системе',
    description:
      'Платформа управления для частных детских садов: дети, оплаты, посещаемость, сотрудники и финансовый контроль. От 400 000 сум / мес.',
  },
}

export const copy: Record<Locale, Copy> = { uz, ru }

export const CURRENCY: Record<Locale, string> = { uz: 'so‘m', ru: 'сум' }

export const groupThousands = (value: number) =>
  Math.round(value)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, ' ')

export const money = (value: number | string | undefined, locale: Locale) =>
  value === undefined || value === '' ? '—' : `${groupThousands(Number(value))} ${CURRENCY[locale]}`
