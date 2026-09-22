/**
 * Huquqiy sahifalar matni (maxfiylik siyosati, foydalanish shartlari).
 *
 * Eski landing content'idan ajratib olingan — sotuv sahifasi endi
 * `features/landing` da, bu yerda faqat huquqiy matn qoldi.
 */

export type Locale = 'uz' | 'ru' | 'en'

export interface LegalSection {
  title: string
  text: string
}

export interface LegalCopy {
  privacy: string
  terms: string
  updated: string
  back: string
  privacySections: LegalSection[]
  termsSections: LegalSection[]
  operator: string
}

export const legal: Record<Locale, LegalCopy> = {
  uz: {
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
  ru: {
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
  en: {
    privacy: 'Privacy Policy',
    terms: 'Terms of Use',
    updated: 'Last updated: September 2026',
    back: 'Back to the home page',
    operator: 'Radix CRM operator',
    privacySections: [
      {
        title: 'What data we collect',
        text: 'In the demo form we collect your name, phone number, kindergarten name, number of children, region and an optional comment.',
      },
      {
        title: 'What we use it for',
        text: 'To review your request, arrange a demo and get in touch about Radix CRM.',
      },
      {
        title: 'Storage and transfer',
        text: 'Form data is stored in the platform database. No third-party notification or analytics service is added to the data flow unless this policy says so in advance.',
      },
      {
        title: 'Your choice',
        text: 'Consent is voluntary but required to review the request. The operator’s official contact channel for questions about your data will be published before launch.',
      },
    ],
    termsSections: [
      {
        title: 'Service description',
        text: 'Radix CRM is a management platform for private kindergartens. The demo form does not open an account or conclude a contract.',
      },
      {
        title: 'Pricing',
        text: 'The calculator on the website is an indicative estimate based on the current subscription plan. Obligations arise only under an official contract and invoice.',
      },
      {
        title: 'Access and use',
        text: 'A CRM account is created by the platform team after a sales conversation. Each organization manages access for its own staff.',
      },
    ],
  },
}
