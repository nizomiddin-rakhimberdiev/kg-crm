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

export const copy: Record<Locale, {
  nav: { product: string; capabilities: string; pricing: string; faq: string; login: string; demo: string }
  hero: { eyebrow: string; title: string; text: string; primary: string; secondary: string; note: string }
  proof: string
  problems: { eyebrow: string; title: string; items: string[] }
  solution: { eyebrow: string; title: string; text: string }
  featureTitle: string
  features: Feature[]
  preview: { eyebrow: string; title: string; text: string; live: string; revenue: string; debt: string; attendance: string; children: string }
  steps: { eyebrow: string; title: string; items: Feature[] }
  pricing: { eyebrow: string; title: string; text: string; monthly: string; annual: string; saving: string; before: string; children: string; perMonth: string; policy: string; disclaimer: string; loading: string }
  delivery: {
    eyebrow: string
    title: string
    text: string
    plans: DeliveryPlan[]
    note: string
  }
  faq: { eyebrow: string; title: string; items: Feature[] }
  form: { eyebrow: string; title: string; text: string; name: string; phone: string; kindergarten: string; children: string; city: string; message: string; consent: string; submit: string; sending: string; success: string; error: string; privacy: string }
  legal: { privacy: string; terms: string; updated: string; back: string; privacySections: Feature[]; termsSections: Feature[]; operator: string }
  footer: { product: string; privacy: string; terms: string; login: string; copyright: string }
}> = {
  uz: {
    nav: { product: 'Mahsulot', capabilities: 'Imkoniyatlar', pricing: 'Narxlar', faq: 'Savollar', login: "CRM'ga kirish", demo: 'Demo olish' },
    hero: { eyebrow: 'Xususiy bog‘chalar uchun SaaS boshqaruv platformasi', title: 'Bog‘changiz boshqaruvini bitta aniq tizimga jamlang.', text: 'Radix CRM bolalar, to‘lovlar, davomat, xodimlar, xarajatlar va hisobotlarni kundalik ish ritmingizga mos yagona markazda birlashtiradi.', primary: 'Demo olish', secondary: 'Imkoniyatlarni ko‘rish', note: 'Cheksiz filial va xodim — to‘lov faqat bolalar soniga qarab.' },
    proof: 'Qog‘oz daftar, Excel va alohida chatlar o‘rniga — yagona boshqaruv manbai.',
    problems: { eyebrow: 'Kundalik tartibsizlik', title: 'Rahbar nazorat qilishi kerak bo‘lgan ishlar turli joylarga sochilib ketmasin.', items: ['Bolalar va ota-onalar ma’lumoti daftarlar hamda fayllarda qolib ketadi.', 'To‘lov va qarzdorlikni qo‘lda hisoblash xato hamda kechikish tug‘diradi.', 'Davomat, ish haqi, xarajat va ombor holatini bir manzarada ko‘rish qiyin.', 'Hisobot tayyorlash vaqt oladi, qaror esa kechikadi.'] },
    solution: { eyebrow: 'Bitta boshqaruv markazi', title: 'Operatsion ish va moliyaviy nazorat bir tizimda.', text: 'Radix CRM bog‘cha jamoasining kundalik vazifalarini rolga mos boshqaradi, rahbarga esa real vaqtga yaqin umumiy ko‘rinish beradi.' },
    featureTitle: 'Bog‘cha ishining asosiy yo‘nalishlari uchun tayyor modullar.',
    features: [
      { title: 'Bolalar va guruhlar', text: 'Bola va vasiy profillari, guruhlar, ro‘yxatga olish hamda CSV/XLSX import.' },
      { title: 'To‘lovlar va qarzdorlik', text: 'Tariflar, hisoblar, to‘lov qabul qilish, ledger va qarzdorlar ko‘rinishi.' },
      { title: 'Davomat', text: 'Guruh bo‘yicha kundalik jurnal va oylik davomat xulosasi.' },
      { title: 'Xodimlar va ish haqi', text: 'Rollar, xodimlar, lavozimlar, payroll run va hisob-kitob tarixi.' },
      { title: 'Ombor va xarajatlar', text: 'Mahsulot, kirim-chiqim, qoldiq, yetkazib beruvchi va xarajatlar nazorati.' },
      { title: 'Hisobot va audit', text: 'Dashboard KPIlari, CSV eksportlar, bildirishnomalar va amallar tarixi.' },
    ],
    preview: { eyebrow: 'Real mahsulot ko‘rinishi', title: 'Rahbar ko‘rishi kerak bo‘lgan raqamlar — bir ekranda.', text: 'Quyidagi ko‘rinish Radix CRM’dagi mavjud boshqaruv modullari va dashboard tuzilmasiga asoslangan.', live: 'Jonli ko‘rsatkichlar', revenue: 'Oy tushumi', debt: 'Qarzdorlik', attendance: 'Bugungi davomat', children: 'Faol bolalar' },
    steps: { eyebrow: 'Boshlash jarayoni', title: 'Sotuv suhbatidan kundalik boshqaruvgacha.', items: [ { title: '01 — Demo so‘rang', text: 'Bog‘changiz ehtiyoji va bolalar sonini qoldiring.' }, { title: '02 — Tashkilotni ochamiz', text: 'Platforma admini tashkilot, dastlabki filial va egani xavfsiz yaratadi.' }, { title: '03 — Ma’lumotlarni yuklang', text: 'Bolalar ro‘yxatini import qiling, guruh va xodimlarni sozlang.' }, { title: '04 — Yagona tizimda ishlang', text: 'Davomat, moliya va operatsion holatni kundalik boshqaring.' } ] },
    pricing: { eyebrow: 'Sodda va tushunarli narxlash', title: 'Bog‘changiz hajmiga mos hisob.', text: 'Bitta obuna barcha filiallar va xodimlarni qamrab oladi. Narx bolalarning eng yuqori soni asosida hisoblanadi.', monthly: 'Oyiga', annual: 'Yiliga', saving: 'Yillik tejov', before: 'Chegirmasiz yillik summa', children: 'Bog‘changizda nechta bola bor?', perMonth: 'so‘m / oy', policy: 'Dastlabki 3 oy davomida joriy tariflar amal qiladi. Keyinchalik xizmat ko‘lami va imkoniyatlar kengayishi bilan tariflar yangilanishi mumkin.', disclaimer: 'Tariflar platformaning joriy imkoniyatlari va xizmat ko‘lami asosida shakllantirilgan. Yakuniy hisob amaldagi subscription plan va rasmiy hisob-fakturaga muvofiq belgilanadi.', loading: 'Hisoblanmoqda…' },
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
    faq: { eyebrow: 'Savollar va javoblar', title: 'Qaror qabul qilish uchun kerakli asosiy ma’lumotlar.', items: [ { title: 'Radix CRM kimlar uchun?', text: 'O‘zbekistondagi xususiy bog‘chalar va bir nechta filiali bo‘lgan tashkilotlar uchun.' }, { title: 'Bulutli obuna va alohida o‘rnatma farqi nima?', text: 'Mahsulot bir xil. Bulutli obunada tizim bizning serverimizda ishlaydi va siz oyiga to‘laysiz. Alohida o‘rnatmada tizim sizning serveringizga o‘rnatiladi, bir martalik to‘lov olinadi va oylik obuna bo‘lmaydi. Narx kelishuv asosida belgilanadi.' }, { title: 'Narx qanday hisoblanadi?', text: '50 tagacha bola uchun oyiga 400 000 so‘m. 50 dan oshganda har boshlangan 10 bola uchun 50 000 so‘m qo‘shiladi: 51–60 bola — 450 000 so‘m.' }, { title: 'Yillik to‘lovda chegirma bormi?', text: 'Ha. Yillik to‘lov 12 oylik summadan 25% chegirma bilan hisoblanadi.' }, { title: 'Birinchi 3 oy nimani anglatadi?', text: 'Dastlabki uch oyda hozirgi tariflar amal qiladi. Keyingi narx o‘zgarishlari xizmat ko‘lami kengayishiga bog‘liq bo‘lishi mumkin.' }, { title: 'Ma’lumotlar xavfsizmi?', text: 'Tizim rollar, tenant izolyatsiyasi, audit va bazadagi RLS qatlamlari bilan ishlaydi. Aniq hosting va data-residency talablari launchdan oldin rasmiylashtiriladi.' }, { title: 'Qanday boshlayman?', text: 'Zayavka qoldiring. Demo va sotuv suhbatidan so‘ng platforma jamoasi tashkilotingizni ochadi.' } ] },
    form: { eyebrow: 'Bog‘changiz uchun demo', title: 'Radix CRM bilan ishlashni boshlang.', text: 'Qisqa ma’lumot qoldiring — platforma jamoasi demo va ulash jarayoni bo‘yicha bog‘lanadi.', name: 'Ismingiz', phone: 'Telefon raqam', kindergarten: 'Bog‘cha nomi', children: 'Bolalar soni', city: 'Shahar / hudud', message: 'Izoh (ixtiyoriy)', consent: 'Shaxsiy ma’lumotlarimga Maxfiylik siyosatiga muvofiq ishlov berilishiga roziman.', submit: 'Zayavka yuborish', sending: 'Yuborilmoqda…', success: 'Rahmat. Zayavkangiz qabul qilindi.', error: 'Zayavkani yuborib bo‘lmadi. Maydonlarni tekshirib, qayta urinib ko‘ring.', privacy: 'Maxfiylik siyosati' },
    legal: { privacy: 'Maxfiylik siyosati', terms: 'Foydalanish shartlari', updated: 'Oxirgi yangilanish: 2026-yil sentabr', back: 'Bosh sahifaga qaytish', operator: 'Radix CRM operatori', privacySections: [ { title: 'Qanday ma’lumot yig‘amiz', text: 'Demo formasida ism, telefon, bog‘cha nomi, bolalar soni, hudud va ixtiyoriy izohni yig‘amiz.' }, { title: 'Nima uchun ishlatamiz', text: 'Zayavkani ko‘rib chiqish, demo tashkil qilish va Radix CRM bo‘yicha bog‘lanish uchun.' }, { title: 'Saqlash va uzatish', text: 'Forma ma’lumotlari platforma bazasida saqlanadi. Uchinchi tomon bildirishnomasi yoki analytics xizmati ma’lumotlar oqimiga qo‘shilmaydi, agar bu siyosatda oldindan ko‘rsatilmasa.' }, { title: 'Sizning tanlovingiz', text: 'Rozilik ixtiyoriy, ammo zayavkani ko‘rib chiqish uchun zarur. Ma’lumotlaringiz bo‘yicha murojaat qilish uchun operatorning rasmiy aloqa kanali launchdan oldin e’lon qilinadi.' } ], termsSections: [ { title: 'Xizmat tavsifi', text: 'Radix CRM xususiy bog‘chalar uchun boshqaruv platformasidir. Demo formasi hisob ochish yoki shartnoma tuzish emas.' }, { title: 'Narxlar', text: 'Landingdagi kalkulyator joriy subscription plan asosidagi yo‘naltiruvchi hisobdir. Majburiyat faqat rasmiy shartnoma va hisob-faktura bilan yuzaga keladi.' }, { title: 'Kirish va foydalanish', text: 'CRM hisobi platforma jamoasi tomonidan sotuv suhbatidan keyin yaratiladi. Har bir tashkilot o‘z xodimlari kirishini boshqaradi.' } ] },
    footer: { product: 'Xususiy bog‘chalar uchun boshqaruv platformasi.', privacy: 'Maxfiylik siyosati', terms: 'Foydalanish shartlari', login: "CRM'ga kirish", copyright: '© 2026 Radix CRM. Barcha huquqlar himoyalangan.' },
  },
  ru: {
    nav: { product: 'Продукт', capabilities: 'Возможности', pricing: 'Тарифы', faq: 'Вопросы', login: 'Войти в CRM', demo: 'Получить демо' },
    hero: { eyebrow: 'SaaS-платформа управления для частных детских садов', title: 'Соберите управление детским садом в одной понятной системе.', text: 'Radix CRM объединяет детей, платежи, посещаемость, сотрудников, расходы и отчёты в едином центре, соответствующем ежедневному ритму вашей команды.', primary: 'Получить демо', secondary: 'Посмотреть возможности', note: 'Неограниченное число филиалов и сотрудников — оплата только по количеству детей.' },
    proof: 'Вместо бумажных журналов, Excel и разрозненных чатов — единый источник управления.',
    problems: { eyebrow: 'Ежедневный хаос', title: 'Важная для руководителя информация не должна быть разбросана по разным местам.', items: ['Данные о детях и родителях остаются в журналах и файлах.', 'Ручной учёт платежей и задолженности создаёт ошибки и задержки.', 'Сложно видеть посещаемость, зарплаты, расходы и склад в одной картине.', 'Подготовка отчётов отнимает время и задерживает решения.'] },
    solution: { eyebrow: 'Единый центр управления', title: 'Операционная работа и финансовый контроль в одной системе.', text: 'Radix CRM поддерживает ежедневные задачи команды по ролям и даёт руководителю целостную картину в реальном времени.' },
    featureTitle: 'Готовые модули для ключевых направлений работы детского сада.',
    features: [
      { title: 'Дети и группы', text: 'Карточки детей и опекунов, группы, зачисление и импорт CSV/XLSX.' },
      { title: 'Платежи и задолженность', text: 'Тарифы, счета, приём платежей, ledger и список должников.' },
      { title: 'Посещаемость', text: 'Ежедневный журнал по группам и месячная сводка.' },
      { title: 'Сотрудники и зарплаты', text: 'Роли, сотрудники, должности, payroll run и история расчётов.' },
      { title: 'Склад и расходы', text: 'Товары, приход-расход, остатки, поставщики и контроль расходов.' },
      { title: 'Отчёты и аудит', text: 'KPI на dashboard, CSV-экспорт, уведомления и история действий.' },
    ],
    preview: { eyebrow: 'Реальный вид продукта', title: 'Цифры, которые нужны руководителю, — на одном экране.', text: 'Этот вид основан на существующих модулях управления и структуре dashboard Radix CRM.', live: 'Текущие показатели', revenue: 'Выручка за месяц', debt: 'Задолженность', attendance: 'Посещаемость сегодня', children: 'Активные дети' },
    steps: { eyebrow: 'Как начать', title: 'От разговора о продажах к ежедневному управлению.', items: [ { title: '01 — Оставьте заявку', text: 'Укажите потребности сада и количество детей.' }, { title: '02 — Мы откроем организацию', text: 'Администратор платформы безопасно создаст организацию, первый филиал и владельца.' }, { title: '03 — Загрузите данные', text: 'Импортируйте список детей, настройте группы и сотрудников.' }, { title: '04 — Работайте в единой системе', text: 'Управляйте посещаемостью, финансами и операционной работой каждый день.' } ] },
    pricing: { eyebrow: 'Простые и понятные тарифы', title: 'Расчёт под размер вашего сада.', text: 'Одна подписка включает все филиалы и сотрудников. Цена зависит от максимального числа детей.', monthly: 'В месяц', annual: 'В год', saving: 'Экономия за год', before: 'Годовая сумма без скидки', children: 'Сколько детей в вашем саду?', perMonth: 'сум / месяц', policy: 'В течение первых 3 месяцев действуют текущие тарифы. В дальнейшем тарифы могут обновляться с расширением возможностей и объёма сервиса.', disclaimer: 'Тарифы сформированы на основе текущих возможностей и объёма сервиса. Итоговый счёт определяется действующим subscription plan и официальным счётом-фактурой.', loading: 'Расчёт…' },
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
    faq: { eyebrow: 'Вопросы и ответы', title: 'Главное для принятия решения.', items: [ { title: 'Для кого Radix CRM?', text: 'Для частных детских садов Узбекистана, включая организации с несколькими филиалами.' }, { title: 'Чем отличается облачная подписка от отдельной установки?', text: 'Продукт один и тот же. В облаке система работает на нашем сервере, и вы платите ежемесячно. При отдельной установке система разворачивается на вашем сервере, оплата разовая, ежемесячной подписки нет. Цена определяется по договорённости.' }, { title: 'Как рассчитывается цена?', text: 'До 50 детей — 400 000 сум в месяц. Свыше 50 добавляется 50 000 сум за каждый начатый блок из 10 детей: 51–60 детей — 450 000 сум.' }, { title: 'Есть ли скидка за годовую оплату?', text: 'Да. Годовая оплата рассчитывается со скидкой 25% от суммы за 12 месяцев.' }, { title: 'Что означают первые 3 месяца?', text: 'Первые три месяца действуют текущие тарифы. Последующие изменения возможны при расширении сервиса.' }, { title: 'Насколько защищены данные?', text: 'Система использует роли, изоляцию tenants, аудит и RLS на уровне базы. Требования к хостингу и data-residency формализуются до запуска.' }, { title: 'Как начать?', text: 'Оставьте заявку. После демо и разговора о продажах команда платформы откроет вашу организацию.' } ] },
    form: { eyebrow: 'Демо для вашего сада', title: 'Начните работать с Radix CRM.', text: 'Оставьте короткую информацию — команда платформы свяжется с вами по демо и подключению.', name: 'Ваше имя', phone: 'Номер телефона', kindergarten: 'Название сада', children: 'Количество детей', city: 'Город / регион', message: 'Комментарий (необязательно)', consent: 'Я согласен(-на) на обработку персональных данных в соответствии с Политикой конфиденциальности.', submit: 'Отправить заявку', sending: 'Отправка…', success: 'Спасибо. Ваша заявка принята.', error: 'Не удалось отправить заявку. Проверьте поля и попробуйте снова.', privacy: 'Политика конфиденциальности' },
    legal: { privacy: 'Политика конфиденциальности', terms: 'Условия использования', updated: 'Последнее обновление: сентябрь 2026', back: 'Вернуться на главную', operator: 'Оператор Radix CRM', privacySections: [ { title: 'Какие данные мы собираем', text: 'В форме демо мы собираем имя, телефон, название сада, число детей, регион и необязательный комментарий.' }, { title: 'Для чего используем', text: 'Для обработки заявки, организации демо и связи по поводу Radix CRM.' }, { title: 'Хранение и передача', text: 'Данные формы хранятся в базе платформы. Сторонние сервисы уведомлений или аналитики не включаются в поток данных, если это не указано заранее в этой политике.' }, { title: 'Ваш выбор', text: 'Согласие добровольно, но необходимо для обработки заявки. Официальный канал связи оператора будет опубликован до запуска.' } ], termsSections: [ { title: 'Описание сервиса', text: 'Radix CRM — платформа управления для частных детских садов. Форма демо не создаёт учётную запись и не заключает договор.' }, { title: 'Тарифы', text: 'Калькулятор на landing page является ориентировочным расчётом по текущему subscription plan. Обязательства возникают только по официальному договору и счёту-фактуре.' }, { title: 'Доступ и использование', text: 'Учётная запись CRM создаётся командой платформы после разговора о продажах. Каждая организация управляет доступом своих сотрудников.' } ] },
    footer: { product: 'Платформа управления для частных детских садов.', privacy: 'Политика конфиденциальности', terms: 'Условия использования', login: 'Войти в CRM', copyright: '© 2026 Radix CRM. Все права защищены.' },
  },
}
