/**
 * Audit jurnalida xom qiymat qolmasin (audit, 2026-10-21).
 *
 * Auditda bir ustunda ikki til turardi: "view" va "Yangilandi".
 * Sabab oddiy — backend `view`, `approve`, `reject` amallarini
 * yozadi, frontenddagi yorliqlar roʻyxatiga esa ular qoʻshilmagan,
 * va yorligʻi yoʻq qiymat shunchaki oʻzini koʻrsatadi.
 *
 * Shuning uchun test yorliqlarni BACKEND bilan solishtiradi: amal
 * qoʻshilganda yorliq ham qoʻshiladi, aks holda jurnal yana ikki
 * tilda gapiradi.
 */

import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { ACTION_LABELS, ENTITY_LABELS } from '@/features/audit/labels'

const BACKEND = resolve(__dirname, '../../../../../backend/apps')
const MODEL = join(BACKEND, 'audit/models.py')

/** Backenddagi `entity_type="…"` qiymatlari. */
function backendEntities(): string[] {
  const found = new Set<string>()
  const walk = (dir: string) => {
    for (const entry of readdirSync(dir)) {
      const full = join(dir, entry)
      if (entry === 'tests' || entry === '__pycache__' || entry === 'migrations') continue
      if (statSync(full).isDirectory()) walk(full)
      else if (entry.endsWith('.py')) {
        for (const match of readFileSync(full, 'utf8').matchAll(/entity_type="([a-z_]+)"/g)) {
          found.add(match[1])
        }
      }
    }
  }
  walk(BACKEND)
  return [...found].sort()
}

function backendActions(): string[] {
  const source = readFileSync(MODEL, 'utf8')
  const block = /ACTION_CHOICES\s*=\s*\[([\s\S]*?)\n {4}\]/.exec(source)
  expect(
    block,
    'ACTION_CHOICES topilmadi — model oʻzgargan boʻlsa testni ham yangilang',
  ).toBeTruthy()
  return [...(block?.[1] ?? '').matchAll(/\(\s*"([a-z_0-9]+)"/g)].map((match) => match[1])
}

describe('audit yorliqlari', () => {
  it('backenddagi har bir amalning yorligʻi bor', () => {
    const actions = backendActions()
    expect(actions.length).toBeGreaterThan(10)
    expect(actions.filter((action) => !(action in ACTION_LABELS))).toEqual([])
  })

  it('yorliqlar roʻyxatida ortiqcha (backendda yoʻq) amal yoʻq', () => {
    const actions = new Set(backendActions())
    expect(Object.keys(ACTION_LABELS).filter((key) => !actions.has(key))).toEqual([])
  })

  it('backend yozadigan har bir obyekt turining yorligʻi bor', () => {
    const entities = backendEntities()
    expect(entities.length).toBeGreaterThan(30)
    expect(entities.filter((entity) => !(entity in ENTITY_LABELS))).toEqual([])
  })
})
