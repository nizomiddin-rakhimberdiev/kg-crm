/**
 * Sozlamaning odamcha nomi — KALIT emas (ADR-45).
 *
 * Kalitlar roʻyxati backendda (`settings_app/services.py::DEFAULTS`),
 * bu yerda faqat ularning nomi va izohi. Ilgari bu roʻyxat
 * `SettingsPage` ichida edi va soliq preseti panelida kalitlar XOM
 * koʻrinardi — `payroll.income_tax_rate`, `tax.regime` (audit,
 * 2026-10-21). Endi ikkala ekran ham shu yerdan oʻqiydi, va
 * `__tests__/settingsMeta.test.ts` nomsiz kalit qolmaganini backend
 * manbasi bilan solishtirib tekshiradi.
 */

import { t } from '@/lib/i18n'

export interface SettingMeta {
  label: string
  help: string
  /** Tanlovli qiymat — erkin matn emas (xato yozilgan "prorate" jimgina toʻliq oyga aylanardi). */
  options?: Array<[string, string]>
  /** Raqam chegaralari. Ilgari hamma raqam 1–31 ga qotirilgan edi — bu `due_day` uchun edi. */
  min?: number
  max?: number
  /** Kasr qadami — komissiya foizi uchun (0,2 %). */
  step?: number
  /**
   * Oʻlchov birligi — maydon YONIDA koʻrsatiladi (ADR-45).
   *
   * Auditda `payroll.pension_rate = 0.1` va `payroll.social_tax_rate =
   * 12` yonma-yon turdi va "biri ulush, ikkinchisi foiz" deb oʻqildi.
   * Aslida ikkisi ham foiz — INPS haqiqatan 0,1 %. Birlik maydonning
   * oʻzida turgani shu savolni butunlay yopadi.
   */
  unit?: string
}

/**
 * Kalitlar ro'yxati backend'da (`DEFAULTS`), bu yerda faqat ularning
 * odamcha nomi. Yangi kalit qo'shilsa u baribir ko'rinadi — shunchaki
 * tarjimasiz, kalitning o'zi bilan.
 */
