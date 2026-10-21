/**
 * Validatsiya xabarlari — brauzerning emas, bizning (audit, 2026-10-21).
 *
 * Bolani qo'shayotgan xodim ro'yxatdan birini tanlamasa, ekranda
 * "Please select an item in the list" chiqardi: inglizcha, boshqa
 * shriftda, tizim uslubidan tashqarida. Butun interfeys o'zbekcha
 * turganda bu xabar mahsulotni yarim tarjima qilingan qilib ko'rsatadi.
 *
 * **Nega bitta joyda.** Ilovada 100 dan ortiq `required` bor. Har
 * biriga `onInvalid` yozish — yuzga yaqin nusxa va keyingi yangi forma
 * yana brauzer xabari bilan chiqishi. `invalid` hodisasi ko'pikka
 * chiqmaydi, lekin TUTIB olinadi, shuning uchun bitta hujjat
 * darajasidagi tinglovchi hammasini qamrab oladi.
 *
 * Nativ validatsiyaning O'ZI qoladi: u fokusni birinchi xato maydonga
 * ko'chiradi, ekranni o'sha joyga suradi va skrinriderga aytadi —
 * buni qo'lda yozilgan tekshiruv kamdan-kam to'g'ri bajaradi.
 */

import { t } from '@/lib/i18n'

type Field = HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement

function isField(target: EventTarget | null): target is Field {
  return (
    target instanceof HTMLInputElement ||
    target instanceof HTMLSelectElement ||
    target instanceof HTMLTextAreaElement
  )
}

/** Maydonning holatiga mos xabar; yaroqli maydon uchun bo'sh satr. */
export function messageFor(field: Field): string {
  // Oldingi o'z xabarimiz holatni buzmasin: `validity` ni o'qishdan
  // oldin uni tozalaymiz, aks holda `customError` qolgan hamma
  // bayroqni yopib qo'yadi.
  field.setCustomValidity('')
  const state = field.validity
  if (state.valid) return ''
  if (state.valueMissing) {
    if (field instanceof HTMLSelectElement) return t('Roʻyxatdan birini tanlang.')
    if (
      field instanceof HTMLInputElement &&
      (field.type === 'checkbox' || field.type === 'radio')
    ) {
      return t('Bu belgini qoʻyish kerak.')
    }
    return t('Bu maydonni toʻldiring.')
  }
  if (state.typeMismatch) {
    const type = field instanceof HTMLInputElement ? field.type : ''
    if (type === 'email') return t('Elektron pochta manzili toʻliq emas.')
    if (type === 'url') return t('Havola toʻgʻri emas.')
    return t('Qiymat toʻgʻri emas.')
  }
  if (state.tooShort && field instanceof HTMLInputElement) {
    return t('Kamida {n} belgi kerak.', { n: field.minLength })
  }
  if (state.tooLong && field instanceof HTMLInputElement) {
    return t('Koʻpi bilan {n} belgi.', { n: field.maxLength })
  }
  if (state.rangeUnderflow && field instanceof HTMLInputElement) {
    return t('Qiymat {min} dan kichik boʻlmasin.', { min: field.min })
  }
  if (state.rangeOverflow && field instanceof HTMLInputElement) {
    return t('Qiymat {max} dan katta boʻlmasin.', { max: field.max })
  }
  return t('Qiymat toʻgʻri emas.')
}

/** Tinglovchilarni o'rnatadi; qaytargan funksiya ularni olib tashlaydi. */
export function installValidationMessages(): () => void {
  const onInvalid = (event: Event) => {
    if (!isField(event.target)) return
    event.target.setCustomValidity(messageFor(event.target))
  }
  // O'z xabarimiz MAYDONNI yaroqsiz qilib ushlab turadi: `customError`
  // o'z-o'zidan yo'qolmaydi. Shuning uchun har kiritishda tozalanadi.
  const onEdit = (event: Event) => {
    if (!isField(event.target)) return
    event.target.setCustomValidity('')
  }
  document.addEventListener('invalid', onInvalid, true)
  document.addEventListener('input', onEdit, true)
  document.addEventListener('change', onEdit, true)
  return () => {
    document.removeEventListener('invalid', onInvalid, true)
    document.removeEventListener('input', onEdit, true)
    document.removeEventListener('change', onEdit, true)
  }
}
