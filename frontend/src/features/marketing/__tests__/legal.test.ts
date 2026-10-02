/**
 * Huquqiy sahifalar (PLAN 5.8).
 */

import { describe, expect, it } from 'vitest'
import { CONTACT } from '@/config/contact'
import { fillLegal, legal } from '../legal'

const LOCALES = ['uz', 'ru', 'en'] as const
const all = (locale: (typeof LOCALES)[number]) =>
  [...legal[locale].privacySections, ...legal[locale].termsSections]
    .map((s) => `${s.title}\n${s.text}`)
    .join('\n')

describe('huquqiy matn', () => {
  it('uch tilda boʻlimlar soni bir xil', () => {
    for (const locale of LOCALES) {
      expect(legal[locale].privacySections).toHaveLength(legal.uz.privacySections.length)
      expect(legal[locale].termsSections).toHaveLength(legal.uz.termsSections.length)
    }
  })

  it('tugallanmagan "ishga tushishdan oldin" vaʼdasi qolmagan', () => {
    // Eski matnda "aloqa kanali ishga tushishdan oldin eʼlon qilinadi"
    // turardi — hujjat oʻzining chala ekanini aytardi.
    expect(all('uz')).not.toMatch(/ishga tushish/i)
    expect(all('ru')).not.toMatch(/запуск/i)
    expect(all('en')).not.toMatch(/launch/i)
  })

  it('brief talab qilgan rekvizit belgilari matnda bor', () => {
    for (const locale of LOCALES) {
      const text = all(locale)
      for (const token of ['{{YURIDIK_NOM}}', '{{STIR}}', '{{MANZIL}}', '{{SERVER_JOYLASHUVI}}']) {
        expect(text).toContain(token)
      }
    }
  })

  it('aloqa maʼlumotlari doim toʻldiriladi, boʻsh rekvizit esa belgi boʻlib qoladi', () => {
    const filled = fillLegal('{{EMAIL}} · {{TELEGRAM}} · STIR {{STIR}}')
    expect(filled).toContain(CONTACT.email)
    expect(filled).toContain(`@${CONTACT.telegram}`)
    // `.env` da yoʻq — chala hujjat chala koʻrinadi, jimgina yoʻqolmaydi.
    expect(filled).toContain('{{STIR}}')
  })

  it('siyosat ikkala tomon rolini aytadi: bogʻcha — egasi, Radix — ishlov beruvchi', () => {
    expect(all('uz')).toMatch(/BOGʻCHAGA tegishli/)
    expect(all('uz')).toMatch(/30 kun/)
    expect(all('uz')).toMatch(/14 kun/)
  })
})
