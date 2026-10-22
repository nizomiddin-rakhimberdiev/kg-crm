/**
 * Huquqiy sahifalar matni — maxfiylik siyosati va foydalanish shartlari
 * (PLAN 5.8).
 *
 * Matnda `{{…}}` belgilari bor: `{{YURIDIK_NOM}}`, `{{STIR}}`,
 * `{{MANZIL}}`, `{{SERVER_JOYLASHUVI}}` — `.env` dagi `VITE_LEGAL_*`
 * qiymatlari bilan `fillLegal()` toʻldiradi. Qiymat boʻsh boʻlsa belgi
 * ATAYLAB koʻrinib qoladi: yuridik hujjatda "operator" qatorining
 * jimgina yoʻqolishi uning toʻgʻri koʻrinishidan yomonroq — chala hujjat
 * chala koʻrinishi kerak. `prerender.mjs` bunday sahifa uchun
 * ogohlantirish chiqaradi.
 *
 * Aloqa (`{{EMAIL}}`, `{{TELEGRAM}}`, `{{TELEFON}}`) har doim
 * `config/contact.ts` dan.
 *
 * Bu matnlar yurist tekshiruvidan oʻtmagan — bu eslatma sahifada emas,
 * hisobotda (brief, 5.8).
 */

import { CONTACT, formatPhone } from '@/config/contact'
import { env } from '@/config/env'

export type Locale = 'uz' | 'ru' | 'en'

