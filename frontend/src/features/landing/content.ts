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

/** Sarlavha + matn — eng oddiy karta (ota-onalar, qoʻshimcha imkoniyatlar). */
export interface CardCopy {
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
  parents: {
    bot: string
    balance: string
    invoices: string
    pay: string
    receipts: string
    askBalance: string
    answer: string
    due: string
    payNow: string
    paid: string
  }
  intelligence: {
    kind: string
    severity: string
    why: string
    evidence: string[]
    action: string
  }
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
    parents: string
    pricing: string
    faq: string
    login: string
    demo: string
    /** Birinchi chaqiriq — oʻzi roʻyxatdan oʻtib sinab koʻrish (ADR-28). */
    trial: string
    /** Telefon paneli uchun qisqa shakl — uzun yozuv panelni toshirardi. */
    trialShort: string
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
    /** Asosiy tugma: 15 kunlik sinov (`/signup`). */
    trial: string
    cta: string
    secondary: string
    /** Tugmalar ostidagi bir qator: nima kerak emasligi. */
    trustLine: string
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
  /** Ota-onalar kanali: Telegram bot + onlayn toʻlov (ADR-23, ADR-26, ADR-27). */
  parents: {
    eyebrow: string
    title: string
    text: string
    items: CardCopy[]
    note: string
  }
  /** Radix Intelligence V1 — qoidaga asoslangan, dalili bilan (ADR-14). */
  intelligence: {
    eyebrow: string
    title: string
    text: string
    points: string[]
  }
  /** Mahsulotning qolgan qismi — mock'siz, oddiy kartalar. */
  extras: { eyebrow: string; title: string; items: CardCopy[] }
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
    /** Uchinchi muddat — 6 oy, −15 % (ADR-12). */
    semiannual: string
    annual: string
    semiannualBadge: string
    annualBadge: string
    perMonth: string
    perHalfYear: string
    perYear: string
    effective: string
    includes: string[]
    examplesTitle: string
    examples: { children: number; monthly: number }[]
    annualFormula: string
    first3: string
    note: string
    /** Sinov muddati — raqam backend'dan (`trial_days`). */
    trial: string
    trialNote: string
    /** Toʻlov kechikса nima boʻladi (invariant 11) — xaridorning jim savoli. */
    safety: string
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
    /** Forma yonidagi tinchlantiruvchi qator — soʻrov nimaga ishlatiladi. */
    assurance: string
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
    parents: 'Ota-onalar',
    pricing: 'Narxlar',
    faq: 'Savollar',
    login: 'CRMʼga kirish',
    demo: 'Demo olish',
    trial: 'Bepul sinab koʻrish',
    trialShort: 'Sinab koʻrish',
    menu: 'Menyu',
    close: 'Yopish',
    language: 'Til',
    lang: { uz: 'UZ', ru: 'RU', en: 'EN' },
  },
  hero: {
    eyebrow: 'Xususiy bogʻchalar uchun boshqaruv platformasi',
    title: 'Bogʻcha boshqaruvi uchun kerak boʻlgan hamma narsa — bitta tizimda.',
    subtitle:
      'Bolalar, toʻlovlar, davomat, xodimlar va moliyaviy nazorat — hammasi bitta tizimda. Ota-ona esa balansni Telegramʼdan koʻradi.',
    trial: '15 kun bepul sinab koʻrish',
    cta: 'Demo olish',
    secondary: 'Radix qanday ishlaydi',
    trustLine: 'Karta kerak emas · 15 kun · istalgan payt toʻxtatasiz',
    priceFrom: 'Oyiga 400 000 soʻmdan',
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
        text: 'Hisob-faktura, toʻlov, qoldiq. Qarzdorlar roʻyxati pul harakatlari jurnalidan hisoblanadi — u hech qachon haqiqatdan ajralmaydi.',
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
        text: 'Kirim, chiqim, qoldiq. Xarajat 20 soniyada — summa, toifa, chek rasmi; xodim uni Telegram botga yuborib ham kiritadi. Nasiya xarid va investitsiya alohida. Bank koʻchirmasini yuklang — toʻlovlar, Click/Payme tushumlari va xarajatlar oʻzi bogʻlanadi.',
        caption: 'Qoldiq kamayadi → xarajat paydo boʻladi',
      },
      {
        id: 'reports',
        title: 'Hisobotlar va nazorat',
        text: 'Tushum, xarajat, ish haqi, qarzdorlik — bir ekranda. Foyda-zarar tegishli oy boʻyicha, pul oqimi pul sanasi boʻyicha: iyul oyligi avgustda toʻlansa ham iyul xarajati, dividend xarajat emas, konditsioner oylarga taqsimlanadi. Terminal va Click puli bankka tushguncha «yoʻlda» koʻrinadi.',
        caption: 'Olti savol, tekshiruvlar va «Diqqat» — bitta ekranda; egaga Telegram xabari',
      },
    ],
  },
  deepDive: {
    eyebrow: 'Boshqaruv paneli',
    title: 'Rahbar koʻrishi kerak boʻlgan barcha raqamlar — bir ekranda.',
    text: 'Bugungi davomat, oylik tushum, qarzdorlik va xodimlar — kirishingiz bilan. Har bir raqam jonli maʼlumotdan hisoblanadi.',
    steps: ['Umumiy holat', 'Davomat', 'Qarzdorlik', 'Tushum'],
  },
  parents: {
    eyebrow: 'Ota-onalar uchun',
    title: 'Ota-ona balansni telefonidan koʻradi — qoʻngʻiroqsiz.',
    text: 'Asosiy kanal — Telegram bot. Ilova oʻrnatish shart emas, bogʻchaga «qancha qarzim bor?» deb qilinadigan qoʻngʻiroqlar esa kamayadi.',
    items: [
      {
        title: 'Telegram bot',
        text: 'Balans, hisob-fakturalar, kvitansiyalar va “toʻlash” tugmasi — ota-onaning oʻz tilida (oʻzbek, rus, ingliz).',
      },
      {
        title: 'Onlayn toʻlov — Payme va Click',
        text: 'Pul toʻgʻridan-toʻgʻri bogʻchaning oʻz merchant hisobiga tushadi. Radix pulni ushlab turmaydi, ota-ona hisobdagi summani toʻlaydi — ustiga hech narsa qoʻshilmaydi.',
      },
      {
        title: 'Ulanish — taklif havolasi orqali',
        text: 'Vasiy botni oʻzi ishga tushiradi — havolani bosgani roziligining yozuvi boʻlib qoladi. Kim hali ulanmaganini roʻyxatda koʻrib turasiz.',
      },
      {
        title: 'SMS — ixtiyoriy',
        text: 'Telegram xabarlari bepul. SMS kerak boʻlsa, oʻz SMS-provayderingiz hisobi ulanadi va har bir xabar alohida hisoblanadi.',
      },
    ],
    note: 'Bola kelmagani haqidagi xabar — standart holatda oʻchiq. Uni yoqish yoki yoqmaslik bogʻchaning qarori.',
  },
  intelligence: {
    eyebrow: 'Radix AI',
    title: 'Toʻlov kechikishini oldindan aytadi — va buning sababini koʻrsatadi.',
    text: 'Har bir ogohlantirish qoidadan chiqadi va dalilini yonida olib yuradi: qaysi bolalar, qancha kun, qancha summa. Bosilsa — oʻsha roʻyxat ochiladi.',
    points: [
      'Qoida asosida, taxmin emas — bir xil maʼlumot har doim bir xil javob beradi',
      'Har bir xulosaning “Nega?” tugmasi bor: raqamlar qayerdan olingani koʻrinadi',
      'Har kecha oʻzi hisoblanadi; ertalab ekranda tayyor turadi',
    ],
  },
  extras: {
    eyebrow: 'Yana nimalar bor',
    title: 'Kundalik ishning mayda-chuydasi ham oʻylangan.',
    items: [
      {
        title: 'Har bir kun hisobda',
        text: 'Oy oʻrtasida kelgan yoki ketgan bola faqat bogʻchada boʻlgan ish kunlari uchun toʻlaydi, birinchi kunlari — bepul sinov. Bir oylik ariza bilan oy 0 soʻm, joy saqlanadi. Kelmagan kunlar maʼlumotnoma yoki ariza bilan qaytariladi — davomat jadvalidan emas.',
      },
      {
        title: 'Excelʼdan koʻchirish',
        text: 'Shablon sizning guruhlaringiz va tariflaringiz bilan yuklanadi; qarzdorlik va imtiyoz ustunlari bor. Boxodirova va Bohodirova — bitta bolami, sizdan soʻraladi. Bir telefon — bitta oila, aka-ukalar narxi farq qilsa ogohlantiriladi.',
      },
      {
        title: 'Pul qayerda va kimning qoʻlida',
        text: 'Naqd kassa va bank: terminal, oʻtkazma, Click va Payme bankka tushadi, komissiyasi oʻzi xarajat boʻlib yoziladi. Kassir pulni masʼulga topshiradi — u tasdiqlaydi, kimda qancha turgani koʻrinadi. Kun sanoq bilan yopiladi, farq sababi bilan. Toʻlovda bitta sana va toʻlovchi vasiy; xodim farzandi uchun — oylikdan ushlash.',
      },
      {
        title: 'Imtiyozlar — sababi bilan',
        text: 'Xodim farzandi, kam taʼminlangan, toʻliq imtiyoz — har biri turi, sababi va kim kiritgani bilan. Aka-uka chegirmasi umumiy vasiy orqali oʻzi qoʻllanadi, familiya boʻyicha taxmin emas. Oyiga kim, kimga, qancha bergani — alohida hisobotda.',
      },
      {
        title: 'Qarz yashirinmaydi',
        text: 'Qarzni qoʻlda 0 qilib boʻlmaydi — faqat sababi va kim qilgani bilan hisobdan chiqariladi. Har bir summa yonida «Nega?»: «3 050 000 × 8 / 21 = 1 162 000». Kim nimani oʻzgartirgani — oʻchmaydigan jurnalda.',
      },
      {
        title: 'Uch til',
        text: 'Oʻzbek, rus, ingliz — har bir xodim oʻzi tanlaydi. Bot ham ota-onaning tilida yozadi.',
      },
      {
        title: 'Rollar va ruxsatlar',
        text: 'Kim nimani koʻrishini egasi belgilaydi. Kassir faqat oʻzi qabul qilgan pulni koʻradi. Boshqaruvchi oylik hisobotni topshiradi — kim qancha maosh olishini koʻrmasdan; rahbar raqam yonida savol beradi, qaytaradi yoki qabul qiladi. Bankka — faqat oʻqish uchun, muddatli havola.',
      },
      {
        title: 'Filiallar',
        text: 'Bitta obuna — cheksiz filial. Filiallar yonma-yon: bandlik, yigʻish, marja — eng yaxshisi va eng yomoni belgilangan; umumiy hisobotda filiallararo oʻtkazma chiqarib tashlanadi. Xodim faqat oʻz filialini koʻradi.',
      },
      {
        title: 'Shartnoma — qoʻlda emas',
        text: 'Shablon sizniki; bolaning ismi, tarifi va vasiysi oʻzi joylashadi, raqam avtomatik — SH-2026-0007. Imzolangani qotib qoladi: tarif keyin oʻzgarsa ham, shartnomada kelishilgan summa turaveradi.',
      },
      {
        title: 'Kassada yoʻq pul chiqmaydi',
        text: 'Qoldiqdan ortiq chiqim rad etiladi — qaysi hisob, qancha bor, qancha yetmaydi. Har bir chiqim qator-qator: «Bozorlik — 600 000» emas, «Kartoshka, 50 kg × 3 000».',
      },
      {
        title: 'Oy oʻzi yigʻiladi va yopiladi',
        text: 'Har oy bir xil 16 boʻlimli hisobot: daromad zanjiri, qarzlar, xarajatlar, kassa koʻprigi, foyda-zarar va «foyda ≠ pul» — har raqamdan manba yozuvigacha bir bosish. Reja va fakt, 30/60/90 kunlik pul prognozi va «qancha pul olsa boʻladi» — formulasi bilan. PDF, Excel, oʻzgarmas nusxa.',
      },
      {
        title: 'Ikki bosqichli himoya',
        text: 'Har bir xodim oʻzi yoqadi — majburiy emas, chunki bogʻchada telefon almashib turiladi. Zaxira kodlar bir martalik: telefon yoʻqolsa ham kirasiz.',
      },
    ],
  },
  roles: {
    eyebrow: 'Radix kimlar uchun?',
    title: 'Har bir rol oʻziga kerak narsani koʻradi.',
    text: 'Ruxsatlar rollar boʻyicha beriladi, rollarni esa bogʻcha egasi belgilaydi.',
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
    title: '50 tagacha bola uchun — oyiga 400 000 soʻm.',
    text: 'Narx faqat bolalar soniga bogʻliq. Filiallar va xodimlar soni cheklanmagan.',
    childrenLabel: 'Bolalar soni',
    childrenUnit: 'bola',
    monthly: 'Oylik',
    semiannual: '6 oy',
    annual: 'Yillik',
    semiannualBadge: '15 % tejang',
    annualBadge: '25 % tejang',
    perMonth: '/ oy',
    perHalfYear: '/ 6 oy',
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
    first3: 'Ilk 3 oy — roʻyxatdan oʻtgan kuningizdagi narx boʻyicha.',
    trial: '15 kun bepul',
    trialNote: 'Karta kerak emas. Sinov tugagach toʻlovga oʻtasiz yoki shunchaki toʻxtatasiz.',
    safety:
      'Toʻlov kechiksa yozish toʻxtaydi, lekin oʻqish va eksport ishlayveradi — maʼlumotingiz oʻchirilmaydi va yashirilmaydi.',
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
        a: 'Xususiy bogʻchalar uchun boshqaruv platformasi: bolalar, guruhlar, davomat, toʻlovlar, qarzdorlik, xodimlar, ish haqi, xarajatlar, ombor va hisobotlar — bitta tizimda. Ota-onalar bilan aloqa Telegram bot orqali.',
      },
      {
        q: 'Bepul sinab koʻrsa boʻladimi?',
        a: 'Ha, 15 kun. Oʻzingiz roʻyxatdan oʻtasiz, karta kerak emas. Sinov davrida tizim toʻliq ishlaydi — oʻz bogʻchangiz maʼlumoti bilan.',
      },
      {
        q: 'Qancha turadi?',
        a: '50 tagacha bola uchun oyiga 400 000 soʻm. Har boshlangan 10 bola uchun 50 000 soʻm qoʻshiladi: 60 bola — 450 000, 70 bola — 500 000. Filiallar va xodimlar soni narxga taʼsir qilmaydi.',
      },
      {
        q: 'Toʻlov muddatlari qanday?',
        a: 'Oylik — chegirmasiz; 6 oylik — 15 % chegirma; yillik — 25 % chegirma. Narx sahifadagi kalkulyatorda hisoblanadi va hisob-faktura ham aynan shu formuladan chiqadi.',
      },
      {
        q: 'Hozirgi bolalar roʻyxatini qanday koʻchiramiz?',
        a: 'Excel shablonini yuklab olasiz — u sizning guruhlaringiz va tariflaringiz bilan keladi. Qarzdorlik ustuni ham bor, shuning uchun eski qarz birinchi kundanoq qarzdorlar roʻyxatida koʻrinadi. Koʻchirishda biz yordam beramiz.',
      },
      {
        q: 'Ota-onalar bilan qanday ishlaydi?',
        a: 'Telegram bot orqali: balans, hisob-fakturalar, kvitansiyalar va toʻlov tugmasi. Ilova oʻrnatish shart emas, xabarlar bepul. SMS kerak boʻlsa — oʻz gateway hisobingiz ulanadi.',
      },
      {
        q: 'Ota-ona onlayn toʻlay oladimi?',
        a: 'Ha — Payme va Click orqali. Pul toʻgʻridan-toʻgʻri sizning merchant hisobingizga tushadi, Radix pulni ushlab turmaydi. Ota-ona hisobdagi summani toʻlaydi, ustiga komissiya qoʻshilmaydi.',
      },
      {
        q: 'Obuna toʻlovini kechiktirsak nima boʻladi?',
        a: 'Yangi yozuv kiritish toʻxtaydi, lekin tizimga kirish, oʻqish va maʼlumotni eksport qilish ishlayveradi. Maʼlumot oʻchirilmaydi va yashirilmaydi — toʻlagan kuningizdan ishni kutgan joyingizdan davom ettirasiz.',
      },
      {
        q: 'Maʼlumotlar xavfsizligi qanday taʼminlanadi?',
        a: 'Rollarga asoslangan kirish, tashkilotlar izolyatsiyasi — ilova va maʼlumotlar bazasi darajasida (RLS), oʻzgartirib boʻlmaydigan audit jurnali, ixtiyoriy ikki bosqichli kirish va har kuni olinadigan zaxira nusxa.',
      },
      {
        q: 'Oʻz serverimizga oʻrnatsa boʻladimi?',
        a: 'Ha. Alohida oʻrnatma — bir martalik litsenziya: tizim sizning serveringizda, sizning domeningizda ishlaydi, oylik obuna boʻlmaydi. Narx kelishuv asosida.',
      },
      {
        q: 'Qaysi tillarda ishlaydi?',
        a: 'Oʻzbek, rus va ingliz tillarida. Har bir xodim oʻzi uchun tanlaydi, bot esa ota-onaning tilida yozadi.',
      },
    ],
  },
  lead: {
    eyebrow: 'Demo',
    title: 'Radix CRM bilan ishlashni boshlang.',
    text: 'Bogʻchangiz boshqaruvini soddalashtirishni birga rejalashtiramiz — bogʻlaning.',
    assurance:
      'Maʼlumotlaringiz faqat shu suhbat uchun ishlatiladi — reklama roʻyxatiga qoʻshilmaydi va boshqalarga berilmaydi. Kutishni xohlamasangiz, 15 kunlik sinovni hoziroq oʻzingiz boshlashingiz mumkin.',
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
  testimonials: {
    eyebrow: 'Mijozlar fikri',
    title: 'Radix bilan ishlayotgan bogʻchalar',
    items: [],
  },
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
    title: 'Radix CRM — bogʻcha boshqaruvi: toʻlovlar, davomat, ota-onalar',
    description:
      'Xususiy bogʻchalar uchun boshqaruv platformasi: bolalar, toʻlovlar, qarzdorlik, davomat, xodimlar va moliyaviy nazorat. Ota-onalar uchun Telegram bot va onlayn toʻlov. 15 kun bepul, 400 000 soʻm / oy dan.',
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
      oil: 'Yogʻ',
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
    parents: {
      bot: 'Radix bot',
      balance: 'Balans',
      invoices: 'Hisob-fakturalar',
      pay: 'Toʻlash',
      receipts: 'Kvitansiyalar',
      askBalance: 'Balans',
      answer: 'Karimov Ali · Quyosh guruhi',
      due: 'Sentabr uchun 1 500 000 soʻm',
      payNow: 'Payme orqali toʻlash',
      paid: 'Toʻlandi · kvitansiya yuborildi',
    },
    intelligence: {
      kind: 'Toʻlov kechikishi',
      severity: 'Jiddiy',
      why: 'Nega?',
      evidence: [
        '9 ta bola boʻyicha muddat 15 kundan oshdi',
        'Jami kechikkan summa — 12 450 000 soʻm',
        'Oʻtgan oyda bu raqam 6 bola va 7 200 000 edi',
      ],
      action: 'Qarzdorlar roʻyxatini ochish',
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
    parents: 'Родителям',
    pricing: 'Цены',
    faq: 'Вопросы',
    login: 'Войти в CRM',
    demo: 'Получить демо',
    trial: 'Попробовать бесплатно',
    trialShort: 'Попробовать',
    menu: 'Меню',
    close: 'Закрыть',
    language: 'Язык',
    lang: { uz: 'UZ', ru: 'RU', en: 'EN' },
  },
  hero: {
    eyebrow: 'Платформа управления для частных детских садов',
    title: 'Всё управление детским садом — в одной системе.',
    subtitle:
      'Дети, оплаты, посещаемость, сотрудники и финансовый контроль — в одной системе. А родитель видит баланс в Telegram.',
    trial: '15 дней бесплатно',
    cta: 'Получить демо',
    secondary: 'Как работает Radix',
    trustLine: 'Без карты · 15 дней · отменить можно в любой момент',
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
    title: 'То, что руководитель должен контролировать, не должно лежать в десяти разных местах.',
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
        text: 'Счёт, оплата, остаток. Список должников считается из журнала операций — он никогда не расходится с реальностью.',
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
        text: 'Приход, расход, остаток. Расход за 20 секунд — сумма, категория, фото чека; сотрудник может отправить его и в Telegram-бот. Покупки в долг и инвестиции — отдельно. Загрузите банковскую выписку — оплаты, поступления Click/Payme и расходы сопоставятся сами.',
        caption: 'Остаток уменьшается → появляется расход',
      },
      {
        id: 'reports',
        title: 'Отчёты и контроль',
        text: 'Выручка, расходы, зарплата, задолженность — на одном экране. Прибыль — по месяцу начисления, денежный поток — по дате денег: июльская зарплата, выплаченная в августе, — расход июля; дивиденд — не расход; кондиционер распределяется по месяцам. Деньги терминала и Click видны «в пути», пока не поступят в банк.',
        caption:
          'Шесть вопросов, проверки и «Внимание» — на одном экране; владельцу — сообщение в Telegram',
      },
    ],
  },
  deepDive: {
    eyebrow: 'Панель управления',
    title: 'Все цифры, которые должен видеть руководитель, — на одном экране.',
    text: 'Посещаемость сегодня, выручка за месяц, задолженность и сотрудники — сразу после входа. Каждая цифра считается из живых данных.',
    steps: ['Общая картина', 'Посещаемость', 'Задолженность', 'Выручка'],
  },
  parents: {
    eyebrow: 'Родителям',
    title: 'Родитель видит баланс в телефоне — без звонков.',
    text: 'Основной канал — бот в Telegram. Приложение ставить не нужно, а звонков «сколько я должен?» становится меньше.',
    items: [
      {
        title: 'Бот в Telegram',
        text: 'Баланс, счета, квитанции и кнопка «оплатить» — на языке самого родителя (узбекский, русский, английский).',
      },
      {
        title: 'Онлайн-оплата — Payme и Click',
        text: 'Деньги идут прямо на мерчант-счёт самого сада. Radix не держит чужие деньги, родитель платит ровно сумму счёта — сверху ничего не добавляется.',
      },
      {
        title: 'Подключение по ссылке-приглашению',
        text: 'Родитель запускает бота сам; переход по ссылке и есть запись о согласии. В списке видно, кто ещё не подключился.',
      },
      {
        title: 'SMS — по желанию',
        text: 'Сообщения в Telegram бесплатны. Если нужны SMS — подключаем ваш собственный шлюз, и каждое сообщение считается отдельно.',
      },
    ],
    note: 'Уведомление «ребёнка сегодня нет» по умолчанию выключено. Включать его или нет — решает сад.',
  },
  intelligence: {
    eyebrow: 'Radix AI',
    title: 'Предупреждает о задержке оплаты — и отвечает на вопрос «почему».',
    text: 'Каждое предупреждение выводится по правилу и несёт с собой доказательство: какие дети, сколько дней, какая сумма. По нажатию открывается тот самый список.',
    points: [
      'По правилам, а не на догадках — одни и те же данные всегда дают один и тот же ответ',
      'У каждого вывода есть «Почему?»: видно, откуда взяты цифры',
      'Считается ночью; утром результат уже на экране',
    ],
  },
  extras: {
    eyebrow: 'Что ещё есть',
    title: 'Мелочи ежедневной работы тоже продуманы.',
    items: [
      {
        title: 'Каждый день на счету',
        text: 'Ребёнок, пришедший или ушедший в середине месяца, платит только за рабочие дни в саду, а первые дни — бесплатная проба. По заявлению на месяц начисляется 0, место сохраняется. Пропуски возвращаются по справке или заявлению — не по табелю.',
      },
      {
        title: 'Перенос из Excel',
        text: 'Шаблон скачивается с вашими группами и тарифами; есть колонки долга и льготы. Бохадирова и Боходирова — один ребёнок или два, система спросит. Один телефон — одна семья, разная цена у братьев и сестёр — предупреждение.',
      },
      {
        title: 'Где деньги и у кого на руках',
        text: 'Касса и банк: терминал, перевод, Click и Payme поступают на банк, комиссия сама записывается расходом. Кассир передаёт деньги ответственному — тот подтверждает, видно, у кого сколько. День закрывается пересчётом, разница — с причиной. У оплаты одна дата и плательщик-опекун; за ребёнка сотрудника — удержание из зарплаты.',
      },
      {
        title: 'Льготы — с причиной',
        text: 'Ребёнок сотрудника, малообеспеченные, полная льгота — у каждой вид, причина и кто её ввёл. Скидка братьям и сёстрам применяется сама через общего опекуна, а не по фамилии. Кто, кому и сколько дал за месяц — в отдельном отчёте.',
      },
      {
        title: 'Долг не спрячешь',
        text: 'Долг нельзя обнулить вручную — только списать, с причиной и автором. У каждой суммы есть «Почему?»: «3 050 000 × 8 / 21 = 1 162 000». Кто что менял — в журнале, который нельзя стереть.',
      },
      {
        title: 'Три языка',
        text: 'Узбекский, русский, английский — каждый сотрудник выбирает свой. Бот пишет на языке родителя.',
      },
      {
        title: 'Роли и права',
        text: 'Владелец решает, кто что видит. Кассир видит только принятые им деньги. Управляющий сдаёт месячный отчёт — не видя, кто сколько получает; руководитель задаёт вопрос у цифры, возвращает или принимает. Банку — ссылка только для чтения и со сроком.',
      },
      {
        title: 'Филиалы',
        text: 'Одна подписка — сколько угодно филиалов. Филиалы рядом: заполненность, сбор, маржа — лучший и худший отмечены; в общем отчёте переводы между филиалами исключены. Сотрудник видит только свой.',
      },
      {
        title: 'Договор — не вручную',
        text: 'Шаблон ваш; имя ребёнка, тариф и опекун подставляются сами, номер автоматический — SH-2026-0007. Подписанный застывает: даже если тариф потом изменится, в договоре останется согласованная сумма.',
      },
      {
        title: 'Из пустой кассы деньги не уйдут',
        text: 'Расход больше остатка отклоняется — с названием счёта, остатком и суммой нехватки. Каждый расход построчно: не «рынок — 600 000», а «картошка, 50 кг × 3 000».',
      },
      {
        title: 'Месяц сводится и закрывается сам',
        text: 'Каждый месяц одинаковый отчёт из 16 разделов: цепочка дохода, долги, расходы, мост по кассе, прибыль и «прибыль ≠ деньги» — от любой цифры один клик до записей. План и факт, прогноз денег на 30/60/90 дней и «сколько можно забрать» — с формулой. PDF, Excel, неизменяемая копия.',
      },
      {
        title: 'Двухэтапная защита',
        text: 'Каждый сотрудник включает её сам — не принудительно, ведь в саду телефонами меняются. Резервные коды одноразовые: войдёте и с потерянным телефоном.',
      },
    ],
  },
  roles: {
    eyebrow: 'Для кого Radix?',
    title: 'Каждая роль видит то, что нужно именно ей.',
    text: 'Права выдаются по ролям, а роли настраивает владелец сада.',
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
        text: 'Ведите списки детей, группы и посещаемость в порядке.',
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
    semiannual: '6 месяцев',
    annual: 'За год',
    semiannualBadge: 'экономия 15 %',
    annualBadge: 'экономия 25 %',
    perMonth: '/ мес',
    perHalfYear: '/ 6 мес',
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
    first3: 'Первые 3 месяца — по цене на день подписки.',
    trial: '15 дней бесплатно',
    trialNote:
      'Карта не нужна. После пробного периода вы переходите на оплату или просто останавливаетесь.',
    safety:
      'При задержке оплаты запись останавливается, но чтение и выгрузка работают — данные не удаляются и не прячутся.',
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
        a: 'Платформа управления для частных детских садов: дети, группы, посещаемость, оплаты, задолженность, сотрудники, зарплата, расходы, склад и отчёты — в одной системе. С родителями — через бот в Telegram.',
      },
      {
        q: 'Можно попробовать бесплатно?',
        a: 'Да, 15 дней. Вы регистрируетесь сами, карта не нужна. В пробный период система работает полностью — на данных вашего сада.',
      },
      {
        q: 'Сколько стоит?',
        a: '400 000 сум в месяц до 50 детей. За каждые начатые 10 детей — плюс 50 000 сум: 60 детей — 450 000, 70 детей — 500 000. Количество филиалов и сотрудников на цену не влияет.',
      },
      {
        q: 'Какие есть периоды оплаты?',
        a: 'Ежемесячно — без скидки; 6 месяцев — скидка 15 %; год — скидка 25 %. Калькулятор на странице считает по той же формуле, по которой выставляется счёт.',
      },
      {
        q: 'Как перенести уже имеющихся детей?',
        a: 'Скачиваете шаблон Excel — он приходит с вашими группами и тарифами. Есть колонка задолженности, поэтому прежний долг виден в списке должников с первого дня. С переносом мы помогаем.',
      },
      {
        q: 'Как это работает для родителей?',
        a: 'Через бот в Telegram: баланс, счета, квитанции и кнопка оплаты. Приложение ставить не нужно, сообщения бесплатны. Нужны SMS — подключаем ваш собственный шлюз.',
      },
      {
        q: 'Родитель может оплатить онлайн?',
        a: 'Да — через Payme и Click. Деньги приходят прямо на ваш мерчант-счёт, Radix их не держит. Родитель платит ровно сумму счёта, комиссия сверху не добавляется.',
      },
      {
        q: 'Что будет, если задержать оплату подписки?',
        a: 'Остановится ввод новых записей, но вход, чтение и выгрузка данных продолжают работать. Ничего не удаляется и не прячется — после оплаты вы продолжаете с того же места.',
      },
      {
        q: 'Как обеспечивается безопасность данных?',
        a: 'Доступ по ролям, изоляция организаций — и в приложении, и на уровне базы данных (RLS), неизменяемый журнал действий, двухфакторный вход по желанию и ежедневная резервная копия.',
      },
      {
        q: 'Можно установить на свой сервер?',
        a: 'Да. Отдельная установка — разовая лицензия: система работает на вашем сервере и вашем домене, без ежемесячной подписки. Цена договорная.',
      },
      {
        q: 'На каких языках работает?',
        a: 'Узбекский, русский и английский. Каждый сотрудник выбирает свой, а бот пишет на языке родителя.',
      },
    ],
  },
  lead: {
    eyebrow: 'Демо',
    title: 'Начните работать с Radix CRM.',
    text: 'Свяжитесь с нами, чтобы упростить управление вашим детским садом.',
    assurance:
      'Ваши данные используются только для этого разговора — ни рассылок, ни передачи третьим лицам. Ждать не обязательно: пробный период на 15 дней можно начать самостоятельно.',
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
    title: 'Radix CRM — управление садом: оплаты, посещаемость, родители',
    description:
      'Платформа управления для частных детских садов: дети, оплаты, задолженность, посещаемость, сотрудники и финансовый контроль. Для родителей — бот в Telegram и онлайн-оплата. 15 дней бесплатно, от 400 000 сум / мес.',
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
    parents: {
      bot: 'Radix bot',
      balance: 'Баланс',
      invoices: 'Счета',
      pay: 'Оплатить',
      receipts: 'Квитанции',
      askBalance: 'Баланс',
      answer: 'Каримов Али · группа «Куёш»',
      due: 'За сентябрь — 1 500 000 сум',
      payNow: 'Оплатить через Payme',
      paid: 'Оплачено · квитанция отправлена',
    },
    intelligence: {
      kind: 'Задержка оплаты',
      severity: 'Серьёзно',
      why: 'Почему?',
      evidence: [
        'По 9 детям срок превышен более чем на 15 дней',
        'Общая просроченная сумма — 12 450 000 сум',
        'В прошлом месяце было 6 детей и 7 200 000',
      ],
      action: 'Открыть список должников',
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
    parents: 'For parents',
    pricing: 'Pricing',
    faq: 'FAQ',
    login: 'Sign in to CRM',
    demo: 'Get a demo',
    trial: 'Try it free',
    trialShort: 'Try free',
    menu: 'Menu',
    close: 'Close',
    language: 'Language',
    lang: { uz: 'UZ', ru: 'RU', en: 'EN' },
  },
  hero: {
    eyebrow: 'A management platform for private kindergartens',
    title: 'Everything to run your kindergarten — in one system.',
    subtitle:
      'Children, payments, attendance, staff and financial control in one system — and parents see the balance in Telegram.',
    trial: 'Start a 15-day free trial',
    cta: 'Get a demo',
    secondary: 'How Radix works',
    trustLine: 'No card · 15 days · cancel whenever you like',
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
    text: 'A message in Telegram, a table in Excel, a note in a notebook, a receipt at the till. Each one is correct — but there is no overall picture.',
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
        text: 'Receipts, issues, stock on hand. An expense in 20 seconds — amount, category, receipt photo; staff can also send it to the Telegram bot. Credit purchases and investments kept apart. Upload the bank statement and payments, Click/Payme receipts and expenses match themselves.',
        caption: 'Stock goes down → an expense appears',
      },
      {
        id: 'reports',
        title: 'Reports and control',
        text: 'Revenue, expenses, payroll, debt — on one screen. Profit by the month it belongs to, cash flow by the day money moved: July salaries paid in August are a July cost, a dividend is not an expense, an air conditioner is spread over months. Terminal and Click money shows as “in transit” until it reaches the bank.',
        caption:
          'Six questions, checks and attention items on one screen; the owner gets a Telegram message',
      },
    ],
  },
  deepDive: {
    eyebrow: 'Dashboard',
    title: 'Every number the director needs — on one screen.',
    text: 'Today’s attendance, monthly revenue, debt and staff — the moment you sign in. Every number is calculated from live data.',
    steps: ['Overview', 'Attendance', 'Debt', 'Revenue'],
  },
  parents: {
    eyebrow: 'For parents',
    title: 'Parents see the balance on their phone — no phone calls.',
    text: 'The main channel is a Telegram bot. Nothing to install, and far fewer “how much do I owe?” calls to the office.',
    items: [
      {
        title: 'Telegram bot',
        text: 'Balance, invoices, receipts and a “pay” button — in the parent’s own language (Uzbek, Russian, English).',
      },
      {
        title: 'Online payment — Payme and Click',
        text: 'The money goes straight to the kindergarten’s own merchant account. Radix never holds it, and the parent pays exactly the invoice — nothing is added on top.',
      },
      {
        title: 'Linking by invitation',
        text: 'The parent starts the bot themselves; following the link is the consent record. The list shows who has not linked yet.',
      },
      {
        title: 'SMS — optional',
        text: 'Telegram messages are free. If you want SMS, we connect your own gateway and every message is counted.',
      },
    ],
    note: 'The “your child is absent today” message is off by default. Whether to turn it on is the kindergarten’s call.',
  },
  intelligence: {
    eyebrow: 'Radix AI',
    title: 'It warns about late payment — and answers “why”.',
    text: 'Every warning comes from a rule and carries its evidence: which children, how many days, how much money. One tap opens that exact list.',
    points: [
      'Rules, not guesswork — the same data always gives the same answer',
      'Every finding has a “Why?”: you can see where the numbers came from',
      'Computed overnight; the answer is on the screen by morning',
    ],
  },
  extras: {
    eyebrow: 'What else is there',
    title: 'The small parts of the daily work are thought through too.',
    items: [
      {
        title: 'Every day accounted for',
        text: 'A child who arrives or leaves mid-month pays only for the working days spent at the kindergarten, and the first days are a free trial. A one-month leave charges nothing and keeps the place. Absences are credited from a certificate or an application — never from the attendance grid.',
      },
      {
        title: 'Import from Excel',
        text: 'The template downloads with your own groups and tariffs, with debt and benefit columns. Boxodirova and Bohodirova — one child or two? You are asked. One phone is one family, and siblings at different prices are flagged.',
      },
      {
        title: 'Where the money is, and who holds it',
        text: 'A till and a bank: terminal, transfer, Click and Payme land in the bank, and the commission is booked as an expense by itself. The cashier hands cash to the person in charge, who confirms it — you can see who holds how much. The day closes with a count; any difference carries a reason. Every payment has one date and a guardian who paid; a staff parent can pay by salary deduction.',
      },
      {
        title: 'Benefits, with a reason',
        text: 'Staff child, low income, full exemption — each with its type, its reason and who entered it. The sibling discount applies itself through a shared guardian, never guessed from a surname. Who gave whom how much each month sits in its own report.',
      },
      {
        title: 'Debt cannot hide',
        text: 'Nobody can set a debt to zero by hand — it is written off with a reason and a name, or not at all. Every amount has a “Why?”: “3 050 000 × 8 / 21 = 1 162 000”. Who changed what sits in a log that cannot be erased.',
      },
      {
        title: 'Three languages',
        text: 'Uzbek, Russian, English — each member of staff picks their own. The bot writes in the parent’s language.',
      },
      {
        title: 'Roles and permissions',
        text: 'The owner decides who sees what. A cashier sees only the money they took. A manager submits the monthly report without seeing who earns what; a leader asks at a number, returns it or accepts it. For the bank — a read-only link that expires.',
      },
      {
        title: 'Branches',
        text: 'One subscription, as many branches as you like. Branches side by side — occupancy, collection, margin, with the best and worst marked; the combined report leaves out transfers between branches. Staff see only their own.',
      },
      {
        title: 'Contracts, not retyping',
        text: 'The template is yours; the child, the tariff and the guardian fill themselves in, and the number is automatic — SH-2026-0007. A signed contract freezes: if the tariff changes next month, it still says what was agreed.',
      },
      {
        title: 'An empty till pays nothing out',
        text: 'A payment larger than the balance is refused, naming the account, what it holds and what is short. Every expense is itemised: not “market — 600 000” but “potatoes, 50 kg × 3 000”.',
      },
      {
        title: 'The month sums and closes itself',
        text: 'The same 16-section report every month: revenue chain, debts, expenses, the till bridge, profit and loss and “profit ≠ cash” — one click from any number to its records. Plan against actual, a 30/60/90-day cash forecast and “how much can I take out”, formula shown. PDF, Excel, an immutable copy.',
      },
      {
        title: 'Two-step protection',
        text: 'Each member of staff turns it on themselves — never forced, because phones get shared and swapped in a kindergarten. Backup codes are single-use, so a lost phone does not lock anyone out.',
      },
    ],
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
    semiannual: '6 months',
    annual: 'Annual',
    semiannualBadge: 'Save 15 %',
    annualBadge: 'Save 25 %',
    perMonth: '/ month',
    perHalfYear: '/ 6 months',
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
    first3: 'First 3 months — at the price on the day you sign up.',
    trial: '15 days free',
    trialNote: 'No card. When the trial ends you either start paying or simply stop.',
    safety:
      'If payment is late, writing stops — but reading and export keep working, and nothing is deleted or hidden.',
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
        a: 'A management platform for private kindergartens: children, groups, attendance, payments, debtors, staff, payroll, expenses, inventory and reports in one system — with a Telegram bot as the channel to parents.',
      },
      {
        q: 'Can we try it for free?',
        a: 'Yes, for 15 days. You sign up yourself and no card is needed. During the trial the system is complete — with your own kindergarten’s data.',
      },
      {
        q: 'What does it cost?',
        a: '400 000 UZS a month for up to 50 children. Each further 10 children, or part of them, adds 50 000: 60 children — 450 000, 70 children — 500 000. Branches and staff do not change the price.',
      },
      {
        q: 'Which payment terms are there?',
        a: 'Monthly at full price, six months at −15 %, a year at −25 %. The calculator on this page uses the same formula the invoice is built from.',
      },
      {
        q: 'How do we move the children we already have?',
        a: 'You download an Excel template that comes with your own groups and tariffs. It has a debt column, so an old balance appears among the debtors from day one. We help with the move.',
      },
      {
        q: 'How does it work for parents?',
        a: 'Through a Telegram bot: balance, invoices, receipts and a pay button. Nothing to install and the messages are free. If you want SMS, we connect your own gateway.',
      },
      {
        q: 'Can a parent pay online?',
        a: 'Yes — with Payme and Click. The money arrives in your own merchant account; Radix never holds it. The parent pays exactly the invoice, with nothing added on top.',
      },
      {
        q: 'What happens if a subscription payment is late?',
        a: 'Writing stops, but signing in, reading and exporting keep working. Nothing is deleted or hidden — once you pay, you carry on where you left off.',
      },
      {
        q: 'How is the data kept safe?',
        a: 'Role-based access, organizations isolated both in the application and in the database itself (RLS), an audit log that cannot be edited, optional two-factor sign-in and a daily backup.',
      },
      {
        q: 'Can we install it on our own server?',
        a: 'Yes. A standalone licence is a one-off: the system runs on your server and your domain, with no monthly subscription. Price by agreement.',
      },
      {
        q: 'Which languages does it work in?',
        a: 'Uzbek, Russian and English. Each member of staff picks their own, and the bot writes in the parent’s language.',
      },
    ],
  },
  lead: {
    eyebrow: 'Demo',
    title: 'Start working with Radix CRM.',
    text: 'Get in touch to simplify the management of your kindergarten.',
    assurance:
      'Your details are used for this conversation only — no mailing list, nothing passed on. And you do not have to wait: you can start the 15-day trial yourself.',
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
    title: 'Radix CRM — kindergarten management: payments, attendance, parents',
    description:
      'A management platform for private kindergartens: children, payments, debtors, attendance, staff and financial control. A Telegram bot and online payment for parents. 15 days free, from 400 000 UZS / month.',
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
    parents: {
      bot: 'Radix bot',
      balance: 'Balance',
      invoices: 'Invoices',
      pay: 'Pay',
      receipts: 'Receipts',
      askBalance: 'Balance',
      answer: 'Ali Karimov · Quyosh group',
      due: 'September — 1 500 000 UZS',
      payNow: 'Pay with Payme',
      paid: 'Paid · receipt sent',
    },
    intelligence: {
      kind: 'Late payment',
      severity: 'Serious',
      why: 'Why?',
      evidence: [
        '9 children are more than 15 days past due',
        'The overdue total is 12 450 000 UZS',
        'Last month it was 6 children and 7 200 000',
      ],
      action: 'Open the debtors list',
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
