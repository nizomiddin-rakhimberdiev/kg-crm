/**
 * Public sayt matni — UZ va RU, bitta joyda.
 *
 * Komponentlarda `locale === 'uz' ? … : …` ternary'lari YO'Q: har bir
 * satr shu yerda, ikkala tilda. Aks holda tarjima ikki joyga sochilib,
 * RU sahifada o'zbekcha so'z qolib ketardi va uni hech kim sezmasdi.
 *
 * Narxlar bu yerda matn sifatida faqat FAQ va model kartalarida — ular
 * tushuntirish. Hisob-kitobning o'zi `/api/v1/public/pricing` dan keladi
 * (ADR-12 dan keyin kodga qotirilgan raqamlar yetti joyda eskirgan edi).
 */

export type Locale = 'uz' | 'ru'

type Feature = { title: string; text: string }

/** Yetkazib berish modeli — bulutli obuna yoki alohida o'rnatma (ADR-13). */
export type DeliveryPlan = {
  id: 'cloud' | 'onprem'
  badge: string
  name: string
  price: string
  priceNote: string
  text: string
  points: string[]
  cta: string
  href: string
}

/** Tizimdagi HAQIQIY rollar (apps/accounts/constants.py) — uydirma emas. */
export type RoleCard = { role: string; text: string }

export type Copy = {
  nav: {
    product: string
    capabilities: string
    pricing: string
    faq: string
    login: string
    demo: string
    switchLabel: string
    switchShort: string
    menuOpen: string
    menuClose: string
  }
  hero: {
    eyebrow: string
    title: string
    text: string
    primary: string
    secondary: string
    note: string
    /** `{children}` va `{amount}` API'dan keladi. */
    priceNote: string
  }
  proof: string
  problems: { eyebrow: string; title: string; items: string[]; bridge: string }
  solution: { eyebrow: string; title: string; text: string }
  featureTitle: string
  features: Feature[]
  preview: {
    eyebrow: string
    title: string
    text: string
    sample: string
    live: string
    revenue: string
    debt: string
    attendance: string
    children: string
    tasksTitle: string
    tasks: string[]
    nav: string[]
    active: string
    finance: string
    recent: string
  }
  roles: { eyebrow: string; title: string; text: string; items: RoleCard[] }
  steps: { eyebrow: string; title: string; items: Feature[] }
  pricing: {
    eyebrow: string
    title: string
    text: string
    monthly: string
    annual: string
    saving: string
    before: string
    children: string
    childrenUnit: string
    sliderLabel: string
    perMonth: string
    perYear: string
    perChild: string
    effectiveMonthly: string
    discountBadge: string
    policy: string
    disclaimer: string
    loading: string
    error: string
  }
  delivery: { eyebrow: string; title: string; text: string; plans: DeliveryPlan[]; note: string }
  security: { eyebrow: string; title: string; points: Feature[] }
  faq: { eyebrow: string; title: string; items: Feature[] }
  form: {
    eyebrow: string
    closing: string
    title: string
    text: string
    name: string
    phone: string
    kindergarten: string
    children: string
    city: string
    message: string
    consent: string
    submit: string
    sending: string
    success: string
    error: string
    privacy: string
    privacyNote: string
  }
  legal: {
    privacy: string
    terms: string
    updated: string
    back: string
    privacySections: Feature[]
    termsSections: Feature[]
    operator: string
  }
  footer: { product: string; privacy: string; terms: string; login: string; copyright: string }
  seo: { title: string; description: string }
}

