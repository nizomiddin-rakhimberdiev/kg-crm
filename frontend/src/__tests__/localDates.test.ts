/**
 * Sana MAHALLIY qismlardan quriladi (audit, 2026-10-30).
 *
 * `toISOString()` sanani UTC'ga oʻgiradi. Toshkent UTC+5 boʻlgani
 * uchun mahalliy yarim tun — oldingi kunning 19:00 i, yaʼni
 * `new Date(2026, 9, 1).toISOString()` → `2026-09-30`.
 *
 * Auditda bu "Shu oy" filtrida koʻrindi: chiqimlar sahifasi oktabr
 * uchun `from=2026-09-30&to=2026-10-30` soʻrardi — sentabrning
 * oxirgi kuni ichkarida, oktabrning 31-kuni esa tashqarida qolardi.
 * Raqam notoʻgʻri boʻlardi va buni hech narsa koʻrsatmasdi.
 *
 * Toʻgʻri vosita `lib/format.ts` da allaqachon bor (`isoDate`,
 * `today`) — bu test shunchaki undan chetga chiqishni taqiqlaydi.
 */

import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..')

function sources(dir: string, found: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry)
    if (statSync(path).isDirectory()) {
      if (entry === '__tests__' || entry === 'node_modules') continue
      sources(path, found)
    } else if (/\.tsx?$/.test(entry) && !entry.endsWith('.test.ts')) {
      found.push(path)
    }
  }
  return found
}

/** Izohlar hisobga olinmaydi — ularda aynan shu tuzoq tushuntirilgan. */
const withoutComments = (text: string): string =>
  text
    .split('\n')
    .filter((line) => {
      const trimmed = line.trim()
      return !trimmed.startsWith('//') && !trimmed.startsWith('*') && !trimmed.startsWith('/*')
    })
    .join('\n')

describe('sana', () => {
  it('hech qayerda `toISOString()` bilan qurilmaydi', () => {
    const guilty = sources(ROOT)
      .filter((path) => /toISOString\(\)/.test(withoutComments(readFileSync(path, 'utf8'))))
      .map((path) => relative(ROOT, path))
    expect(guilty).toEqual([])
  })
})
