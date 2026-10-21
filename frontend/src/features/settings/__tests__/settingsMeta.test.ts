/**
 * Har bir sozlamaning NOMI bor (audit, 2026-10-21).
 *
 * Auditda ekranda `payroll.income_tax_rate` va `tax.regime` xom
 * koʻrindi: nomi yoʻq kalit shunchaki oʻzini koʻrsatadi. Kalitlar
 * roʻyxati backendda, nomlar esa frontendda — ya'ni ular ajralib
 * ketishi tabiiy. Shuning uchun test ikkisini solishtiradi.
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { SETTING_META } from '@/features/settings/settingsMeta'

const SERVICES = resolve(__dirname, '../../../../../backend/apps/settings_app/services.py')

function backendKeys(): string[] {
  const source = readFileSync(SERVICES, 'utf8')
  const block = /DEFAULTS: dict\[str, Any\] = \{([\s\S]*?)\n\}/.exec(source)
  expect(block, 'DEFAULTS topilmadi — backend oʻzgargan boʻlsa testni ham yangilang').toBeTruthy()
  return [...(block?.[1] ?? '').matchAll(/^ {4}"([a-z_0-9.]+)":/gm)].map((match) => match[1])
}

describe('sozlama nomlari', () => {
  it('backenddagi har bir kalitning nomi bor', () => {
    const keys = backendKeys()
    expect(keys.length).toBeGreaterThan(50)
    expect(keys.filter((key) => !(key in SETTING_META))).toEqual([])
  })

  it('nomlar roʻyxatida backendda yoʻq kalit yoʻq', () => {
    const keys = new Set(backendKeys())
    expect(Object.keys(SETTING_META).filter((key) => !keys.has(key))).toEqual([])
  })

  it('har bir nom va izoh boʻsh emas', () => {
    const empty = Object.entries(SETTING_META)
      .filter(([, meta]) => !meta.label.trim() || !meta.help.trim())
      .map(([key]) => key)
    expect(empty).toEqual([])
  })
})