export const copy: Record<Locale, Copy> = {
  uz: {
    nav: {
      product: 'Mahsulot',
      capabilities: 'Imkoniyatlar',
      pricing: 'Narxlar',
      faq: 'Savollar',
      login: 'CRM‘ga kirish',
      demo: 'Demo olish',
      switchLabel: 'Русский',
      switchShort: 'RU',
      menuOpen: 'Menyuni ochish',
      menuClose: 'Menyuni yopish',
    },
    hero: {
      eyebrow: 'Xususiy bog‘chalar uchun boshqaruv platformasi',
      title: 'Bog‘changizni boshqarishning barchasi — bitta tizimda.',
      text: 'Bolalar, davomat, to‘lovlar, qarzdorlik, xodimlar, xarajatlar va hisobotlarni yagona platformada boshqaring.',
      primary: 'Demo olish',
      secondary: 'Imkoniyatlarni ko‘rish',
      note: 'Cheksiz filial va xodim — to‘lov faqat bolalar soniga qarab.',
      priceNote: '{children} bolagacha — {amount}/oydan',
    },
    proof: 'Qog‘oz daftar, Excel va alohida chatlar o‘rniga — bitta boshqaruv manbai.',
    problems: {
      eyebrow: 'Kundalik tartibsizlik',
      title: 'Rahbar nazorat qilishi kerak bo‘lgan ishlar turli joylarga sochilib ketmasin.',
      items: [
        'To‘lovlar bir joyda, davomat boshqa joyda, hisobot Excelda.',
        'Qarzdorlik qo‘lda hisoblanadi — xato va kechikish tug‘iladi.',
        'Xodimlar, ish haqi, xarajat va ombor holati bir manzarada ko‘rinmaydi.',
        'Hisobot tayyorlash vaqt oladi, qaror esa kechikadi.',
      ],
      bridge: 'Bularning barchasini Radix bitta tizimga jamlaydi.',
    },
    solution: {
      eyebrow: 'Bitta boshqaruv markazi',
      title: 'Operatsion ish va moliyaviy nazorat bir tizimda.',
      text: 'Radix bog‘cha jamoasining kundalik vazifalarini rolga mos boshqaradi, rahbarga esa real vaqtga yaqin umumiy ko‘rinish beradi.',
    },
    featureTitle: 'Bog‘cha ishining asosiy yo‘nalishlari uchun tayyor modullar.',
    features: [
      {
        title: 'Bolalar va guruhlar',
        text: 'Har bir bola va vasiyning ma’lumoti bir joyda. Guruhlarni tuzing, bolalarni ro‘yxatdan o‘tkazing, mavjud ro‘yxatni Excel’dan bir marta yuklang.',
      },
      {
        title: 'To‘lovlar va qarzdorlik',
        text: 'Har bir bolaning to‘lovi, qarzdorligi va moliyaviy tarixini bir joydan nazorat qiling. Qarzdorlar ro‘yxati o‘zi shakllanadi.',
      },
      {
        title: 'Davomat',
        text: 'Guruh bo‘yicha kundalik davomatni bir necha soniyada belgilang va oylik xulosani hisobotda ko‘ring.',
      },
      {
        title: 'Xodimlar va ish haqi',
        text: 'Xodimlar, lavozimlar va oylik hisob-kitob — tarixi bilan. Har oyning hisobi keyin o‘zgarmaydi.',
      },
      {
        title: 'Ombor va xarajatlar',
        text: 'Mahsulot qoldig‘i, kirim-chiqim va xarajatlarni nazorat qiling — kam qolgan mahsulot o‘zi ko‘rinadi.',
      },
      {
        title: 'Hisobot va audit',
        text: 'Rahbar uchun kerakli raqamlar bir ekranda, hisobotlar CSV’ga chiqadi, har bir amal jurnalda qoladi.',
      },
    ],
    preview: {
      eyebrow: 'Mahsulot ko‘rinishi',
      title: 'Rahbar ko‘rishi kerak bo‘lgan raqamlar — bir ekranda.',
      text: 'Kunlik holatni, moliyaviy ko‘rsatkichlarni va asosiy operatsion jarayonlarni bir qarashda nazorat qiling. Ko‘rinish Radix’dagi haqiqiy dashboard tuzilmasiga asoslangan.',
      sample: 'Namuna',
      live: 'Asosiy ko‘rsatkichlar',
      revenue: 'Oy tushumi',
      debt: 'Qarzdorlik',
      attendance: 'Bugungi davomat',
      children: 'Faol bolalar',
      tasksTitle: 'Bugungi ustuvor vazifalar',
      tasks: ['Davomatni yakunlash', 'Qarzdorlikni ko‘rib chiqish', 'Ombor qoldig‘ini tekshirish'],
      nav: ['Dashboard', 'Bolalar', 'To‘lovlar', 'Davomat', 'Hisobotlar'],
      active: 'Faol',
      finance: 'Moliyaviy dinamika',
      recent: 'So‘nggi to‘lovlar',
    },
    roles: {
      eyebrow: 'Kimlar uchun',
      title: 'Radix kimlar uchun?',
      text: 'Har bir xodim o‘z roliga mos imkoniyatlarni ko‘radi — ortiqchasini emas.',
      items: [
        {
          role: 'Bog‘cha egasi',
          text: 'Moliyaviy holat, xodimlar va barcha filiallar — bir qarashda. Obuna va rollarni o‘zingiz boshqarasiz.',
        },
        {
          role: 'Direktor',
          text: 'Kundalik operatsion ishlarni yagona tizimdan boshqaring: bolalar, davomat, to‘lovlar, xodimlar, hisobotlar.',
        },
        {
          role: 'Kassir',
          text: 'To‘lovlarni qabul qiling, qarzdorlikni aniq yuriting. Har bir to‘lov ledger’da iz qoldiradi.',
        },
        {
          role: 'Menejer',
          text: 'Bolalar, guruhlar, davomat va omborni tartibli boshqaring — moliyaviy ma’lumotga tegmasdan.',
        },
      ],
    },
    steps: {
      eyebrow: 'Boshlash jarayoni',
      title: 'Sotuv suhbatidan kundalik boshqaruvgacha.',
      items: [
        { title: 'Demo so‘rang', text: 'Bog‘changiz ehtiyoji va bolalar sonini qoldiring.' },
        {
          title: 'Tashkilotni ochamiz',
          text: 'Platforma jamoasi tashkilot, dastlabki filial va egani xavfsiz yaratadi.',
        },
        {
          title: 'Ma’lumotlarni yuklang',
          text: 'Bolalar ro‘yxatini import qiling, guruh va xodimlarni sozlang.',
        },
        {
          title: 'Boshqaruvni boshlang',
          text: 'Davomat, moliya va operatsion holatni kundalik boshqaring.',
        },
      ],
    },
    pricing: {
      eyebrow: 'Sodda va tushunarli narxlash',
      title: 'Bog‘changiz uchun qancha turadi?',
      text: 'Bitta obuna barcha filiallar va xodimlarni qamrab oladi. Narx bolalarning eng yuqori soni asosida hisoblanadi.',
      monthly: 'Oyma-oy',
      annual: 'Yillik',
      saving: 'Yillik to‘lovda tejaysiz',
      before: 'Chegirmasiz yillik summa',
      children: 'Bolalar soni',
      childrenUnit: 'bola',
      sliderLabel: 'Bolalar sonini slayder bilan sozlash',
      perMonth: 'so‘m / oy',
      perYear: 'so‘m / yil',
      perChild: 'bir bola uchun, oyiga',
      effectiveMonthly: 'yillik to‘lovda oyiga',
      discountBadge: '25% chegirma',
      policy: 'Dastlabki 3 oy davomida joriy tariflar amal qiladi. Platformaga yangi imkoniyatlar va xizmatlar qo‘shilishi bilan tariflar kelajakda yangilanishi mumkin.',
      disclaimer: 'Kalkulyator joriy tarif asosidagi yo‘naltiruvchi hisob. Yakuniy summa rasmiy shartnoma va hisob-fakturaga muvofiq belgilanadi.',
      loading: 'Hisoblanmoqda…',
      error: 'Hisobni yuklab bo‘lmadi. Qayta urinib ko‘ring.',
    },
    delivery: {
      eyebrow: 'Ikki xil ishlash modeli',
      title: 'Bulutda obuna bilan yoki o‘z serveringizda — tanlov sizda.',
      text: 'Mahsulot ikkalasida ham bir xil: bir xil modullar, bir xil imkoniyatlar. Farq faqat tizim qayerda ishlashida va qanday to‘lashingizda.',
      plans: [
        {
          id: 'cloud',
          badge: 'Ko‘p tanlanadi',
          name: 'Bulutli obuna',
          price: '400 000 so‘mdan',
          priceNote: 'oyiga, 50 bolagacha',
          text: 'Server, yangilanish va zaxira nusxa bizning zimmamizda. Siz faqat bog‘chani boshqarasiz.',
          points: [
            'Bir necha daqiqada ishga tushadi — o‘rnatish kerak emas',
            '15 kunlik bepul sinov, karta so‘ralmaydi',
            'Yangilanishlar avtomatik va bepul',
            'Zaxira nusxa, monitoring va texnik xizmat bizda',
            'Cheksiz filial va xodim',
          ],
          cta: 'Demo olish',
          href: '#demo',
        },
        {
          id: 'onprem',
          badge: 'Bir martalik to‘lov',
          name: 'Alohida o‘rnatma',
          price: 'Kelishuv asosida',
          priceNote: 'bir martalik to‘lov, oylik to‘lovsiz',
          text: 'Tizim to‘liq sizniki bo‘ladi: o‘z serveringizda, o‘z domeningizda, obunasiz.',
          points: [
            'Ma’lumot butunlay sizning serveringizda qoladi',
            'Oylik obuna yo‘q — bir marta to‘laysiz',
            'O‘z domeningizda ishlaydi',
            'O‘rnatish va sozlashni biz bajaramiz',
            'Yangilanishlar kelishuvga muvofiq o‘rnatiladi',
          ],
          cta: 'Narx so‘rash',
          href: '#demo',
        },
      ],
      note: 'Qaysi model mos kelishini bilmayapsizmi? Zayavka qoldiring — bog‘changiz hajmi va talablariga qarab maslahat beramiz.',
    },
    security: {
      eyebrow: 'Ma’lumotlar xavfsizligi',
      title: 'Ma’lumotlaringizga mas’uliyat bilan yondashamiz.',
      points: [
        {
          title: 'Rollarga asoslangan kirish',
          text: 'Har bir xodim faqat o‘z roliga tegishli bo‘limlarni ko‘radi. Ruxsatlarni tashkilot egasi boshqaradi.',
        },
        {
          title: 'Tashkilotlar izolyatsiyasi',
          text: 'Har bir bog‘chaning ma’lumoti ilova va ma’lumotlar bazasi darajasida alohida — boshqa tashkilot uni hech qachon ko‘rmaydi.',
        },
        {
          title: 'Audit jurnali',
          text: 'Kim, nima va qachon o‘zgartirgani o‘zgartirib bo‘lmaydigan jurnalda saqlanadi.',
        },
      ],
    },
    faq: {
      eyebrow: 'Savollar va javoblar',
      title: 'Qaror qabul qilish uchun kerakli asosiy ma’lumotlar.',
      items: [
        {
          title: 'Radix CRM nima?',
          text: 'Xususiy bog‘chalar uchun boshqaruv platformasi: bolalar, guruhlar, davomat, to‘lovlar, qarzdorlik, xodimlar, ish haqi, xarajatlar, ombor va hisobotlar — bitta tizimda.',
        },
        {
          title: 'Radix CRM kimlar uchun?',
          text: 'O‘zbekistondagi xususiy bog‘chalar va bir nechta filiali bo‘lgan tashkilotlar uchun.',
        },
        {
          title: 'Narx qanday hisoblanadi?',
          text: '50 tagacha bola uchun oyiga 400 000 so‘m. 50 dan oshganda har boshlangan 10 bola uchun 50 000 so‘m qo‘shiladi: 51–60 bola — 450 000 so‘m.',
        },
        {
          title: 'Yillik to‘lovda chegirma bormi?',
          text: 'Ha. Yillik to‘lov 12 oylik summadan 25% chegirma bilan hisoblanadi.',
        },
        {
          title: 'Dastlabki 3 oy qanday ishlaydi?',
          text: 'Dastlabki uch oyda joriy tariflar amal qiladi. Keyingi o‘zgarishlar platformaga yangi imkoniyatlar qo‘shilishi bilan bog‘liq bo‘lishi mumkin.',
        },
        {
          title: 'Bulutli obuna va alohida o‘rnatma farqi nima?',
          text: 'Mahsulot bir xil. Bulutli obunada tizim bizning serverimizda ishlaydi va siz oyiga to‘laysiz. Alohida o‘rnatmada tizim sizning serveringizga o‘rnatiladi, bir martalik to‘lov olinadi va oylik obuna bo‘lmaydi. Narx kelishuv asosida belgilanadi.',
        },
        {
          title: 'Ma’lumotlar xavfsizmi?',
          text: 'Tizim rollarga asoslangan kirish, tashkilotlar izolyatsiyasi (ma’lumotlar bazasi darajasida ham) va o‘zgartirib bo‘lmaydigan audit jurnali bilan ishlaydi.',
        },
        {
          title: 'Qanday boshlash mumkin?',
          text: 'Demo so‘rang. Suhbatdan so‘ng platforma jamoasi tashkilotingizni ochadi va siz ma’lumotlarni yuklashni boshlaysiz.',
        },
      ],
    },
    form: {
      eyebrow: 'Bog‘changiz uchun demo',
      closing: 'Bog‘changiz boshqaruvini soddalashtirishga tayyormisiz?',
      title: 'Radix CRM bilan ishlashni boshlang.',
      text: 'Bog‘changiz haqida qisqacha ma’lumot qoldiring — siz bilan bog‘lanib, tizimni namoyish qilamiz.',
      name: 'Ismingiz',
      phone: 'Telefon raqam',
      kindergarten: 'Bog‘cha nomi',
      children: 'Bolalar soni',
      city: 'Shahar / hudud',
      message: 'Izoh (ixtiyoriy)',
      consent: 'Shaxsiy ma’lumotlarimga Maxfiylik siyosatiga muvofiq ishlov berilishiga roziman.',
      submit: 'Demo so‘rash',
      sending: 'Yuborilmoqda…',
      success: 'Rahmat. So‘rovingiz qabul qilindi — tez orada bog‘lanamiz.',
      error: 'So‘rovni yuborib bo‘lmadi. Maydonlarni tekshirib, qayta urinib ko‘ring.',
      privacy: 'Maxfiylik siyosati',
      privacyNote: 'Ma’lumotlaringiz faqat demo so‘rovini ko‘rib chiqish uchun ishlatiladi.',
    },
    legal: {
      privacy: 'Maxfiylik siyosati',
      terms: 'Foydalanish shartlari',
      updated: 'Oxirgi yangilanish: 2026-yil sentabr',
      back: 'Bosh sahifaga qaytish',
      operator: 'Radix CRM operatori',
      privacySections: [
        {
          title: 'Qanday ma’lumot yig‘amiz',
          text: 'Demo formasida ism, telefon, bog‘cha nomi, bolalar soni, hudud va ixtiyoriy izohni yig‘amiz.',
        },
        {
          title: 'Nima uchun ishlatamiz',
          text: 'Zayavkani ko‘rib chiqish, demo tashkil qilish va Radix CRM bo‘yicha bog‘lanish uchun.',
        },
        {
          title: 'Saqlash va uzatish',
          text: 'Forma ma’lumotlari platforma bazasida saqlanadi. Uchinchi tomon bildirishnomasi yoki analytics xizmati ma’lumotlar oqimiga qo‘shilmaydi, agar bu siyosatda oldindan ko‘rsatilmasa.',
        },
        {
          title: 'Sizning tanlovingiz',
          text: 'Rozilik ixtiyoriy, ammo zayavkani ko‘rib chiqish uchun zarur. Ma’lumotlaringiz bo‘yicha murojaat qilish uchun operatorning rasmiy aloqa kanali launchdan oldin e’lon qilinadi.',
        },
      ],
      termsSections: [
        {
          title: 'Xizmat tavsifi',
          text: 'Radix CRM xususiy bog‘chalar uchun boshqaruv platformasidir. Demo formasi hisob ochish yoki shartnoma tuzish emas.',
        },
        {
          title: 'Narxlar',
          text: 'Landingdagi kalkulyator joriy subscription plan asosidagi yo‘naltiruvchi hisobdir. Majburiyat faqat rasmiy shartnoma va hisob-faktura bilan yuzaga keladi.',
        },
        {
          title: 'Kirish va foydalanish',
          text: 'CRM hisobi platforma jamoasi tomonidan sotuv suhbatidan keyin yaratiladi. Har bir tashkilot o‘z xodimlari kirishini boshqaradi.',
        },
      ],
    },
    footer: {
      product: 'Xususiy bog‘chalar uchun boshqaruv platformasi.',
      privacy: 'Maxfiylik siyosati',
      terms: 'Foydalanish shartlari',
      login: 'CRM‘ga kirish',
      copyright: '© 2026 Radix CRM. Barcha huquqlar himoyalangan.',
    },
    seo: {
      title: 'Radix CRM — Xususiy bog‘chalarni boshqarish tizimi',
      description: 'Xususiy bog‘chalar uchun bolalar, davomat, to‘lovlar, qarzdorlik, xodimlar va hisobotlarni yagona tizimda boshqarish.',
    },
  },

  ru: {
    nav: {
      product: 'Продукт',
      capabilities: 'Возможности',
      pricing: 'Тарифы',
      faq: 'Вопросы',
      login: 'Войти в CRM',
      demo: 'Получить демо',
      switchLabel: 'O‘zbekcha',
      switchShort: 'UZ',
      menuOpen: 'Открыть меню',
      menuClose: 'Закрыть меню',
    },
    hero: {
      eyebrow: 'Платформа управления для частных детских садов',
      title: 'Всё управление детским садом — в одной системе.',
      text: 'Дети, посещаемость, платежи, задолженность, сотрудники, расходы и отчёты — на одной платформе.',
      primary: 'Получить демо',
      secondary: 'Посмотреть возможности',
      note: 'Неограниченное число филиалов и сотрудников — оплата только по количеству детей.',
      priceNote: 'до {children} детей — от {amount} в месяц',
    },
    proof: 'Вместо бумажных журналов, Excel и разрозненных чатов — один источник управления.',
    problems: {
      eyebrow: 'Ежедневный хаос',
      title: 'Важная для руководителя информация не должна быть разбросана по разным местам.',
      items: [
        'Платежи в одном месте, посещаемость в другом, отчёты в Excel.',
        'Задолженность считается вручную — появляются ошибки и задержки.',
        'Сотрудники, зарплаты, расходы и склад не видны в одной картине.',
        'Подготовка отчётов отнимает время и задерживает решения.',
      ],
      bridge: 'Всё это Radix собирает в одну систему.',
    },
    solution: {
      eyebrow: 'Единый центр управления',
      title: 'Операционная работа и финансовый контроль в одной системе.',
      text: 'Radix поддерживает ежедневные задачи команды по ролям и даёт руководителю целостную картину, близкую к реальному времени.',
    },
    featureTitle: 'Готовые модули для ключевых направлений работы детского сада.',
    features: [
      {
        title: 'Дети и группы',
        text: 'Данные каждого ребёнка и опекуна в одном месте. Создавайте группы, зачисляйте детей, загрузите существующий список из Excel один раз.',
      },
      {
        title: 'Платежи и задолженность',
        text: 'Контролируйте платежи, задолженность и финансовую историю каждого ребёнка из одного места. Список должников формируется сам.',
      },
      {
        title: 'Посещаемость',
        text: 'Отмечайте ежедневную посещаемость по группе за несколько секунд и смотрите месячную сводку в отчёте.',
      },
      {
        title: 'Сотрудники и зарплаты',
        text: 'Сотрудники, должности и расчёт зарплаты — с историей. Расчёт за месяц потом не меняется.',
      },
      {
        title: 'Склад и расходы',
        text: 'Контролируйте остатки, приход-расход и расходы — товары на исходе видны сами.',
      },
      {
        title: 'Отчёты и аудит',
        text: 'Нужные руководителю цифры на одном экране, отчёты выгружаются в CSV, каждое действие остаётся в журнале.',
      },
    ],
    preview: {
      eyebrow: 'Вид продукта',
      title: 'Цифры, которые нужны руководителю, — на одном экране.',
      text: 'Контролируйте текущее состояние, финансовые показатели и ключевые операционные процессы одним взглядом. Вид основан на реальной структуре dashboard Radix.',
      sample: 'Пример',
      live: 'Ключевые показатели',
      revenue: 'Выручка за месяц',
      debt: 'Задолженность',
      attendance: 'Посещаемость сегодня',
      children: 'Активные дети',
      tasksTitle: 'Задачи на сегодня',
      tasks: ['Завершить посещаемость', 'Проверить задолженность', 'Проверить остатки склада'],
      nav: ['Дашборд', 'Дети', 'Платежи', 'Посещаемость', 'Отчёты'],
      active: 'Активно',
      finance: 'Финансовая динамика',
      recent: 'Последние платежи',
    },
    roles: {
      eyebrow: 'Для кого',
      title: 'Для кого Radix?',
      text: 'Каждый сотрудник видит возможности своей роли — и ничего лишнего.',
      items: [
        {
          role: 'Владелец сада',
          text: 'Финансы, сотрудники и все филиалы — одним взглядом. Подпиской и ролями управляете сами.',
        },
        {
          role: 'Директор',
          text: 'Ежедневная операционная работа из одной системы: дети, посещаемость, платежи, сотрудники, отчёты.',
        },
        {
          role: 'Кассир',
          text: 'Принимайте платежи, точно ведите задолженность. Каждый платёж оставляет след в ledger.',
        },
        {
          role: 'Менеджер',
          text: 'Дети, группы, посещаемость и склад в порядке — без доступа к финансовым данным.',
        },
      ],
    },
    steps: {
      eyebrow: 'Как начать',
      title: 'От разговора о продажах к ежедневному управлению.',
      items: [
        { title: 'Оставьте заявку', text: 'Укажите потребности сада и количество детей.' },
        {
          title: 'Мы откроем организацию',
          text: 'Команда платформы безопасно создаст организацию, первый филиал и владельца.',
        },
        {
          title: 'Загрузите данные',
          text: 'Импортируйте список детей, настройте группы и сотрудников.',
        },
        {
          title: 'Начните управлять',
          text: 'Управляйте посещаемостью, финансами и операционной работой каждый день.',
        },
      ],
    },
    pricing: {
      eyebrow: 'Простые и понятные тарифы',
      title: 'Сколько это стоит для вашего сада?',
      text: 'Одна подписка включает все филиалы и сотрудников. Цена зависит от максимального числа детей.',
      monthly: 'Помесячно',
      annual: 'За год',
      saving: 'Экономия при годовой оплате',
      before: 'Годовая сумма без скидки',
      children: 'Количество детей',
      childrenUnit: 'детей',
      sliderLabel: 'Настроить количество детей ползунком',
      perMonth: 'сум / месяц',
      perYear: 'сум / год',
      perChild: 'за ребёнка в месяц',
      effectiveMonthly: 'в месяц при годовой оплате',
      discountBadge: 'скидка 25%',
      policy: 'В течение первых 3 месяцев действуют текущие тарифы. С добавлением новых возможностей и услуг тарифы в будущем могут обновляться.',
      disclaimer: 'Калькулятор — ориентировочный расчёт по текущему тарифу. Итоговая сумма определяется официальным договором и счётом-фактурой.',
      loading: 'Расчёт…',
      error: 'Не удалось загрузить расчёт. Попробуйте ещё раз.',
    },
    delivery: {
      eyebrow: 'Две модели работы',
      title: 'Облачная подписка или установка на вашем сервере — выбор за вами.',
      text: 'Продукт в обоих случаях один и тот же: те же модули, те же возможности. Разница только в том, где работает система и как вы платите.',
      plans: [
        {
          id: 'cloud',
          badge: 'Выбирают чаще',
          name: 'Облачная подписка',
          price: 'от 400 000 сум',
          priceNote: 'в месяц, до 50 детей',
          text: 'Сервер, обновления и резервные копии — на нас. Вы просто управляете садом.',
          points: [
            'Запуск за несколько минут — установка не нужна',
            '15 дней бесплатно, карта не требуется',
            'Обновления автоматические и бесплатные',
            'Резервные копии, мониторинг и поддержка на нас',
            'Неограниченно филиалов и сотрудников',
          ],
          cta: 'Получить демо',
          href: '#demo',
        },
        {
          id: 'onprem',
          badge: 'Разовый платёж',
          name: 'Отдельная установка',
          price: 'По договорённости',
          priceNote: 'разовый платёж, без абонплаты',
          text: 'Система полностью ваша: на вашем сервере, на вашем домене, без подписки.',
          points: [
            'Данные полностью остаются на вашем сервере',
            'Нет ежемесячной подписки — платите один раз',
            'Работает на вашем домене',
            'Установку и настройку выполняем мы',
            'Обновления устанавливаются по договорённости',
          ],
          cta: 'Узнать цену',
          href: '#demo',
        },
      ],
      note: 'Не знаете, какая модель подойдёт? Оставьте заявку — подскажем, исходя из размера сада и ваших требований.',
    },
    security: {
      eyebrow: 'Безопасность данных',
      title: 'Мы ответственно относимся к вашим данным.',
      points: [
        {
          title: 'Доступ по ролям',
          text: 'Каждый сотрудник видит только разделы своей роли. Правами управляет владелец организации.',
        },
        {
          title: 'Изоляция организаций',
          text: 'Данные каждого сада изолированы на уровне приложения и базы данных — другая организация никогда их не увидит.',
        },
        {
          title: 'Журнал аудита',
          text: 'Кто, что и когда изменил — хранится в неизменяемом журнале.',
        },
      ],
    },
    faq: {
      eyebrow: 'Вопросы и ответы',
      title: 'Главное для принятия решения.',
      items: [
        {
          title: 'Что такое Radix CRM?',
          text: 'Платформа управления для частных детских садов: дети, группы, посещаемость, платежи, задолженность, сотрудники, зарплаты, расходы, склад и отчёты — в одной системе.',
        },
        {
          title: 'Для кого Radix CRM?',
          text: 'Для частных детских садов Узбекистана, включая организации с несколькими филиалами.',
        },
        {
          title: 'Как рассчитывается цена?',
          text: 'До 50 детей — 400 000 сум в месяц. Свыше 50 добавляется 50 000 сум за каждый начатый блок из 10 детей: 51–60 детей — 450 000 сум.',
        },
        {
          title: 'Есть ли скидка за годовую оплату?',
          text: 'Да. Годовая оплата рассчитывается со скидкой 25% от суммы за 12 месяцев.',
        },
        {
          title: 'Как работают первые 3 месяца?',
          text: 'Первые три месяца действуют текущие тарифы. Последующие изменения могут быть связаны с добавлением новых возможностей платформы.',
        },
        {
          title: 'Чем отличается облачная подписка от отдельной установки?',
          text: 'Продукт один и тот же. В облаке система работает на нашем сервере, и вы платите ежемесячно. При отдельной установке система разворачивается на вашем сервере, оплата разовая, ежемесячной подписки нет. Цена определяется по договорённости.',
        },
        {
          title: 'Насколько защищены данные?',
          text: 'Система использует доступ по ролям, изоляцию организаций (в том числе на уровне базы данных) и неизменяемый журнал аудита.',
        },
        {
          title: 'Как начать?',
          text: 'Запросите демо. После разговора команда платформы откроет вашу организацию, и вы начнёте загружать данные.',
        },
      ],
    },
    form: {
      eyebrow: 'Демо для вашего сада',
      closing: 'Готовы упростить управление детским садом?',
      title: 'Начните работать с Radix CRM.',
      text: 'Оставьте короткую информацию о саде — мы свяжемся с вами и покажем систему.',
      name: 'Ваше имя',
      phone: 'Номер телефона',
      kindergarten: 'Название сада',
      children: 'Количество детей',
      city: 'Город / регион',
      message: 'Комментарий (необязательно)',
      consent: 'Я согласен(-на) на обработку персональных данных в соответствии с Политикой конфиденциальности.',
      submit: 'Запросить демо',
      sending: 'Отправка…',
      success: 'Спасибо. Ваш запрос принят — скоро свяжемся.',
      error: 'Не удалось отправить запрос. Проверьте поля и попробуйте снова.',
      privacy: 'Политика конфиденциальности',
      privacyNote: 'Ваши данные используются только для обработки запроса на демо.',
    },
    legal: {
      privacy: 'Политика конфиденциальности',
      terms: 'Условия использования',
      updated: 'Последнее обновление: сентябрь 2026',
      back: 'Вернуться на главную',
      operator: 'Оператор Radix CRM',
      privacySections: [
        {
          title: 'Какие данные мы собираем',
          text: 'В форме демо мы собираем имя, телефон, название сада, число детей, регион и необязательный комментарий.',
        },
        {
          title: 'Для чего используем',
          text: 'Для обработки заявки, организации демо и связи по поводу Radix CRM.',
        },
        {
          title: 'Хранение и передача',
          text: 'Данные формы хранятся в базе платформы. Сторонние сервисы уведомлений или аналитики не включаются в поток данных, если это не указано заранее в этой политике.',
        },
        {
          title: 'Ваш выбор',
          text: 'Согласие добровольно, но необходимо для обработки заявки. Официальный канал связи оператора будет опубликован до запуска.',
        },
      ],
      termsSections: [
        {
          title: 'Описание сервиса',
          text: 'Radix CRM — платформа управления для частных детских садов. Форма демо не создаёт учётную запись и не заключает договор.',
        },
        {
          title: 'Тарифы',
          text: 'Калькулятор на landing page является ориентировочным расчётом по текущему subscription plan. Обязательства возникают только по официальному договору и счёту-фактуре.',
        },
        {
          title: 'Доступ и использование',
          text: 'Учётная запись CRM создаётся командой платформы после разговора о продажах. Каждая организация управляет доступом своих сотрудников.',
        },
      ],
    },
    footer: {
      product: 'Платформа управления для частных детских садов.',
      privacy: 'Политика конфиденциальности',
      terms: 'Условия использования',
      login: 'Войти в CRM',
      copyright: '© 2026 Radix CRM. Все права защищены.',
    },
    seo: {
      title: 'Radix CRM — Система управления частным детским садом',
      description: 'Управление детьми, посещаемостью, платежами, задолженностью, сотрудниками и отчётами частного детского сада в одной системе.',
    },
  },
}
