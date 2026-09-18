/**
 * Radix Intelligence matnlari (docs/07 §7, §12).
 *
 * Til qoidasi: FAKT, bashorat emas. "Kechikmoqda" — ha; "to'lamaydi",
 * "xavf ostida" — yo'q. Har bir jumla evidence'dagi raqamdan tuziladi;
 * `{placeholder}` kalitlari evidence maydonlari bilan bir xil.
 *
 * Backend `apps/intelligence/content/{uz,ru}.py` bilan bir xil kalitlar.
 */

import type { InsightSeverity, InsightType } from '@/lib/api/types'

export type Locale = 'uz' | 'ru'

export interface IntelligenceCopy {
  brand: string
  briefingTitle: string
  noOpenInsights: string
  loadError: string
  severity: Record<InsightSeverity, string>
  statusNew: string
  titles: Record<InsightType, string>
  recommendations: Record<string, string>
  actions: {
    why: string
    open: string
    resolve: string
    dismiss: string
    close: string
  }
  facts: {
    totalOverdue: string
    maxDays: string
    avgDays: string
    children: string
    ofActive: string
    dayUnit: string
    invoices: string
  }
  why: {
    title: string
    rule: string
    ruleBody: string
    severityTitle: string
    criticalByDays: string
    criticalByCount: string
    warningReason: string
    snapshotTitle: string
    snapshotBody: string
    capped: string
    childCol: string
    groupCol: string
    daysCol: string
    invoicesCol: string
    amountCol: string
    deletedChild: string
    noGroup: string
  }
  checks: {
    attendanceTitle: string
    attendanceBody: string
    attendanceComplete: string
    attendanceIncomplete: string
    open: string
  }
  debtors: { banner: string; showAll: string }
}

export const uz: IntelligenceCopy = {
  brand: 'Radix AI',
  briefingTitle: 'Kunlik brifing',
  noOpenInsights: 'Bugun ochiq signal yo‘q.',
  loadError: 'Brifingni yuklab bo‘lmadi.',
  severity: { critical: 'Jiddiy', warning: 'Diqqat' },
  statusNew: 'Yangi',
  titles: {
    payment_delay:
      '{children_count} ta bola bo‘yicha to‘lov {overdue_days_threshold} kundan ortiq kechikmoqda',
    attendance_drop: 'Guruhda davomat o‘z bazasiga nisbatan {drop_points} punktga pasaydi',
  },
  recommendations: {
    'payment_delay.review_debtors':
      'Qarzdorlar ro‘yxatini ko‘rib, eslatma yuborishni ko‘rib chiqing.',
    'attendance_drop.ask_teacher': 'Guruh tarbiyachisi bilan pasayish sababini aniqlang.',
  },
  actions: {
    why: 'Nega?',
    open: 'Ro‘yxatni ochish',
    resolve: 'Hal qilindi',
    dismiss: 'Keyinroq',
    close: 'Yopish',
  },
  facts: {
    totalOverdue: 'Kechikkan summa',
    maxDays: 'Eng uzoq kechikish',
    avgDays: 'O‘rtacha kechikish',
    children: 'Bolalar',
    ofActive: '{active_children} faol boladan',
    dayUnit: 'kun',
    invoices: 'faktura',
  },
  why: {
    title: 'Nega bu signal chiqdi?',
    rule: 'Qoida',
    ruleBody:
      'Muddati {overdue_days_threshold} kundan ortiq o‘tgan va hali yopilmagan faktura qismi bo‘lgan bolalar. Qarz ledger’dan hisoblanadi — Qarzdorlar sahifasi bilan bir xil; fakturasiz to‘langan pul eng eski fakturaga yotqiziladi.',
    severityTitle: 'Nega {severity}?',
    criticalByDays:
      'Eng uzoq kechikish {max_days_overdue} kun — chegara {critical_days_threshold} kun.',
    criticalByCount:
      '{children_count} ta bola — chegara {critical_children_threshold} ta (faol bolalarning 10 %, kamida 3).',
    warningReason:
      'Eng uzoq kechikish {max_days_overdue} kun ({critical_days_threshold} dan kam) va {children_count} ta bola ({critical_children_threshold} dan kam).',
    snapshotTitle: 'Holat {as_of} sanasiga',
    snapshotBody:
      'Raqamlar signal chiqqan paytdagi holat. Ismlar jonli. Ro‘yxatni ochsangiz, hozirgi holat farq qilishi mumkin — masalan, kimdir shu orada to‘lagan bo‘lsa.',
    capped: 'Eng uzoq kechikkan {shown} tasi ko‘rsatilmoqda (jami {children_count}).',
    childCol: 'Bola',
    groupCol: 'Guruh',
    daysCol: 'Kechikish',
    invoicesCol: 'Faktura',
    amountCol: 'Summa',
    deletedChild: 'o‘chirilgan bola',
    noGroup: 'guruhsiz',
  },
  checks: {
    attendanceTitle: 'Bugungi davomat',
    attendanceBody: '{recorded} / {expected} bola belgilangan',
    attendanceComplete: 'To‘liq',
    attendanceIncomplete: '{missing} ta bola belgilanmagan',
    open: 'Davomatni ochish',
  },
  debtors: {
    banner: 'Radix AI signali: {days} kundan ortiq kechikkanlar ko‘rsatilmoqda.',
    showAll: 'Hammasini ko‘rish',
  },
}

