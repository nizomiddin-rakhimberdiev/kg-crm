/**
 * Bosh sahifa matnlari (UZ / RU / EN) — `/uz`, `/ru`, `/en`.
 *
 * Namunaviy ekranlardagi yorliqlar ham shu yerda (`ui`): bo'limlar ichida
 * `locale === 'uz' ? … : …` yo'q, shuning uchun kalitlar tengligi testi
 * uchinchi tilda biror yozuv o'zbekcha qolib ketmaganini kafolatlaydi.
 * Narx raqamlari ADR-12 bilan bir xil (400 000 / 50 bola, +50 000 / 10,
 * yillik −25 %) — kalkulyator esa raqamni backend'dan oladi.
 *
 * Uydirma narsa yo'q: mijoz, statistika, mukofot, sharh — hech biri.
 * UI ichidagi raqamlar NAMUNAVIY va sahifada shunday deb yozilgan.
 */

export type Locale = 'uz' | 'ru' | 'en'

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

/** Namunaviy ekranlardagi qisqa yorliqlar — bo'limlar bo'yicha. */
export interface UiCopy {
  hero: { alert: string; severe: string }
  problem: { wait: string; paid: string; debt: string; receiptAttached: string }
  children: {
    all: string
    age: string
    tariff: string
    guardian: string
    balance: string
    attendance: string
  }
  payments: { paid: string; wait: string; debt: string }
  attendance: { today: string; title: string; present: string }
  staff: {
    director: string
    teacher: string
    cashier: string
    cook: string
    title: string
    payroll: string
    advance: string
    total: string
  }
  inventory: {
    rice: string
    flour: string
    oil: string
    sugar: string
    food: string
    utilities: string
    repair: string
    stock: string
    expenses: string
  }
  deepDive: { last6: string; alert: string; why: string }
  roles: {
    branches: string
    chilonzor: string
    yunusobod: string
    tasks: string
    attendanceMissing: string
    newChildren: string
    today: string
    cookAdvance: string
    acceptedToday: string
    waiting: string
    debt: string
    acceptPayment: string
    septemberInvoice: string
    cash: string
    wait: string
    augustInvoice: string
    debtPill: string
    children: string
    groups: string
    marked: string
    attendanceMarked: string
  }
  workflow: { groups: string; age: string; newChild: string; enrolled: string; capacity: string }
  finance: { inflow: string; outflow: string; unitMonth: string }
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
    /** Til tanlagichning aria yorlig'i. */
    language: string
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
  /**
   * Mijozlar fikri (PLAN 5.7). `items` BO'SH ekan — blok umuman
   * chizilmaydi: to'qima iqtibos ishonchni buzadi, bo'sh joy esa
   * tugallanmagan sayt kabi ko'rinadi.
   */
  testimonials: {
    eyebrow: string
    title: string
    items: { quote: string; name: string; role: string }[]
  }
  /** Aloqa bloki — header va footer (PLAN 5.7). */
  contact: { title: string; telegram: string; email: string; tin: string; call: string }
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
    /** Yuborilgandan keyin: qachon bog'lanishimiz (PLAN 5.7). */
    successNext: string
    /** Kutishni xohlamaganlar uchun — Telegram tugmasi. */
    telegram: string
    error: string
  }
  final: { title: string; text: string; cta: string; secondary: string }
  footer: { privacy: string; terms: string; login: string; copyright: string }
  seo: { title: string; description: string }
  /** Notoʻgʻri manzil sahifasi (PLAN 5.6) — `dist/404.html`. */
  notFound: { title: string; text: string; home: string }
  ui: UiCopy
}

