/**
 * Qulaylik darvozalari (PLAN 4.8).
 *
 * Bu uchta qoida bir marta tuzatilib, keyin qoʻriqlanmasa, ertami-
 * kechmi qaytadi: ular koʻzga tashlanmaydi va hech qanday testni
 * yiqitmaydi. Shuning uchun ular SHU testda.
 *
 * Landing sahifasi chetda: undagi 10–11px yozuvlar namunaviy ekran
 * TASVIRINING bir qismi (`ui/Mock.tsx`) — oʻqiladigan matn emas, va
 * ularni kattalashtirish tasvirni buzadi.
 */

import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const SRC = resolve(__dirname, '..')
const SKIP_DIRS = ['__tests__', 'features/landing', 'features/marketing']

function walk(dir: string, files: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry)
    const relative = full.replace(`${SRC}/`, '')
    if (SKIP_DIRS.some((part) => relative.startsWith(part) || relative.includes(`/${part}`))) {
      continue
    }
    if (statSync(full).isDirectory()) walk(full, files)
    else if (full.endsWith('.tsx')) files.push(full)
  }
  return files
}

/** `<tag …>` ni topadi — `=>` ichidagi `>` ni hisobga olmaydi. */
function openTags(source: string, tag: string): string[] {
  const out: string[] = []
  let i = 0
  for (;;) {
    const start = source.indexOf(tag, i)
    if (start < 0) break
    let depth = 0
    let j = start + tag.length
    for (; j < source.length; j += 1) {
      const ch = source[j]
      if (ch === '{') depth += 1
      else if (ch === '}') depth -= 1
      else if (depth === 0 && (ch === '>' || source.slice(j, j + 2) === '/>')) break
    }
    out.push(source.slice(start, j + 1))
    i = j + 1
  }
  return out
}

const files = walk(SRC)

describe('a11y', () => {
  it('12px dan kichik matn yoʻq', () => {
    // Bogʻcha mudirasi 40+ yoshda boʻlishi odatiy hol va u ekranga
    // qoʻl uzunligida qaraydi; 10px yozuv oʻqilmaydi.
    const offenders: string[] = []
    for (const file of files) {
      const text = readFileSync(file, 'utf8')
      const found = text.match(/text-\[(\d+)px\]/g) ?? []
      for (const match of found) {
        const size = Number(/\d+/.exec(match)?.[0] ?? 0)
        if (size < 12) offenders.push(`${file.replace(SRC, '')}: ${match}`)
      }
    }
    expect(offenders).toEqual([])
  })

  it('placeholder LABEL vazifasini bajarmaydi', () => {
    // Placeholder yozish boshlanishi bilan yoʻqoladi: toʻldirilgan
    // formani qayta oʻqiyotgan odam maydon nimaligini bilmaydi.
    const offenders: string[] = []
    for (const file of files) {
      const text = readFileSync(file, 'utf8')
      for (const tag of [...openTags(text, '<input'), ...openTags(text, '<textarea')]) {
        // `placeholder=` atributi — Tailwind'ning `placeholder:`
        // variantidan farqli.
        if (!tag.includes('placeholder=')) continue
        if (tag.includes('aria-label') || / id=/.test(tag)) continue
        offenders.push(`${file.replace(SRC, '')}: ${tag.slice(0, 60)}`)
      }
    }
    expect(offenders).toEqual([])
  })

  it('`title` boʻlgan tugmada `aria-label` ham bor', () => {
    // `title` — sichqoncha uchun maslahat; skrinrider uchun ishonchli
    // nom `aria-label`.
    const offenders: string[] = []
    for (const file of files) {
      const text = readFileSync(file, 'utf8')
      for (const tag of openTags(text, '<button')) {
        if (!tag.includes('title=')) continue
        if (tag.includes('aria-label')) continue
        offenders.push(`${file.replace(SRC, '')}: ${tag.slice(0, 60)}`)
      }
    }
    expect(offenders).toEqual([])
  })

  it('koʻrinadigan fokus butun ilovada belgilangan', () => {
    const css = readFileSync(join(SRC, 'index.css'), 'utf8')
    // `:focus` emas, `:focus-visible`: sichqoncha bosganda halqa
    // chiqmasligi kerak.
    expect(css).toMatch(/:focus-visible\s*\{[^}]*ring-2/)
  })
})