export const ru: IntelligenceCopy = {
  brand: 'Radix AI',
  briefingTitle: 'Ежедневный брифинг',
  noOpenInsights: 'Сегодня открытых сигналов нет.',
  loadError: 'Не удалось загрузить брифинг.',
  severity: { critical: 'Серьёзно', warning: 'Внимание' },
  statusNew: 'Новый',
  titles: {
    payment_delay:
      'По {children_count} детям оплата задерживается более {overdue_days_threshold} дней',
    attendance_drop: 'Посещаемость группы снизилась на {drop_points} пунктов относительно её базы',
  },
  recommendations: {
    'payment_delay.review_debtors':
      'Просмотрите список должников и рассмотрите отправку напоминаний.',
    'attendance_drop.ask_teacher': 'Уточните причину снижения у воспитателя группы.',
  },
  actions: {
    why: 'Почему?',
    open: 'Открыть список',
    resolve: 'Решено',
    dismiss: 'Позже',
    close: 'Закрыть',
  },
  facts: {
    totalOverdue: 'Просроченная сумма',
    maxDays: 'Максимальная задержка',
    avgDays: 'Средняя задержка',
    children: 'Детей',
    ofActive: 'из {active_children} активных',
    dayUnit: 'дн.',
    invoices: 'счетов',
  },
  why: {
    title: 'Почему появился этот сигнал?',
    rule: 'Правило',
    ruleBody:
      'Дети, у которых есть незакрытая часть счёта с просрочкой более {overdue_days_threshold} дней. Долг считается по леджеру — так же, как на странице должников; оплата без привязки к счёту закрывает самый старый счёт.',
    severityTitle: 'Почему {severity}?',
    criticalByDays:
      'Максимальная задержка {max_days_overdue} дн. — порог {critical_days_threshold} дн.',
    criticalByCount:
      '{children_count} детей — порог {critical_children_threshold} (10 % активных детей, минимум 3).',
    warningReason:
      'Максимальная задержка {max_days_overdue} дн. (меньше {critical_days_threshold}) и {children_count} детей (меньше {critical_children_threshold}).',
    snapshotTitle: 'Состояние на {as_of}',
    snapshotBody:
      'Цифры — на момент появления сигнала. Имена — актуальные. Открыв список, вы можете увидеть отличие — например, если кто-то уже оплатил.',
    capped: 'Показаны {shown} с самой долгой задержкой (всего {children_count}).',
    childCol: 'Ребёнок',
    groupCol: 'Группа',
    daysCol: 'Задержка',
    invoicesCol: 'Счетов',
    amountCol: 'Сумма',
    deletedChild: 'удалённый ребёнок',
    noGroup: 'без группы',
  },
  checks: {
    attendanceTitle: 'Посещаемость сегодня',
    attendanceBody: 'Отмечено {recorded} / {expected} детей',
    attendanceComplete: 'Полностью',
    attendanceIncomplete: 'Не отмечено: {missing}',
    open: 'Открыть посещаемость',
  },
  debtors: {
    banner: 'Сигнал Radix AI: показаны задержки более {days} дней.',
    showAll: 'Показать всех',
  },
}

const copies: Record<Locale, IntelligenceCopy> = { uz, ru }

/** Ilova hozircha o‘zbek tilida; RU nusxa kalit-ma-kalit tayyor. */
export function getCopy(locale: Locale = 'uz'): IntelligenceCopy {
  return copies[locale]
}

/**
 * `{kalit}` joylarini qiymat bilan to‘ldiradi. Yo‘q kalit bo‘sh emas,
 * ko‘rinib turadigan `{kalit}` bo‘lib qoladi — sukut bilan yashirilgan
 * xatodan ko‘ra ko‘rinadigani yaxshi.
 */
export function fill(template: string, values: Record<string, unknown>): string {
  return template.replace(/\{(\w+)\}/g, (match, key: string) => {
    const value = values[key]
    return value === undefined || value === null ? match : String(value)
  })
}