const uz: Copy = {
  nav: {
    product: 'Mahsulot',
    capabilities: 'Imkoniyatlar',
    pricing: 'Narxlar',
    faq: 'Savollar',
    login: 'CRMʼga kirish',
    demo: 'Demo olish',
    menu: 'Menyu',
    close: 'Yopish',
    language: 'Til',
    lang: { uz: 'UZ', ru: 'RU', en: 'EN' },
  },
  hero: {
    eyebrow: 'Xususiy bogʻchalar uchun boshqaruv platformasi',
    title: 'Bogʻchangizni boshqarishning barchasi — bitta tizimda.',
    subtitle: 'Bolalar, toʻlovlar, davomat, xodimlar va moliyaviy nazorat — hammasi Radix CRMʼda.',
    cta: 'Demo olish',
    secondary: 'Radix qanday ishlaydi',
    priceFrom: '400 000 soʻm / oy dan',
    scroll: 'Pastga',
  },
  demo: {
    note: 'Ekranlardagi raqamlar — namunaviy maʼlumot.',
    kpis: [
      { label: 'Faol bolalar', value: 128, hint: 'roʻyxatda' },
      { label: 'Bugungi davomat', value: 94, suffix: '%', hint: '120 / 128 belgilangan' },
      { label: 'Qarzdorlik', value: 12_450_000, hint: '9 ta bola boʻyicha' },
      { label: 'Oylik tushum', value: 86_400_000, hint: 'sentabr' },
      { label: 'Xodimlar', value: 24, hint: '6 guruh' },
    ],
    sidebar: [
      'Boshqaruv paneli',
      'Bolalar',
      'Guruhlar',
      'Toʻlovlar',
      'Qarzdorlar',
      'Davomat',
      'Xodimlar',
      'Ombor',
      'Hisobotlar',
    ],
    org: 'Quyosh bogʻchasi',
    today: '18-sentabr, payshanba',
    chartTitle: 'Tushum dinamikasi',
    months: ['Apr', 'May', 'Iyn', 'Iyl', 'Avg', 'Sen'],
  },
  problem: {
    eyebrow: 'Tanish holat',
    title: 'Rahbar nazorat qilishi kerak boʻlgan ishlar turli joylarga sochilib ketmasin.',
    text: 'Telegramʼdagi xabar, Excelʼdagi jadval, daftardagi yozuv, kassadagi chek. Har biri toʻgʻri — lekin umumiy manzara yoʻq.',
    fragments: [
      {
        kind: 'chat',
        title: 'Tarbiyachilar guruhi',
        lines: ['Bugun 3 bola kelmadi', 'Kimlar? — keyin yozaman'],
      },
      {
        kind: 'sheet',
        title: 'tolovlar_sentabr_final2.xlsx',
        lines: ['Karimov A. · 1 500 000 · ?', 'Rasulova M. · 1 500 000 · toʻlandi'],
      },
      { kind: 'note', title: 'Daftar', lines: ['Yusupov — 600 ming qarz', 'Oshpaz — avans 400'] },
      { kind: 'receipt', title: 'Kassa cheki', lines: ['Naqd · 1 500 000', '12.09 · imzo yoʻq'] },
      {
        kind: 'attendance',
        title: 'Davomat varagʻi',
        lines: ['Quyosh guruhi · 18/20', 'Sana yozilmagan'],
      },
      {
        kind: 'staff',
        title: 'Xodimlar',
        lines: ['24 kishi · 3 ta shartnoma yoʻq', 'Ish haqi — Excelʼda'],
      },
      { kind: 'expense', title: 'Xarajat', lines: ['Oziq-ovqat · 2 300 000', 'Chek — telefonda'] },
    ],
    resolved: 'Bitta tizim',
  },
  oneSystem: {
    eyebrow: 'Bitta tizim',
    title: 'Operatsion ish va moliyaviy nazorat — bir tizimda.',
    text: 'Har bir modul oʻz ishini qiladi va bir-biri bilan bogʻlangan: davomat belgilansa — hisobot yangilanadi, toʻlov kirsa — qarzdorlik kamayadi.',
    modules: ['Bolalar', 'Toʻlovlar', 'Davomat', 'Xodimlar', 'Ombor', 'Xarajatlar', 'Hisobotlar'],
    links: [
      ['Davomat belgilandi', 'Hisobot 94 %'],
      ['Toʻlov kirdi', 'Qarz −1,5 mln'],
      ['Ombor chiqimi', 'Xarajat +2,3 mln'],
    ],
  },
  modules: {
    eyebrow: 'Imkoniyatlar',
    title: 'Har kuni kerak boʻladigan olti modul.',
    items: [
      {
        id: 'children',
        title: 'Bolalar va guruhlar',
        text: 'Har bir bola — profil, guruh, vasiy va tarif bilan. Guruhlar boʻyicha filtr, tez qidiruv, bir zumda ochiladigan karta.',
        caption: 'Bolalar roʻyxati → guruh filtri → profil',
      },
      {
        id: 'payments',
        title: 'Toʻlovlar va qarzdorlik',
        text: 'Hisob-faktura, toʻlov, qoldiq. Qarzdorlar roʻyxati ledgerʼdan hisoblanadi — u hech qachon haqiqatdan ajralmaydi.',
        caption: 'Toʻlangan → kutilmoqda → qarz',
      },
      {
        id: 'attendance',
        title: 'Davomat',
        text: 'Tarbiyachi bir chertishda belgilaydi, rahbar foizni koʻradi. Yozilmagan kun — «yoʻq» emas, «belgilanmagan».',
        caption: 'Guruh davomati va kunlik foiz',
      },
      {
        id: 'staff',
        title: 'Xodimlar va ish haqi',
        text: 'Lavozim, rol, stavka, avans va oylik hisob-kitob — bitta joyda. Kim nimaga kirishini tashkilot egasi belgilaydi.',
        caption: 'Xodimlar roʻyxati · ish haqi',
      },
      {
        id: 'inventory',
        title: 'Ombor va xarajatlar',
        text: 'Kirim, chiqim, qoldiq. Xarajat kategoriyalar boʻyicha — oziq-ovqat, kommunal, taʼmir — va u hisobotga oʻzi tushadi.',
        caption: 'Qoldiq kamayadi → xarajat paydo boʻladi',
      },
      {
        id: 'reports',
        title: 'Hisobotlar va nazorat',
        text: 'Tushum, xarajat, ish haqi, qarzdorlik — bir ekranda. Har bir raqamni bosib, uning qayerdan kelganini koʻrasiz.',
        caption: 'Barcha koʻrsatkichlar bitta panelda',
      },
    ],
  },
  deepDive: {
    eyebrow: 'Boshqaruv paneli',
    title: 'Rahbar koʻrishi kerak boʻlgan barcha raqamlar — bir ekranda.',
    text: 'Bugungi davomat, oylik tushum, qarzdorlik va xodimlar — kirishingiz bilan. Har bir raqam jonli maʼlumotdan hisoblanadi.',
    steps: ['Umumiy holat', 'Davomat', 'Qarzdorlik', 'Tushum'],
  },
  roles: {
    eyebrow: 'Radix kimlar uchun?',
    title: 'Har bir rol oʻziga kerak narsani koʻradi.',
    text: 'Ruxsatlar rollarga asoslangan va tashkilot egasi tomonidan boshqariladi.',
    items: [
      {
        id: 'owner',
        title: 'Bogʻcha egasi',
        text: 'Biznesingizning umumiy holatini nazorat qiling.',
        focus: 'Tushum, qarzdorlik, xarajat — barcha filiallar boʻyicha',
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
        text: 'Toʻlovlar va qarzdorlikni aniq yuriting.',
        focus: 'Hisob-faktura, toʻlov qabul, qarzdorlar',
      },
      {
        id: 'admin',
        title: 'Administrator',
        text: 'Bolalar, guruhlar va davomatni tartibli boshqaring.',
        focus: 'Roʻyxat, profil, guruhga biriktirish, davomat',
      },
    ],
  },
  workflow: {
    eyebrow: 'Radix bilan bir kun',
    title: 'Bir kun. Bitta tizim. Aniq nazorat.',
    text: 'Ertalabdan kechgacha — har bir amal oʻz joyida yoziladi va kechqurun hisobotga aylanadi.',
    steps: [
      {
        time: '08:00',
        title: 'Davomat',
        text: 'Tarbiyachi guruhni belgilaydi — 120 / 128 bola keldi.',
      },
      {
        time: '09:30',
        title: 'Guruhlar',
        text: 'Yangi bola «Yulduzcha» guruhiga biriktirildi. Sigʻim — 19 / 20.',
      },
      {
        time: '12:00',
        title: 'Toʻlovlar',
        text: 'Kassir 3 ta toʻlov qabul qildi — qarzdorlik 12 450 000 ga tushdi.',
      },
      {
        time: '15:00',
        title: 'Xodimlar',
        text: 'Oshpazga avans yozildi. Oylik hisob-kitob oʻzi yangilandi.',
      },
      {
        time: '17:00',
        title: 'Hisobotlar',
        text: 'Rahbar kun yakunini koʻradi: davomat 94 %, tushum, xarajat.',
      },
    ],
  },
  finance: {
    eyebrow: 'Moliyaviy nazorat',
    title: 'Pul qayerdan kelayotganini va qayerga ketayotganini biling.',
    text: 'Har bir soʻm — hisob-fakturadan toʻlovgacha, xarajatdan ish haqigacha — bitta jurnalda. Balans hisoblanadi, qoʻlda yozilmaydi.',
    metrics: [
      { id: 'revenue', label: 'Hisoblangan tushum', value: 86_400_000, tone: 'neutral' },
      { id: 'payments', label: 'Qabul qilingan toʻlovlar', value: 73_950_000, tone: 'in' },
      { id: 'debt', label: 'Qarzdorlik', value: 12_450_000, tone: 'warn' },
      { id: 'expenses', label: 'Xarajatlar', value: 18_300_000, tone: 'out' },
      { id: 'salaries', label: 'Ish haqi', value: 31_500_000, tone: 'out' },
      { id: 'balance', label: 'Balans', value: 24_150_000, tone: 'in' },
    ],
    equation: 'Toʻlovlar − Xarajatlar − Ish haqi = Balans',
  },
  pricing: {
    eyebrow: 'Narxlar',
    title: '50 tagacha bola uchun — 400 000 soʻm / oy.',
    text: 'Narx faqat bolalar soniga bogʻliq. Filiallar va xodimlar soni cheklanmagan.',
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
    note: 'Radix rivojlanishi va yangi imkoniyatlar qoʻshilishi bilan narxlar kelajakda oʻzgarishi mumkin.',
    cta: 'Demo olish',
    error: 'Narxni yuklab boʻlmadi — qayta urinib koʻring.',
    standalone: {
      badge: 'Bir martalik toʻlov',
      title: 'Alohida oʻrnatma — kelishuv asosida',
      text: 'Tizim toʻliq sizniki: oʻz serveringizda, oʻz domeningizda, oylik obunasiz.',
      points: [
        'Maʼlumot sizning serveringizda qoladi',
        'Oʻrnatish va sozlashni biz bajaramiz',
        'Yangilanishlar kelishuvga muvofiq',
      ],
      cta: 'Narx soʻrash',
    },
  },
  faq: {
    eyebrow: 'Savollar',
    title: 'Qaror qabul qilish uchun kerakli javoblar.',
    items: [
      {
        q: 'Radix nima?',
        a: 'Xususiy bogʻchalar uchun boshqaruv platformasi: bolalar, guruhlar, davomat, toʻlovlar, qarzdorlik, xodimlar, ish haqi, xarajatlar, ombor va hisobotlar — bitta tizimda.',
      },
      {
        q: 'Kimlar uchun moʻljallangan?',
        a: 'Oʻzbekistondagi xususiy bogʻchalar va bir nechta filiali boʻlgan tashkilotlar uchun. Rollar — bogʻcha egasi, direktor, kassir, administrator, tarbiyachi.',
      },
      {
        q: 'Qancha turadi?',
        a: '50 tagacha bola uchun oyiga 400 000 soʻm. Filiallar va xodimlar soni narxga taʼsir qilmaydi.',
      },
      {
        q: '50 tadan koʻp bola boʻlsa nima boʻladi?',
        a: 'Har boshlangan 10 bola uchun oyiga 50 000 soʻm qoʻshiladi: 60 bola — 450 000, 70 bola — 500 000, 80 bola — 550 000 soʻm.',
      },
      {
        q: 'Yillik toʻlov qanday hisoblanadi?',
        a: 'Oylik narx × 12 × 0,75 — yaʼni 25 % chegirma. 50 bola uchun yillik toʻlov 3 600 000 soʻm.',
      },
      {
        q: 'Demo olish mumkinmi?',
        a: 'Ha. Pastdagi formani toʻldiring — biz bogʻlanib, tizimni sizning bogʻchangiz misolida koʻrsatamiz.',
      },
      {
        q: 'Maʼlumotlar xavfsizligi qanday taʼminlanadi?',
        a: 'Rollarga asoslangan kirish, tashkilotlar izolyatsiyasi — ilova va maʼlumotlar bazasi darajasida — hamda oʻzgartirib boʻlmaydigan audit jurnali. Zaxira nusxa muntazam olinadi.',
      },
    ],
  },
  lead: {
    eyebrow: 'Demo',
    title: 'Radix CRM bilan ishlashni boshlang.',
    text: 'Bogʻchangiz boshqaruvini soddalashtirish uchun biz bilan bogʻlaning.',
    name: 'Ism',
    phone: 'Telefon raqami',
    kindergarten: 'Bogʻcha nomi',
    children: 'Bolalar soni',
    city: 'Shahar / viloyat',
    message: 'Izoh (ixtiyoriy)',
    consent: 'Shaxsiy maʼlumotlarimga Maxfiylik siyosatiga muvofiq ishlov berilishiga roziman.',
    privacy: 'Maxfiylik siyosati',
    submit: 'Demo olish',
    sending: 'Yuborilmoqda…',
    success: 'Rahmat! Soʻrovingiz qabul qilindi.',
    successNext: '24 soat ichida bogʻlanamiz.',
    telegram: 'Telegramda yozish',
    error: 'Soʻrovni yuborib boʻlmadi. Maydonlarni tekshirib, qayta urinib koʻring.',
  },
  final: {
    title: 'Bogʻchangizni boshqarishning yangi usuli.',
    text: 'Bitta tizim. Toʻliq nazorat.',
    cta: 'Demo olish',
    secondary: 'CRMʼga kirish',
  },
  footer: {
    privacy: 'Maxfiylik siyosati',
    terms: 'Foydalanish shartlari',
    login: 'CRMʼga kirish',
    copyright: '© 2026 Radix CRM',
  },
  testimonials: { eyebrow: 'Mijozlar fikri', title: 'Radix bilan ishlayotgan bogʻchalar', items: [] },
  contact: {
    title: 'Aloqa',
    telegram: 'Telegram',
    email: 'Email',
    tin: 'STIR',
    call: 'Qoʻngʻiroq qilish',
  },
  notFound: {
    title: 'Bu sahifa topilmadi',
    text: 'Manzil notoʻgʻri yozilgan yoki sahifa koʻchirilgan.',
    home: 'Bosh sahifa',
  },
  seo: {
    title: 'Radix CRM — bogʻchangizni boshqarishning barchasi bitta tizimda',
    description:
      'Xususiy bogʻchalar uchun boshqaruv platformasi: bolalar, toʻlovlar, davomat, xodimlar va moliyaviy nazorat. 400 000 soʻm / oy dan.',
  },
  ui: {
    hero: { alert: '9 ta bola boʻyicha toʻlov 15 kundan ortiq kechikmoqda', severe: 'Jiddiy' },
    problem: {
      wait: 'kutilmoqda',
      paid: 'toʻlandi',
      debt: 'qarz',
      receiptAttached: 'chek biriktirilgan',
    },
    children: {
      all: 'Hammasi',
      age: 'yosh',
      tariff: 'Tarif',
      guardian: 'Vasiy',
      balance: 'Balans',
      attendance: 'Davomat',
    },
    payments: { paid: 'toʻlandi', wait: 'kutilmoqda', debt: 'qarz' },
    attendance: { today: 'bugun', title: 'Davomat', present: 'kelgan' },
    staff: {
      director: 'Direktor',
      teacher: 'Tarbiyachi',
      cashier: 'Kassir',
      cook: 'Oshpaz',
      title: 'Xodimlar · 24',
      payroll: 'Sentabr ish haqi',
      advance: 'avans 400 000',
      total: 'Jami (24 xodim)',
    },
    inventory: {
      rice: 'Guruch',
      flour: 'Un',
      oil: 'Yog‘',
      sugar: 'Shakar',
      food: 'Oziq-ovqat',
      utilities: 'Kommunal',
      repair: 'Taʼmir',
      stock: 'Ombor qoldigʻi',
      expenses: 'Xarajatlar · sentabr',
    },
    deepDive: {
      last6: 'oxirgi 6 oy',
      alert: '9 ta bola boʻyicha toʻlov 15 kundan ortiq kechikmoqda',
      why: 'Nega?',
    },
    roles: {
      branches: 'Filiallar',
      chilonzor: 'Chilonzor',
      yunusobod: 'Yunusobod',
      tasks: 'Bugungi vazifalar',
      attendanceMissing: 'Kamalak guruhi davomati belgilanmagan',
      newChildren: '2 ta yangi bola — guruhga biriktirish',
      today: 'bugun',
      cookAdvance: 'Oshpaz — avans soʻrovi',
      acceptedToday: 'Bugun qabul qilindi',
      waiting: 'Kutilmoqda',
      debt: 'Qarzdorlik',
      acceptPayment: 'Toʻlov qabul qilish',
      septemberInvoice: 'Sentabr · 1 500 000',
      cash: 'naqd',
      wait: 'kutilmoqda',
      augustInvoice: 'Avgust · 600 000',
      debtPill: 'qarz',
      children: 'Bolalar',
      groups: 'Guruhlar',
      marked: 'Belgilangan',
      attendanceMarked: 'davomat belgilangan',
    },
    workflow: {
      groups: 'Guruhlar',
      age: '3–4 yosh',
      newChild: 'Yangi bola',
      enrolled: 'Yulduzcha guruhiga biriktirildi',
      capacity: 'Sigʻim 19 / 20',
    },
    finance: { inflow: 'Kirim', outflow: 'Chiqim', unitMonth: 'soʻm · sentabr' },
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
    language: 'Язык',
    lang: { uz: 'UZ', ru: 'RU', en: 'EN' },
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
    success: 'Спасибо! Заявка принята.',
    successNext: 'Свяжемся с вами в течение 24 часов.',
    telegram: 'Написать в Telegram',
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
  testimonials: { eyebrow: 'Отзывы', title: 'Детские сады, которые работают с Radix', items: [] },
  contact: {
    title: 'Контакты',
    telegram: 'Telegram',
    email: 'Email',
    tin: 'ИНН',
    call: 'Позвонить',
  },
  notFound: {
    title: 'Страница не найдена',
    text: 'Адрес набран с ошибкой или страница перенесена.',
    home: 'На главную',
  },
  seo: {
    title: 'Radix CRM — всё управление детским садом в одной системе',
    description:
      'Платформа управления для частных детских садов: дети, оплаты, посещаемость, сотрудники и финансовый контроль. От 400 000 сум / мес.',
  },
  ui: {
    hero: { alert: 'По 9 детям оплата задерживается более 15 дней', severe: 'Серьёзно' },
    problem: { wait: 'ожидает', paid: 'оплачено', debt: 'долг', receiptAttached: 'чек приложен' },
    children: {
      all: 'Все',
      age: 'года',
      tariff: 'Тариф',
      guardian: 'Опекун',
      balance: 'Баланс',
      attendance: 'Посещ.',
    },
    payments: { paid: 'оплачено', wait: 'ожидает', debt: 'долг' },
    attendance: { today: 'сегодня', title: 'Посещаемость', present: 'пришли' },
    staff: {
      director: 'Директор',
      teacher: 'Воспитатель',
      cashier: 'Кассир',
      cook: 'Повар',
      title: 'Сотрудники · 24',
      payroll: 'Зарплата за сентябрь',
      advance: 'аванс 400 000',
      total: 'Итого (24 сотрудника)',
    },
    inventory: {
      rice: 'Рис',
      flour: 'Мука',
      oil: 'Масло',
      sugar: 'Сахар',
      food: 'Продукты',
      utilities: 'Коммунальные',
      repair: 'Ремонт',
      stock: 'Остаток на складе',
      expenses: 'Расходы · сентябрь',
    },
    deepDive: {
      last6: 'последние 6 мес.',
      alert: 'По 9 детям оплата задерживается более 15 дней',
      why: 'Почему?',
    },
    roles: {
      branches: 'Филиалы',
      chilonzor: 'Чиланзар',
      yunusobod: 'Юнусабад',
      tasks: 'Задачи на сегодня',
      attendanceMissing: 'Группа Kamalak — посещаемость не отмечена',
      newChildren: '2 новых ребёнка — зачислить в группу',
      today: 'сегодня',
      cookAdvance: 'Повар — запрос аванса',
      acceptedToday: 'Принято сегодня',
      waiting: 'Ожидает',
      debt: 'Долг',
      acceptPayment: 'Приём оплаты',
      septemberInvoice: 'Сентябрь · 1 500 000',
      cash: 'наличные',
      wait: 'ожидает',
      augustInvoice: 'Август · 600 000',
      debtPill: 'долг',
      children: 'Дети',
      groups: 'Группы',
      marked: 'Отмечено',
      attendanceMarked: 'посещаемость отмечена',
    },
    workflow: {
      groups: 'Группы',
      age: '3–4 года',
      newChild: 'Новый ребёнок',
      enrolled: 'Зачислена в группу Yulduzcha',
      capacity: 'Заполненность 19 / 20',
    },
    finance: { inflow: 'Приход', outflow: 'Расход', unitMonth: 'сум · сентябрь' },
  },
}

const en: Copy = {
  nav: {
    product: 'Product',
    capabilities: 'Capabilities',
    pricing: 'Pricing',
    faq: 'FAQ',
    login: 'Sign in to CRM',
    demo: 'Get a demo',
    menu: 'Menu',
    close: 'Close',
    language: 'Language',
    lang: { uz: 'UZ', ru: 'RU', en: 'EN' },
  },
  hero: {
    eyebrow: 'A management platform for private kindergartens',
    title: 'Everything to run your kindergarten — in one system.',
    subtitle: 'Children, payments, attendance, staff and financial control — all in Radix CRM.',
    cta: 'Get a demo',
    secondary: 'How Radix works',
    priceFrom: 'from 400 000 UZS / month',
    scroll: 'Scroll',
  },
  demo: {
    note: 'Numbers on the screens are sample data.',
    kpis: [
      { label: 'Active children', value: 128, hint: 'enrolled' },
      { label: 'Attendance today', value: 94, suffix: '%', hint: '120 / 128 marked' },
      { label: 'Overdue', value: 12_450_000, hint: 'across 9 children' },
      { label: 'Monthly revenue', value: 86_400_000, hint: 'September' },
      { label: 'Staff', value: 24, hint: '6 groups' },
    ],
    sidebar: [
      'Dashboard',
      'Children',
      'Groups',
      'Payments',
      'Debtors',
      'Attendance',
      'Staff',
      'Inventory',
      'Reports',
    ],
    org: 'Quyosh kindergarten',
    today: 'Thursday, 18 September',
    chartTitle: 'Revenue trend',
    months: ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep'],
  },
  problem: {
    eyebrow: 'A familiar picture',
    title: 'What a director has to keep track of shouldn’t be scattered across ten places.',
    text: 'A message in Telegram, a table in Excel, a note in a ledger book, a receipt at the till. Each one is correct — but there is no overall picture.',
    fragments: [
      {
        kind: 'chat',
        title: 'Teachers’ group chat',
        lines: ['3 children absent today', 'Who? — will write later'],
      },
      {
        kind: 'sheet',
        title: 'payments_september_final2.xlsx',
        lines: ['Karimov A. · 1 500 000 · ?', 'Rasulova M. · 1 500 000 · paid'],
      },
      { kind: 'note', title: 'Notebook', lines: ['Yusupov — owes 600k', 'Cook — advance 400'] },
      {
        kind: 'receipt',
        title: 'Cash receipt',
        lines: ['Cash · 1 500 000', '12.09 · no signature'],
      },
      {
        kind: 'attendance',
        title: 'Attendance sheet',
        lines: ['Quyosh group · 18/20', 'No date written'],
      },
      {
        kind: 'staff',
        title: 'Staff',
        lines: ['24 people · 3 without a contract', 'Payroll — in Excel'],
      },
      { kind: 'expense', title: 'Expense', lines: ['Food · 2 300 000', 'Receipt — on a phone'] },
    ],
    resolved: 'One system',
  },
  oneSystem: {
    eyebrow: 'One system',
    title: 'Daily operations and financial control — in one system.',
    text: 'Each module does its own job, and they are connected: attendance is marked — the report updates; a payment comes in — the debt goes down.',
    modules: ['Children', 'Payments', 'Attendance', 'Staff', 'Inventory', 'Expenses', 'Reports'],
    links: [
      ['Attendance marked', 'Report 94 %'],
      ['Payment received', 'Debt −1.5 M'],
      ['Stock issued', 'Expense +2.3 M'],
    ],
  },
  modules: {
    eyebrow: 'Capabilities',
    title: 'Six modules you need every day.',
    items: [
      {
        id: 'children',
        title: 'Children and groups',
        text: 'Every child has a profile, a group, a guardian and a plan. Filter by group, search instantly, open a card in one click.',
        caption: 'Children list → group filter → profile',
      },
      {
        id: 'payments',
        title: 'Payments and debt',
        text: 'Invoices, payments, balance. The debtors list is computed from the ledger — it never drifts from the truth.',
        caption: 'Paid → pending → overdue',
      },
      {
        id: 'attendance',
        title: 'Attendance',
        text: 'A teacher marks it with one tap, the director sees the percentage. A day that wasn’t recorded is “not marked”, not “absent”.',
        caption: 'Group attendance and the daily rate',
      },
      {
        id: 'staff',
        title: 'Staff and payroll',
        text: 'Position, role, rate, advances and the monthly calculation — in one place. The owner decides who has access to what.',
        caption: 'Staff list · payroll',
      },
      {
        id: 'inventory',
        title: 'Inventory and expenses',
        text: 'Receipts, issues, stock on hand. Expenses by category — food, utilities, repairs — flow into the report on their own.',
        caption: 'Stock goes down → an expense appears',
      },
      {
        id: 'reports',
        title: 'Reports and control',
        text: 'Revenue, expenses, payroll, debt — on one screen. Click any number to see where it came from.',
        caption: 'All indicators in one dashboard',
      },
    ],
  },
  deepDive: {
    eyebrow: 'Dashboard',
    title: 'Every number the director needs — on one screen.',
    text: 'Today’s attendance, monthly revenue, debt and staff — the moment you sign in. Every number is calculated from live data.',
    steps: ['Overview', 'Attendance', 'Debt', 'Revenue'],
  },
  roles: {
    eyebrow: 'Who is Radix for?',
    title: 'Every role sees exactly what it needs.',
    text: 'Permissions are role-based and managed by the organization owner.',
    items: [
      {
        id: 'owner',
        title: 'Kindergarten owner',
        text: 'Keep an eye on the overall state of your business.',
        focus: 'Revenue, debt, expenses — across all branches',
      },
      {
        id: 'director',
        title: 'Director',
        text: 'Run daily operations from one system.',
        focus: 'Attendance, groups, staff, today’s tasks',
      },
      {
        id: 'cashier',
        title: 'Cashier',
        text: 'Keep payments and debt accurate.',
        focus: 'Invoices, receiving payments, debtors',
      },
      {
        id: 'admin',
        title: 'Administrator',
        text: 'Keep children, groups and attendance in order.',
        focus: 'Lists, profiles, group assignment, attendance',
      },
    ],
  },
  workflow: {
    eyebrow: 'A day with Radix',
    title: 'One day. One system. Clear control.',
    text: 'From morning to evening — every action is recorded where it belongs and becomes a report by the end of the day.',
    steps: [
      {
        time: '08:00',
        title: 'Attendance',
        text: 'The teacher marks the group — 120 of 128 children are in.',
      },
      {
        time: '09:30',
        title: 'Groups',
        text: 'A new child is assigned to the “Yulduzcha” group. Capacity — 19 / 20.',
      },
      {
        time: '12:00',
        title: 'Payments',
        text: 'The cashier receives 3 payments — debt drops to 12 450 000.',
      },
      {
        time: '15:00',
        title: 'Staff',
        text: 'An advance is recorded for the cook. The monthly payroll updates itself.',
      },
      {
        time: '17:00',
        title: 'Reports',
        text: 'The director sees the day’s summary: attendance 94 %, revenue, expenses.',
      },
    ],
  },
  finance: {
    eyebrow: 'Financial control',
    title: 'Know where the money comes from and where it goes.',
    text: 'Every sum — from invoice to payment, from expense to payroll — in one ledger. The balance is calculated, never typed by hand.',
    metrics: [
      { id: 'revenue', label: 'Invoiced revenue', value: 86_400_000, tone: 'neutral' },
      { id: 'payments', label: 'Payments received', value: 73_950_000, tone: 'in' },
      { id: 'debt', label: 'Overdue', value: 12_450_000, tone: 'warn' },
      { id: 'expenses', label: 'Expenses', value: 18_300_000, tone: 'out' },
      { id: 'salaries', label: 'Payroll', value: 31_500_000, tone: 'out' },
      { id: 'balance', label: 'Balance', value: 24_150_000, tone: 'in' },
    ],
    equation: 'Payments − Expenses − Payroll = Balance',
  },
  pricing: {
    eyebrow: 'Pricing',
    title: 'Up to 50 children — 400 000 UZS / month.',
    text: 'The price depends only on the number of children. Branches and staff are unlimited.',
    childrenLabel: 'Number of children',
    childrenUnit: 'children',
    monthly: 'Monthly',
    annual: 'Annual',
    annualBadge: 'Save 25 %',
    perMonth: '/ month',
    perYear: '/ year',
    effective: 'equals {amount} per month',
    includes: [
      'All modules',
      'Unlimited branches and staff',
      'Free updates',
      'Backups and technical support',
    ],
    examplesTitle: 'Examples',
    examples: [
      { children: 50, monthly: 400_000 },
      { children: 60, monthly: 450_000 },
      { children: 70, monthly: 500_000 },
      { children: 80, monthly: 550_000 },
    ],
    annualFormula: 'Annual = monthly × 12 × 0.75',
    first3: 'First 3 months — at the current price.',
    note: 'As Radix grows and new capabilities are added, prices may change in the future.',
    cta: 'Get a demo',
    error: 'Couldn’t load the price — please try again.',
    standalone: {
      badge: 'One-time payment',
      title: 'Self-hosted installation — by agreement',
      text: 'The system is fully yours: on your own server, on your own domain, with no monthly subscription.',
      points: [
        'Your data stays on your server',
        'We handle installation and setup',
        'Updates by agreement',
      ],
      cta: 'Request a quote',
    },
  },
  faq: {
    eyebrow: 'FAQ',
    title: 'The answers you need to decide.',
    items: [
      {
        q: 'What is Radix?',
        a: 'A management platform for private kindergartens: children, groups, attendance, payments, debt, staff, payroll, expenses, inventory and reports — in one system.',
      },
      {
        q: 'Who is it for?',
        a: 'Private kindergartens in Uzbekistan and organizations with several branches. Roles — kindergarten owner, director, cashier, administrator, teacher.',
      },
      {
        q: 'How much does it cost?',
        a: '400 000 UZS per month for up to 50 children. The number of branches and staff doesn’t affect the price.',
      },
      {
        q: 'What if there are more than 50 children?',
        a: 'Every started block of 10 children adds 50 000 UZS per month: 60 children — 450 000, 70 — 500 000, 80 — 550 000 UZS.',
      },
      {
        q: 'How is the annual payment calculated?',
        a: 'Monthly price × 12 × 0.75 — a 25 % discount. For 50 children the annual payment is 3 600 000 UZS.',
      },
      {
        q: 'Can I get a demo?',
        a: 'Yes. Fill in the form below — we’ll get in touch and walk you through the system using your kindergarten as the example.',
      },
      {
        q: 'How is data security ensured?',
        a: 'Role-based access, organization isolation — at the application and database level — and an immutable audit log. Backups are taken regularly.',
      },
    ],
  },
  lead: {
    eyebrow: 'Demo',
    title: 'Start working with Radix CRM.',
    text: 'Get in touch to simplify the management of your kindergarten.',
    name: 'Name',
    phone: 'Phone number',
    kindergarten: 'Kindergarten name',
    children: 'Number of children',
    city: 'City / region',
    message: 'Comment (optional)',
    consent: 'I agree to the processing of my personal data in accordance with the Privacy Policy.',
    privacy: 'Privacy Policy',
    submit: 'Get a demo',
    sending: 'Sending…',
    success: 'Thank you! Your request has been received.',
    successNext: 'We will contact you within 24 hours.',
    telegram: 'Message us on Telegram',
    error: 'Couldn’t send the request. Check the fields and try again.',
  },
  final: {
    title: 'A new way to run your kindergarten.',
    text: 'One system. Full control.',
    cta: 'Get a demo',
    secondary: 'Sign in to CRM',
  },
  footer: {
    privacy: 'Privacy Policy',
    terms: 'Terms of Use',
    login: 'Sign in to CRM',
    copyright: '© 2026 Radix CRM',
  },
  testimonials: { eyebrow: 'Testimonials', title: 'Kindergartens that work with Radix', items: [] },
  contact: {
    title: 'Contact',
    telegram: 'Telegram',
    email: 'Email',
    tin: 'TIN',
    call: 'Call',
  },
  notFound: {
    title: 'Page not found',
    text: 'The address is mistyped or the page has moved.',
    home: 'Home page',
  },
  seo: {
    title: 'Radix CRM — everything to run your kindergarten in one system',
    description:
      'A management platform for private kindergartens: children, payments, attendance, staff and financial control. From 400 000 UZS / month.',
  },
  ui: {
    hero: { alert: 'Payments for 9 children are more than 15 days overdue', severe: 'Serious' },
    problem: {
      wait: 'pending',
      paid: 'paid',
      debt: 'overdue',
      receiptAttached: 'receipt attached',
    },
    children: {
      all: 'All',
      age: 'yrs',
      tariff: 'Plan',
      guardian: 'Guardian',
      balance: 'Balance',
      attendance: 'Attend.',
    },
    payments: { paid: 'paid', wait: 'pending', debt: 'overdue' },
    attendance: { today: 'today', title: 'Attendance', present: 'present' },
    staff: {
      director: 'Director',
      teacher: 'Teacher',
      cashier: 'Cashier',
      cook: 'Cook',
      title: 'Staff · 24',
      payroll: 'September payroll',
      advance: 'advance 400 000',
      total: 'Total (24 staff)',
    },
    inventory: {
      rice: 'Rice',
      flour: 'Flour',
      oil: 'Oil',
      sugar: 'Sugar',
      food: 'Food',
      utilities: 'Utilities',
      repair: 'Repairs',
      stock: 'Stock on hand',
      expenses: 'Expenses · September',
    },
    deepDive: {
      last6: 'last 6 months',
      alert: 'Payments for 9 children are more than 15 days overdue',
      why: 'Why?',
    },
    roles: {
      branches: 'Branches',
      chilonzor: 'Chilonzor',
      yunusobod: 'Yunusobod',
      tasks: 'Today’s tasks',
      attendanceMissing: 'Kamalak group — attendance not marked',
      newChildren: '2 new children — assign to a group',
      today: 'today',
      cookAdvance: 'Cook — advance request',
      acceptedToday: 'Received today',
      waiting: 'Pending',
      debt: 'Overdue',
      acceptPayment: 'Receive payment',
      septemberInvoice: 'September · 1 500 000',
      cash: 'cash',
      wait: 'pending',
      augustInvoice: 'August · 600 000',
      debtPill: 'overdue',
      children: 'Children',
      groups: 'Groups',
      marked: 'Marked',
      attendanceMarked: 'attendance marked',
    },
    workflow: {
      groups: 'Groups',
      age: 'ages 3–4',
      newChild: 'New child',
      enrolled: 'Assigned to the Yulduzcha group',
      capacity: 'Capacity 19 / 20',
    },
    finance: { inflow: 'Inflow', outflow: 'Outflow', unitMonth: 'UZS · September' },
  },
}

export const copy: Record<Locale, Copy> = { uz, ru, en }

export const CURRENCY: Record<Locale, string> = { uz: 'soʻm', ru: 'сум', en: 'UZS' }

export const groupThousands = (value: number) =>
  Math.round(value)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, ' ')

export const money = (value: number | string | undefined, locale: Locale) =>
  value === undefined || value === '' ? '—' : `${groupThousands(Number(value))} ${CURRENCY[locale]}`