export interface LegalSection {
  title: string
  /** Xatboshilar `\n` bilan ajratiladi. */
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

/**
 * Siyosat versiyasi — demo formasidagi rozilik shu versiya bilan
 * saqlanadi (`lead.privacy_policy_version`). Matn mazmunan oʻzgarsa —
 * versiya ham oʻzgaradi, aks holda kim qaysi matnga rozi boʻlgani
 * aniqlanmaydi.
 */
export const POLICY_VERSION = '2026-10-03'

/**
 * `{{…}}` belgilarini toʻldiradi; **toʻldirilmagani bor gap tushib
 * qoladi**.
 *
 * Avval belgi EKRANDA qolardi — "chala hujjat chala koʻrinsin" degan
 * qaror bilan. Mustaqil audit (2026-10-21) buning narxini oʻlchadi:
 * saytga kirgan direktor "{{STIR}}" ni koʻrib "tizim hali tayyor
 * emas" degan xulosaga keladi. Ya'ni ogohlantirish MIJOZGA ketardi,
 * bizga emas. Chala ekanini endi `scripts/deploy.sh` bizga aytadi.
 *
 * Gap tushib qolishi — yashirish emas: operatorning nomi yoki
 * serverlar joylashuvi haqida **noma'lum** gapni yozib qoʻyish undan
 * ham yomon (docs/01 §10 — joylashuv ishga tushirish shartlaridan).
 */
export function fillLegal(text: string): string {
  const values: Record<string, string> = {
    YURIDIK_NOM: env.legalEntityName,
    STIR: env.legalTin,
    MANZIL: env.legalAddress,
    SERVER_JOYLASHUVI: env.serverLocation,
    EMAIL: CONTACT.email,
    TELEGRAM: `@${CONTACT.telegram}`,
    TELEFON: CONTACT.phones.map(formatPhone).join(', '),
  }
  const filled = text.replace(/\{\{([A-Z_]+)\}\}/g, (token, key: string) => values[key] || token)
  if (!filled.includes('{{')) return filled

  // Xatboshi — `\n`; gap — nuqta, undov yoki soʻroqdan keyin boʻshliq.
  // Belgi qolgan gap chiqarib tashlanadi; xatboshidan hech narsa
  // qolmasa, xatboshi ham qolmaydi.
  return filled
    .split('\n')
    .map((paragraph) =>
      (paragraph.match(/[^.!?]*[.!?]+\s*|[^.!?]+$/g) ?? [paragraph])
        .filter((sentence) => !sentence.includes('{{'))
        .join('')
        .trim(),
    )
    .filter(Boolean)
    .join('\n')
}

const OPERATOR_UZ =
  '{{YURIDIK_NOM}}, STIR {{STIR}}, manzil: {{MANZIL}}.\nAloqa: {{EMAIL}}, Telegram {{TELEGRAM}}, telefon {{TELEFON}}.'
const OPERATOR_RU =
  '{{YURIDIK_NOM}}, ИНН {{STIR}}, адрес: {{MANZIL}}.\nКонтакты: {{EMAIL}}, Telegram {{TELEGRAM}}, телефон {{TELEFON}}.'
const OPERATOR_EN =
  '{{YURIDIK_NOM}}, TIN {{STIR}}, address: {{MANZIL}}.\nContact: {{EMAIL}}, Telegram {{TELEGRAM}}, phone {{TELEFON}}.'

export const legal: Record<Locale, LegalCopy> = {
  uz: {
    privacy: 'Maxfiylik siyosati',
    terms: 'Foydalanish shartlari',
    updated: 'Oxirgi yangilanish: 03.10.2026',
    back: 'Bosh sahifaga qaytish',
    operator: 'Radix CRM operatori',
    privacySections: [
      {
        title: '1. Operator',
        text: `Radix CRM xizmatini koʻrsatuvchi: ${OPERATOR_UZ}`,
      },
      {
        title: '2. Ikki xil maʼlumot — ikki xil rol',
        text: 'Saytdagi demo formasi maʼlumotlari uchun Radix — maʼlumotlar egasi va operatori.\nBogʻcha CRM ichiga kiritadigan maʼlumotlar (bolalar, vasiylar, xodimlar) BOGʻCHAGA tegishli: bogʻcha — maʼlumotlar egasi va ularni yigʻish uchun qonuniy asos (jumladan, ota-onalar roziligi) uchun javobgar. Radix bu maʼlumotlarga faqat bogʻcha bilan tuzilgan shartnoma doirasida va faqat xizmat koʻrsatish uchun ishlov beradi.',
      },
      {
        title: '3. Sayt formasidan yigʻiladigan maʼlumotlar',
        text: 'Ism, telefon raqami, bogʻcha nomi, bolalar soni, shahar yoki viloyat, ixtiyoriy izoh, interfeys tili, rozilik fakti va siyosat versiyasi.',
      },
      {
        title: '4. CRM ichidagi maʼlumotlar',
        text: 'Bolalar: F.I.Sh., tugʻilgan sana, jinsi, guruhi, rasmi (ixtiyoriy), bogʻcha kiritgan qoʻshimcha maʼlumot, davomat.\nVasiylar: F.I.Sh., telefon, qarindoshlik, Telegram botga ulangan boʻlsa — chat identifikatori.\nXodimlar: F.I.Sh., telefon, lavozim, ish haqi va toʻlovlar.\nMoliya: hisob-fakturalar, toʻlovlar, xarajatlar.\nFoydalanuvchi hisoblari: email, parol xeshi, kirish tarixi va IP manzil (xavfsizlik jurnali).',
      },
      {
        title: '5. Maqsadlar',
        text: 'Demo arizasini koʻrib chiqish va siz bilan bogʻlanish; bogʻchaga CRM xizmatini koʻrsatish; ota-onalarga bogʻcha nomidan xabar yuborish; obuna hisob-kitobi; xavfsizlik va suiisteʼmolning oldini olish.\nMaʼlumotlar reklama uchun ishlatilmaydi va sotilmaydi.',
      },
      {
        title: '6. Saqlash muddati',
        text: 'Demo arizasi — oxirgi muloqotdan keyin koʻpi bilan 12 oy, agar shartnoma tuzilmasa.\nCRM maʼlumotlari — shartnoma amal qilgan davrda. Shartnoma tugagach bogʻcha 30 kun davomida maʼlumotlarni koʻrish va eksport qilish imkoniga ega; shundan soʻng ular jurnalga yoziladigan tartibda butunlay oʻchiriladi. Zaxira nusxalar 14 kun ichida aylanib, ulardagi maʼlumot ham yoʻqoladi.',
      },
      {
        title: '7. Saqlash joyi va xavfsizlik',
        text: 'Maʼlumotlar {{SERVER_JOYLASHUVI}} joylashgan serverlarda saqlanadi.\nUlanish faqat HTTPS orqali; parollar xesh koʻrinishida saqlanadi; ikki bosqichli tasdiqlash mavjud. Har bir bogʻchaning maʼlumoti maʼlumotlar bazasi darajasida ajratilgan — bir bogʻcha boshqasining maʼlumotini koʻra olmaydi. Radix xodimlari CRM maʼlumotlarini koʻrmaydi; texnik yordam uchun kirish faqat bogʻcha koʻradigan, muddati cheklangan ruxsat bilan va jurnalga yoziladi.',
      },
      {
        title: '8. Uchinchi shaxslar',
        text: 'Hosting provayderi — serverlar va zaxira nusxalar uchun.\nTelegram — ota-ona bogʻcha botiga oʻzi ulangan boʻlsa, xabarlar shu orqali yetkaziladi.\nSMS provayder (Eskiz.uz) — faqat bogʻcha SMS kanalini yoqqan boʻlsa.\nEmail yetkazish xizmati — parolni tiklash va taklif xatlari uchun.\nBoshqa analitika yoki reklama xizmatlari ishlatilmaydi.',
      },
      {
        title: '9. Sizning huquqlaringiz',
        text: 'Oʻzbekiston Respublikasining "Shaxsga doir maʼlumotlar toʻgʻrisida"gi Qonuniga muvofiq siz oʻz maʼlumotlaringiz qanday ishlanayotganini bilish, ulardan nusxa olish, ularni tuzatish, oʻchirish yoki bloklashni talab qilish va rozilikni qaytarib olish huquqiga egasiz.\nCRM ichidagi maʼlumotlar (masalan, farzandingiz haqidagi yozuv) boʻyicha avval bogʻchaga murojaat qiling — u maʼlumotlar egasi. Biz bogʻchaga talabni bajarishda yordam beramiz.',
      },
      {
        title: '10. Murojaat tartibi',
        text: 'Murojaatni {{EMAIL}} manziliga yoki Telegramda {{TELEGRAM}} ga yuboring. Javob 30 kun ichida beriladi. Javobdan qoniqmasangiz, vakolatli davlat organiga shikoyat qilishingiz mumkin.',
      },
      {
        title: '11. Oʻzgarishlar',
        text: 'Siyosat oʻzgarsa, yangi matn shu sahifada sana bilan eʼlon qilinadi. Demo formasidagi rozilik qaysi versiyaga berilgani saqlanadi.',
      },
    ],
    termsSections: [
      {
        title: '1. Taraflar va xizmat',
        text: `Xizmatni koʻrsatuvchi: ${OPERATOR_UZ}\nRadix CRM — xususiy bogʻchalar uchun bulutli boshqaruv tizimi: bolalar, davomat, toʻlovlar, xodimlar, ombor va hisobotlar. Saytdagi demo formasi shartnoma emas; majburiyatlar rasmiy shartnoma va hisob-faktura bilan yuzaga keladi.`,
      },
      {
        title: '2. Hisob ochish',
        text: 'Bogʻcha hisobini Radix jamoasi kelishuvdan keyin ochadi. Bogʻcha egasi elektron pochtasiga 72 soat amal qiladigan taklif havolasi keladi va parolni oʻzi oʻrnatadi — Radix parolni bilmaydi. Xodimlarning hisoblari va ularning huquqlari uchun bogʻcha javobgar.',
      },
      {
        title: '3. Obuna va toʻlov',
        text: 'Narx roʻyxatdagi bolalar soniga bogʻliq: oyiga 400 000 soʻm, 50 nafargacha bola kiradi; har qoʻshimcha 10 nafar bola uchun +50 000 soʻm. Toʻlov muddati: oylik, yarim yillik (−15 %) yoki yillik (−25 %). Toʻlov hisob-faktura asosida bank orqali amalga oshiriladi.\nNarx oʻzgarsa, bu kamida 30 kun oldin xabar qilinadi va allaqachon toʻlangan davrga taʼsir qilmaydi.',
      },
      {
        title: '4. Sinov muddati',
        text: '15 kunlik bepul sinov. Obunaga oʻtilganda birinchi toʻlangan oy sinov boshlangan kundan hisoblanadi — bu hisob ochilganda aytiladi.',
      },
      {
        title: '5. Mavjudlik',
        text: 'Xizmat kun-u tun ishlashga moʻljallangan. Rejali texnik ishlar oldindan eʼlon qilinadi va iloji boricha ish vaqtidan tashqarida oʻtkaziladi. Aniq mavjudlik koʻrsatkichi (SLA) va uning buzilishidagi kompensatsiya, agar kelishilgan boʻlsa, shartnomada koʻrsatiladi.',
      },
      {
        title: '6. Zaxira nusxa',
        text: 'Maʼlumotlar bazasidan har kuni zaxira nusxa olinadi va 14 kun saqlanadi. Tiklash bogʻchaning soʻrovi bilan amalga oshiriladi.',
      },
      {
        title: '7. Toʻlov kechiksa',
        text: 'Toʻlov kechiksa, hisob "faqat oʻqish" rejimiga oʻtadi: yangi yozuv kiritib boʻlmaydi, lekin maʼlumotlarni koʻrish va eksport qilish ishlayveradi. Toʻlanmagani uchun maʼlumotlar oʻchirilmaydi va yashirilmaydi.',
      },
      {
        title: '8. Shartnoma tugaganda',
        text: 'Shartnoma tugagach bogʻcha 30 kun davomida maʼlumotlarini koʻra va eksport qila oladi (Excel/CSV). Shundan keyin maʼlumotlar butunlay oʻchiriladi.',
      },
      {
        title: '9. Mijozning majburiyatlari',
        text: 'Bogʻcha CRMʼga kiritadigan shaxsga doir maʼlumotlar uchun qonuniy asosga (jumladan, ota-onalar va xodimlar roziligiga) ega boʻlishi, maʼlumotlarning toʻgʻriligi va oʻz xodimlari hisoblarining xavfsizligi uchun javobgar.',
      },
      {
        title: '10. Javobgarlik chegarasi',
        text: 'Radix bilvosita zarar va boy berilgan foyda uchun javobgar emas. Radixning umumiy javobgarligi zarar yuzaga kelgan paytgacha boʻlgan oxirgi 3 oyda toʻlangan obuna summasi bilan cheklanadi, agar qonunchilik boshqacha talab qilmasa.',
      },
      {
        title: '11. Toʻxtatish tartibi',
        text: 'Bogʻcha shartnomani istalgan vaqtda bekor qilishi mumkin; xizmat toʻlangan davr oxirigacha ishlaydi. Radix shartlar jiddiy buzilganda yoki toʻlov uzoq muddat kechiksa, oldindan yozma ogohlantirib, xizmatni toʻxtatishi mumkin.',
      },
      {
        title: '12. Nizolar',
        text: 'Nizolar avvalo muzokara yoʻli bilan hal qilinadi. Kelishuvga erishilmasa — Oʻzbekiston Respublikasi qonunchiligiga muvofiq, vakolatli sudda.',
      },
    ],
  },
  ru: {
    privacy: 'Политика конфиденциальности',
    terms: 'Условия использования',
    updated: 'Последнее обновление: 03.10.2026',
    back: 'Вернуться на главную',
    operator: 'Оператор Radix CRM',
    privacySections: [
      {
        title: '1. Оператор',
        text: `Сервис Radix CRM предоставляет: ${OPERATOR_RU}`,
      },
      {
        title: '2. Два вида данных — две роли',
        text: 'Для данных из формы демо на сайте Radix — собственник и оператор.\nДанные, которые детский сад вносит в CRM (дети, опекуны, сотрудники), ПРИНАДЛЕЖАТ САДУ: сад — собственник данных и отвечает за законное основание их сбора (в том числе согласие родителей). Radix обрабатывает эти данные только в рамках договора с садом и только для оказания услуги.',
      },
      {
        title: '3. Данные из формы на сайте',
        text: 'Имя, телефон, название сада, число детей, город или область, необязательный комментарий, язык интерфейса, факт согласия и версия политики.',
      },
      {
        title: '4. Данные внутри CRM',
        text: 'Дети: Ф.И.О., дата рождения, пол, группа, фото (по желанию), дополнительные сведения, внесённые садом, посещаемость.\nОпекуны: Ф.И.О., телефон, степень родства, идентификатор чата — если подключён Telegram-бот.\nСотрудники: Ф.И.О., телефон, должность, зарплата и выплаты.\nФинансы: счета, оплаты, расходы.\nУчётные записи: e-mail, хеш пароля, история входов и IP-адрес (журнал безопасности).',
      },
      {
        title: '5. Цели',
        text: 'Рассмотрение заявки на демо и связь с вами; предоставление саду сервиса CRM; отправка сообщений родителям от имени сада; расчёты по подписке; безопасность и предотвращение злоупотреблений.\nДанные не используются для рекламы и не продаются.',
      },
      {
        title: '6. Срок хранения',
        text: 'Заявка на демо — не более 12 месяцев после последнего общения, если договор не заключён.\nДанные CRM — в течение действия договора. После его окончания сад 30 дней может просматривать и выгружать данные; затем они удаляются полностью, с записью в журнал. Резервные копии обновляются в течение 14 дней, и данные исчезают и из них.',
      },
      {
        title: '7. Место хранения и безопасность',
        text: 'Данные хранятся на серверах, расположенных: {{SERVER_JOYLASHUVI}}.\nСоединение только по HTTPS; пароли хранятся в виде хешей; доступна двухфакторная аутентификация. Данные каждого сада разделены на уровне базы данных — один сад не видит данных другого. Сотрудники Radix не видят данные CRM; доступ для техподдержки возможен только по ограниченному по времени разрешению, которое видит сад, и записывается в журнал.',
      },
      {
        title: '8. Третьи лица',
        text: 'Хостинг-провайдер — серверы и резервные копии.\nTelegram — если родитель сам подключился к боту сада, сообщения доставляются через него.\nSMS-провайдер (Eskiz.uz) — только если сад включил SMS.\nСервис доставки e-mail — письма для сброса пароля и приглашения.\nДругие сервисы аналитики или рекламы не используются.',
      },
      {
        title: '9. Ваши права',
        text: 'В соответствии с Законом Республики Узбекистан «О персональных данных» вы вправе знать, как обрабатываются ваши данные, получить их копию, требовать исправления, удаления или блокирования и отозвать согласие.\nПо данным внутри CRM (например, записи о вашем ребёнке) сначала обратитесь в детский сад — он собственник данных. Мы помогаем саду выполнить запрос.',
      },
      {
        title: '10. Порядок обращения',
        text: 'Направьте обращение на {{EMAIL}} или в Telegram {{TELEGRAM}}. Ответ — в течение 30 дней. Если ответ вас не устроил, вы можете обратиться в уполномоченный государственный орган.',
      },
      {
        title: '11. Изменения',
        text: 'При изменении политики новый текст публикуется на этой странице с датой. Для согласия из формы демо сохраняется версия политики, к которой оно относится.',
      },
    ],
    termsSections: [
      {
        title: '1. Стороны и услуга',
        text: `Услугу предоставляет: ${OPERATOR_RU}\nRadix CRM — облачная система управления для частных детских садов: дети, посещаемость, оплаты, сотрудники, склад и отчёты. Форма демо на сайте не является договором; обязательства возникают по официальному договору и счёту.`,
      },
      {
        title: '2. Открытие учётной записи',
        text: 'Учётную запись сада открывает команда Radix после договорённости. Владелец сада получает на e-mail ссылку-приглашение, действующую 72 часа, и сам задаёт пароль — Radix его не знает. За учётные записи сотрудников и их права отвечает сад.',
      },
      {
        title: '3. Подписка и оплата',
        text: 'Цена зависит от числа детей в списке: 400 000 сум в месяц, включено до 50 детей; каждые следующие 10 детей — +50 000 сум. Период оплаты: месяц, полгода (−15 %) или год (−25 %). Оплата по счёту, банковским переводом.\nОб изменении цены сообщается не менее чем за 30 дней; уже оплаченный период не меняется.',
      },
      {
        title: '4. Пробный период',
        text: '15 дней бесплатно. При переходе на подписку первый оплаченный месяц отсчитывается с начала пробного периода — об этом сообщается при открытии учётной записи.',
      },
      {
        title: '5. Доступность',
        text: 'Сервис рассчитан на круглосуточную работу. Плановые работы объявляются заранее и по возможности проводятся вне рабочего времени. Конкретный показатель доступности (SLA) и компенсация за его нарушение, если согласованы, указываются в договоре.',
      },
      {
        title: '6. Резервные копии',
        text: 'Резервная копия базы данных создаётся ежедневно и хранится 14 дней. Восстановление выполняется по запросу сада.',
      },
      {
        title: '7. Просрочка оплаты',
        text: 'При просрочке оплаты учётная запись переходит в режим «только чтение»: новые записи вносить нельзя, но просмотр и выгрузка данных работают. За неоплату данные не удаляются и не скрываются.',
      },
      {
        title: '8. Окончание договора',
        text: 'После окончания договора сад 30 дней может просматривать и выгружать свои данные (Excel/CSV). Затем данные удаляются полностью.',
      },
      {
        title: '9. Обязанности клиента',
        text: 'Сад отвечает за наличие законного основания для персональных данных, которые вносит в CRM (в том числе согласия родителей и сотрудников), за их достоверность и за безопасность учётных записей своих сотрудников.',
      },
      {
        title: '10. Ограничение ответственности',
        text: 'Radix не отвечает за косвенный ущерб и упущенную выгоду. Общая ответственность Radix ограничена суммой подписки, оплаченной за последние 3 месяца до возникновения ущерба, если законодательство не требует иного.',
      },
      {
        title: '11. Порядок приостановки',
        text: 'Сад может расторгнуть договор в любой момент; сервис работает до конца оплаченного периода. Radix может приостановить сервис при существенном нарушении условий или длительной просрочке оплаты, предварительно письменно предупредив.',
      },
      {
        title: '12. Споры',
        text: 'Споры решаются прежде всего путём переговоров. Если соглашение не достигнуто — в компетентном суде в соответствии с законодательством Республики Узбекистан.',
      },
    ],
  },
  en: {
    privacy: 'Privacy Policy',
    terms: 'Terms of Use',
    updated: 'Last updated: 03.10.2026',
    back: 'Back to the home page',
    operator: 'Radix CRM operator',
    privacySections: [
      {
        title: '1. Operator',
        text: `Radix CRM is provided by: ${OPERATOR_EN}`,
      },
      {
        title: '2. Two kinds of data — two roles',
        text: 'For data from the demo form on this website, Radix is the owner and operator.\nData a kindergarten enters into the CRM (children, guardians, staff) BELONGS TO THE KINDERGARTEN: the kindergarten is the data owner and is responsible for the lawful basis for collecting it (including parental consent). Radix processes that data only under its contract with the kindergarten and only to provide the service.',
      },
      {
        title: '3. Data from the website form',
        text: 'Name, phone number, kindergarten name, number of children, city or region, an optional comment, interface language, the fact of consent and the policy version.',
      },
      {
        title: '4. Data inside the CRM',
        text: 'Children: full name, date of birth, sex, group, photo (optional), additional details entered by the kindergarten, attendance.\nGuardians: full name, phone, relationship, chat identifier if they joined the Telegram bot.\nStaff: full name, phone, position, salary and payouts.\nFinance: invoices, payments, expenses.\nUser accounts: e-mail, password hash, sign-in history and IP address (security log).',
      },
      {
        title: '5. Purposes',
        text: 'Reviewing demo requests and contacting you; providing the CRM service to the kindergarten; sending messages to parents on the kindergarten’s behalf; subscription billing; security and abuse prevention.\nData is not used for advertising and is never sold.',
      },
      {
        title: '6. Retention',
        text: 'Demo requests — at most 12 months after the last contact if no contract follows.\nCRM data — for the term of the contract. After it ends, the kindergarten can view and export its data for 30 days; the data is then deleted completely, with a log entry. Backups rotate within 14 days, so the data disappears from them too.',
      },
      {
        title: '7. Storage location and security',
        text: 'Data is stored on servers located in: {{SERVER_JOYLASHUVI}}.\nConnections are HTTPS only; passwords are stored as hashes; two-factor authentication is available. Each kindergarten’s data is separated at the database level — one kindergarten cannot see another’s. Radix staff cannot see CRM data; support access is possible only under a time-limited permission that the kindergarten can see, and it is logged.',
      },
      {
        title: '8. Third parties',
        text: 'Hosting provider — servers and backups.\nTelegram — if a parent joined the kindergarten’s bot themselves, messages are delivered through it.\nSMS provider (Eskiz.uz) — only if the kindergarten has switched SMS on.\nE-mail delivery service — password-reset and invitation e-mails.\nNo other analytics or advertising services are used.',
      },
      {
        title: '9. Your rights',
        text: 'Under the Law of the Republic of Uzbekistan “On Personal Data” you have the right to know how your data is processed, to obtain a copy, to request correction, deletion or blocking, and to withdraw consent.\nFor data inside the CRM (for example, a record about your child), contact the kindergarten first — it owns the data. We help the kindergarten fulfil the request.',
      },
      {
        title: '10. How to contact us',
        text: 'Send your request to {{EMAIL}} or on Telegram to {{TELEGRAM}}. We reply within 30 days. If you are not satisfied with the reply, you may complain to the competent state authority.',
      },
      {
        title: '11. Changes',
        text: 'If this policy changes, the new text is published on this page with its date. For consent given in the demo form, the policy version it refers to is stored.',
      },
    ],
    termsSections: [
      {
        title: '1. Parties and service',
        text: `The service is provided by: ${OPERATOR_EN}\nRadix CRM is a cloud management system for private kindergartens: children, attendance, payments, staff, inventory and reports. The demo form on this website is not a contract; obligations arise under an official contract and invoice.`,
      },
      {
        title: '2. Opening an account',
        text: 'The Radix team opens a kindergarten’s account after an agreement. The owner receives an invitation link by e-mail, valid for 72 hours, and sets the password themselves — Radix never knows it. The kindergarten is responsible for its staff accounts and their permissions.',
      },
      {
        title: '3. Subscription and payment',
        text: 'The price depends on the number of enrolled children: 400 000 UZS per month including up to 50 children; +50 000 UZS for every further 10 children. Billing period: monthly, semi-annual (−15 %) or annual (−25 %). Payment by bank transfer against an invoice.\nPrice changes are announced at least 30 days in advance and do not affect periods already paid.',
      },
      {
        title: '4. Trial',
        text: 'A free 15-day trial. On conversion, the first paid month is counted from the start of the trial — this is stated when the account is opened.',
      },
      {
        title: '5. Availability',
        text: 'The service is designed to run around the clock. Planned maintenance is announced in advance and, where possible, carried out outside working hours. A specific availability target (SLA) and any compensation for missing it, if agreed, are set out in the contract.',
      },
      {
        title: '6. Backups',
        text: 'The database is backed up daily and each backup is kept for 14 days. Restores are carried out at the kindergarten’s request.',
      },
      {
        title: '7. Late payment',
        text: 'If payment is late, the account switches to read-only: no new records can be entered, but viewing and exporting data keep working. Data is never deleted or hidden for non-payment.',
      },
      {
        title: '8. End of contract',
        text: 'After the contract ends, the kindergarten can view and export its data for 30 days (Excel/CSV). The data is then deleted completely.',
      },
      {
        title: '9. Customer obligations',
        text: 'The kindergarten is responsible for having a lawful basis for the personal data it enters into the CRM (including consent from parents and staff), for its accuracy, and for the security of its staff accounts.',
      },
      {
        title: '10. Limitation of liability',
        text: 'Radix is not liable for indirect damage or lost profit. Radix’s total liability is limited to the subscription fees paid in the 3 months before the damage occurred, unless the law requires otherwise.',
      },
      {
        title: '11. Suspension',
        text: 'The kindergarten may terminate the contract at any time; the service runs until the end of the paid period. Radix may suspend the service after prior written notice in case of a material breach or prolonged late payment.',
      },
      {
        title: '12. Disputes',
        text: 'Disputes are settled by negotiation first. Failing agreement — by the competent court under the legislation of the Republic of Uzbekistan.',
      },
    ],
  },
}