export const SETTING_META: Record<string, SettingMeta> = {
  'general.default_language': {
    label: t('Bogʻcha tili'),
    help: t('Xodim oʻzi til tanlamagan boʻlsa, tizim shu tilda ochiladi.'),
  },
  'finance.due_day': {
    label: t('Toʻlov muddati (oy kuni)'),
    help: t('Hisob-faktura shu kungacha toʻlanishi kutiladi.'),
    min: 1,
    max: 31,
  },
  'finance.reminder_day': {
    label: t('Eslatma kuni'),
    help: t('Qarzdorlarga eslatma shu kundan boshlab yuboriladi.'),
    min: 1,
    max: 31,
  },
  'notifications.sms_enabled': {
    label: t('Xabarnomalar'),
    help: t('Oʻchirilsa hech qanday xabar yuborilmaydi — na Telegram, na SMS.'),
  },
  'notifications.default_channel': {
    label: t('Asosiy kanal'),
    help: t('Telegram bepul; SMS har xabar uchun pul turadi va shlyuz shartnomasini talab qiladi.'),
  },
  'notifications.absence_alert': {
    label: t('Kelmagani haqida xabar'),
    help: t('Bola bugun «kelmadi» deb belgilansa, ota-onaga xabar ketadi. Pulga taʼsir qilmaydi.'),
  },
  'notifications.payment_receipt': {
    label: t('Toʻlov haqida xabar'),
    help: t('Toʻlov qabul qilinganda ota-onaga xabar ketadi.'),
  },
  'notifications.send_from_hour': {
    label: t('Yuborishni boshlash (soat)'),
    help: t('Bundan oldin tayyor boʻlgan xabar navbatda turadi — tungi xabar yuborilmaydi.'),
  },
  'notifications.send_to_hour': {
    label: t('Yuborishni tugatish (soat)'),
    help: t('Shu soatdan keyin xabar yuborilmaydi, ertalab ketadi.'),
  },
  'notifications.debt_reminders_per_day': {
    label: t('Kuniga eslatma soni'),
    help: t('Bir ota-ona kuniga shundan ortiq qarz eslatmasini olmaydi.'),
  },
  'notifications.max_retries': {
    label: t('Qayta urinish soni'),
    help: t('Xato boʻlgan xabar shuncha marta qayta yuboriladi.'),
  },
  'notifications.sms_price': {
    unit: 'soʻm',
    label: t('Bitta SMS boʻlagi narxi'),
    help: t('Taxminiy xarajatni hisoblash uchun — provayder shartnomasidagi narx.'),
  },
  'finance.first_month_mode': {
    label: t('Birinchi oy hisobi'),
    help: t(
      'Oy oʻrtasida kelgan yoki ketgan bola uchun: toʻliq oy, ish kunlari boʻyicha yoki keyingi oydan.',
    ),
    options: [
      ['prorated', t('Ish kunlari boʻyicha')],
      ['full', t('Toʻliq oy')],
      ['next_month', t('Keyingi oydan')],
    ],
  },
  'benefits.sibling_amount': {
    unit: 'soʻm',
    label: t('Aka-uka chegirmasi'),
    help: t(
      'Bir oiladagi (umumiy vasiy) har bir bolaga shuncha chegirma — avtomatik, qoʻlda kiritilmaydi.',
    ),
    min: 0,
  },
  'benefits.sibling_rule': {
    label: t('Aka-uka qoidasi'),
    help: t('Chegirma kimga tushadi.'),
    options: [
      ['all', t('Hammasiga, birinchisiga ham')],
      ['after_first', t('Birinchisi toʻliq, keyingilarga chegirma')],
    ],
  },
  'benefits.staff_child_percent': {
    unit: '%',
    label: t('Xodim farzandi'),
    help: t('Oylik narxdan shuncha foiz chegirma.'),
    min: 0,
    max: 100,
  },
  'benefits.low_income_percent': {
    unit: '%',
    label: t('Kam taʼminlangan'),
    help: t('Oylik narxdan shuncha foiz chegirma.'),
    min: 0,
    max: 100,
  },
  'benefits.full_percent': {
    unit: '%',
    label: t('Toʻliq imtiyoz'),
    help: t('Oylik narxdan shuncha foiz chegirma.'),
    min: 0,
    max: 100,
  },
  'finance.trial_days': {
    min: 0,
    max: 20,
    label: t('Sinov muddati (ish kuni)'),
    help: t(
      'Yangi bolaning birinchi shuncha ish kuni bepul. Sinovda ketsa — hech narsa hisoblanmaydi. 0 — sinov yoʻq.',
    ),
  },
  'finance.rounding_step': {
    unit: 'soʻm',
    min: 1,
    label: t('Yaxlitlash'),
    help: t(
      'Hisoblangan summa shu qadamgacha yaxlitlanadi: 1 161 905 → 1 162 000. Kunlik stavka emas, natija.',
    ),
  },
  'finance.backdate_days': {
    min: 0,
    max: 3650,
    label: t('Eski sana chegarasi (kun)'),
    help: t(
      'Shundan eski sana bilan toʻlov faqat sabab bilan kiritiladi. Kelajakdagi sana hech qachon.',
    ),
  },
  'commission.terminal_percent': {
    unit: '%',
    min: 0,
    max: 10,
    step: 0.01,
    label: t('Terminal komissiyasi'),
    help: t(
      'Toʻlov bankka toʻliq tushadi, komissiya “Bank komissiyasi” chiqimi boʻlib oʻzi yoziladi.',
    ),
  },
  'commission.bank_transfer_percent': {
    unit: '%',
    min: 0,
    max: 10,
    step: 0.01,
    label: t('Oʻtkazma komissiyasi'),
    help: t('Odatda 0 — bank oʻtkazma uchun bogʻchadan olmaydi.'),
  },
  'commission.click_percent': {
    unit: '%',
    min: 0,
    max: 10,
    step: 0.01,
    label: t('Click komissiyasi'),
    help: t('Click oʻz ulushini ushlab qoladi — u bank xarajati boʻlib koʻrinadi.'),
  },
  'commission.payme_percent': {
    unit: '%',
    min: 0,
    max: 10,
    step: 0.01,
    label: t('Payme komissiyasi'),
    help: t('Payme oʻz ulushini ushlab qoladi — u bank xarajati boʻlib koʻrinadi.'),
  },
  'finance.first_invoice_grace_days': {
    label: t('Birinchi faktura muddati (kun)'),
    help: t(
      'Qabul sanasidan kamida shuncha kun keyin — bola kelgan kuniyoq qarzdor boʻlib qolmasin.',
    ),
  },
  'attendance.teacher_edit_days': {
    label: t('Tarbiyachi necha kun orqaga belgilaydi'),
    help: t('1 = bugun va kecha. Eski kunlarni faqat direktor sabab bilan oʻzgartiradi.'),
  },
  'attendance.working_weekdays': {
    label: t('Ish kunlari'),
    help: t(
      'Kunlik toʻlov shu kunlar boʻyicha hisoblanadi — shanba ishlaydigan bogʻcha uchun ham.',
    ),
  },
  'children.min_age': {
    label: t('Eng kichik yosh'),
    help: t('Bu yoshdan kichik bola qoʻshilmaydi — xato yozilgan tugʻilgan sana shunda ushlanadi.'),
  },
  'children.max_age': {
    label: t('Eng katta yosh'),
    help: t('Bogʻchalar turlicha: baʼzilari 7 yoshgacha oladi.'),
  },
  'payroll.income_tax_rate': {
    unit: '%',
    label: t('Daromad soligʻi'),
    help: t('Xodim maoshidan ushlanadi. 0 — ushlanmaydi.'),
  },
  'payroll.pension_rate': {
    unit: '%',
    label: t('Pensiya jamgʻarmasi'),
    // INPS stavkasi haqiqatan 0,1 % — kichik, lekin toʻgʻri raqam.
    // Auditda u yondagi 12 % bilan solishtirilib "ulush" deb oʻqildi,
    // shuning uchun izoh buni ochiq aytadi.
    help: t('Xodim maoshidan ushlanadi. INPS stavkasi 0,1 % — 0 boʻlsa ushlanmaydi.'),
  },
  'payroll.social_tax_rate': {
    unit: '%',
    label: t('Ijtimoiy soliq'),
    help: t('Bogʻcha ustiga toʻlaydi — xodim maoshidan ushlanmaydi.'),
  },
  'transit.settle_days': {
    unit: 'kun',
    label: t('Yoʻldagi pul necha kunda tushadi'),
    help: t('Terminal va onlayn toʻlov bankka shuncha kunda tushadi; kechikkani roʻyxatda qizil.'),
    min: 0,
    max: 30,
  },
  'control.document_threshold': {
    unit: 'soʻm',
    label: t('Hujjat talab qiladigan chiqim'),
    help: t('Shu summadan katta chiqimda chek yoki shartnoma boʻlishi tekshiriladi.'),
    min: 0,
  },
  'control.change_percent': {
    unit: '%',
    label: t('Toifa keskin oʻzgardi'),
    help: t('Oʻtgan oyga nisbatan shu foizdan koʻp oʻzgargan toifa eʼtibor roʻyxatiga tushadi.'),
    min: 0,
  },
  'alerts.expense_threshold': {
    unit: 'soʻm',
    label: t('Katta chiqim ogohlantirishi'),
    help: t('Shu summadan katta chiqim yozilsa, rahbarga darhol xabar boradi.'),
    min: 0,
  },
  'alerts.benefit_percent': {
    unit: '%',
    label: t('Imtiyoz ogohlantirishi'),
    help: t('Oylik hisobda imtiyozlar daromadning shu foizidan oshsa — xabar.'),
    min: 0,
  },
  'alerts.digest_hour': {
    label: t('Kunlik xulosa soati'),
    help: t('Rahbarga kunlik brifing shu soatda yuboriladi.'),
    min: 0,
    max: 23,
  },
  'alerts.recipients': {
    label: t('Ogohlantirish kimga boradi'),
    help: t('Rollar yoki elektron pochta, vergul bilan. Boʻsh boʻlsa — egasiga.'),
  },
  'report.food_category': {
    label: t('Oziq-ovqat toifasi nomi'),
    help: t('Hisobotda bir bolaga toʻgʻri keladigan ovqat xarajati shu toifadan olinadi.'),
  },
  'report.marketing_category': {
    label: t('Marketing toifasi nomi'),
    help: t('Bitta yangi bola nechaga tushgani shu toifadan hisoblanadi.'),
  },
  'attendance.auto_absent': {
    label: t('Avtomatik "kelmadi"'),
    help: t('Belgilanmagan bolalar kun oxirida kelmagan deb yoziladi.'),
  },
  // Hisobot topshirish (Bosqich 13.6, ADR-42): raqamlar modelga bogʻliq
  // emas, faqat jarayon.
  'governance.model': {
    label: t('Boshqaruv modeli'),
    help: t('Oylik hisobotni kim tayyorlaydi va kim qabul qiladi.'),
    options: [
      ['A', t('A — ega oʻzi tasdiqlaydi')],
      ['B', t('B — boshqaruvchi topshiradi, rahbar qabul qiladi')],
      ['C', t('C — filiallar topshiradi, ega konsolidatsiyani tasdiqlaydi')],
    ],
  },
  'governance.acceptors': {
    label: t('Kim qabul qiladi'),
    help: t('Har biri alohida «Qabul qildim» bosadi.'),
    options: [
      ['owner', t('Ega')],
      ['owner,director', t('Ega va direktor')],
    ],
  },
  'governance.deadline_day': {
    label: t('Topshirish muddati (keyingi oy kuni)'),
    help: t('Muddat oʻtsa, rahbarga bir marta eslatma boradi.'),
    min: 1,
    max: 28,
  },
  // Bosqich 13.7–13.8: prognoz, soliq, fiskal chek, hisob kodlari.
  'forecast.reserve_amount': {
    unit: 'soʻm',
    label: t('Zaxira summasi'),
    help: t('0 boʻlsa — quyidagi oylar soni × oylik ish haqi fondi.'),
  },
  'forecast.reserve_months': {
    label: t('Zaxira (oylik fondi, oy)'),
    help: t('Xavfsiz olish summasidan ayiriladi. Sukut 0,5.'),
  },
  'forecast.pay_day': {
    label: t('Oylik toʻlanadigan kun'),
    help: t('Prognozda oʻtgan oy oyligi shu kuni chiqadi.'),
    min: 1,
    max: 28,
  },
  'forecast.tax_day': {
    label: t('Soliq toʻlanadigan kun'),
    help: t('Soliq taqvimidagi muddat — keyingi oyning shu kuni.'),
    min: 1,
    max: 28,
  },
  'tax.regime': {
    label: t('Soliq rejimi'),
    help: t('Yuqoridagi preset bilan oʻrnatiladi.'),
    options: [
      ['pq403', t('Nodavlat MTT imtiyozi (PQ-403)')],
      ['general', t('Umumiy rejim')],
      ['turnover', t('Aylanmadan olinadigan soliq')],
    ],
  },
  'tax.turnover_percent': {
    unit: '%',
    label: t('Aylanma soligʻi'),
    help: t('Faqat aylanma rejimida: oy daromadidan.'),
  },
  'tax.dividend_percent': {
    unit: '%',
    label: t('Dividend soligʻi'),
    help: t('Egasiga dividend toʻlanganda majburiyat boʻlib yoziladi.'),
  },
  'tax.parent_exemption_monthly': {
    unit: 'soʻm',
    label: t('Ota-ona JShDS imtiyozi limiti (oyiga)'),
    help: t('Yillik maʼlumotnomada har oy shu summagacha koʻrsatiladi.'),
  },
  'fiscal.control_from': {
    label: t('Fiskal chek nazorati qachondan'),
    help: t('YYYY-MM-DD. Boʻsh — nazorat oʻchiq. Naqd va karta toʻlovida chek kerak.'),
  },
  // Shartnoma rekvizitlari (PLAN 9.3) — shablondagi {{...}} maydonlar
  // shu yerdan to'ldiriladi.
  'contracts.director_name': {
    label: t('Direktor (F.I.Sh.)'),
    help: t('Shartnomada imzo qoʻyuvchi shaxs.'),
  },
  'contracts.bank_name': {
    label: t('Bank nomi'),
    help: t('Shartnomaning rekvizitlar qismida koʻrsatiladi.'),
  },
  'contracts.bank_account': {
    label: t('Hisob raqami'),
    help: t('Bogʻchaning hisob-kitob raqami.'),
  },
  'contracts.bank_mfo': { label: t('MFO'), help: t('Bank kodi.') },
  'contracts.daily_meal_fee': {
    unit: 'soʻm',
    label: t('Bir kunlik ovqat puli'),
    help: t('Bola kelmagan kun uchun shartnoma boʻyicha ayriladigan summa.'),
  },
  'contracts.free_absence_days': {
    label: t('Toʻlovsiz saqlanadigan kunlar'),
    help: t('Yiliga shuncha ish kuni joy toʻlovsiz saqlanadi.'),
  },
  'contracts.daily_hours': {
    label: t('Kunlik saqlash vaqti (soat)'),
    help: t('Shartnomaning birinchi bandidagi soat.'),
  },
}

// Buxgalter jurnali hisob kodlari (13.8c): hammasi bir xil izoh bilan.
const ACCOUNT_LABELS: Array<[string, string]> = [
  ['cash', t('Kassa')],
  ['bank', t('Hisob-kitob schyoti')],
  ['receivables', t('Ota-onalar qarzi')],
  ['advances', t('Olingan avanslar')],
  ['payroll', t('Ish haqi boʻyicha qarz')],
  ['budget', t('Byudjetga toʻlovlar')],
  ['revenue', t('Xizmat daromadi')],
  ['suppliers', t('Yetkazib beruvchilar')],
  ['expenses', t('Chiqimlar (toifada kod boʻlmasa)')],
  ['payroll_expense', t('Oylik maosh chiqimi')],
  ['fixed_assets', t('Asosiy vositalar')],
  ['other_income', t('Boshqa daromad')],
  ['adjustments', t('Tuzatishlar')],
  ['owner', t('Egasiga toʻlov')],
  ['capital', t('Egadan kiritma')],
  ['loans', t('Kreditlar')],
]
for (const [key, label] of ACCOUNT_LABELS) {
  SETTING_META[`accounts.${key}`] = { label, help: t('Hisob kodi; buxgalter tasdiqlaydi.') }
}
