/**
 * Qulaylik darvozalari (PLAN 4.8).
 *
 * Bu uchta qoida bir marta tuzatilib, keyin qoʻriqlanmasa, ertami-
 * kechmi qaytadi: ular koʻzga tashlanmaydi va hech qanday testni
 * yiqitmaydi. Shuning uchun ular SHU testda.
 *
 * Public sayt (`features/landing`, `features/marketing`) qolgan
 * tekshiruvlardan chetda, lekin 12px qoidasi unga HAM tegishli (PLAN
 * 5.7): avval namunaviy ekranlardagi 10–11px yozuvlar "tasvirning bir
 * qismi" deb chetda qoldirilgan edi, lekin ularni odam oʻqiydi —
 * aynan shu ekranlar mahsulotni koʻrsatadi.
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

/** 12px qoidasi uchun — public sayt bilan birga. */
function publicFiles(): string[] {
  const out: string[] = []
  for (const part of ['features/landing', 'features/marketing']) {
    const walkAll = (dir: string) => {
      for (const entry of readdirSync(dir)) {
        const full = join(dir, entry)
        if (entry === '__tests__') continue
        if (statSync(full).isDirectory()) walkAll(full)
        else if (full.endsWith('.tsx')) out.push(full)
      }
    }
    walkAll(join(SRC, part))
  }
  return out
}

describe('a11y', () => {
  it('12px dan kichik matn yoʻq', () => {
    // Bogʻcha mudirasi 40+ yoshda boʻlishi odatiy hol va u ekranga
    // qoʻl uzunligida qaraydi; 10px yozuv oʻqilmaydi.
    const offenders: string[] = []
    for (const file of [...files, ...publicFiles()]) {
      const text = readFileSync(file, 'utf8')
      // `10.5px` ham — kasr oʻlcham avval qoidadan sirgʻalib oʻtardi.
      // Grafik o'qlari ham: Recharts `fontSize={11}` Tailwind klassi emas va
      // avval bu tekshiruvdan o'tib ketardi (Hisobotlar sahifasi).
      const found = [
        ...(text.match(/text-\[(\d+(?:\.\d+)?)px\]/g) ?? []),
        ...(text.match(/fontSize(?:=\{|: ?)\d+(?:\.\d+)?/g) ?? []),
      ]
      for (const match of found) {
        const size = Number(/\d+(?:\.\d+)?/.exec(match)?.[0] ?? 0)
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

  it('har bir `aria-modal` dialogda fokus tutqichi bor', () => {
    /*
     * `aria-modal="true"` ekranni oʻquvchiga "orqasidagi narsa yoʻq"
     * deydi, lekin Tab baribir orqaga oʻtadi (PLAN 10.15). Uchinchi
     * dialog yozilganda bu qoida eng oson unutiladigan narsa, shuning
     * uchun u testda: modal boʻlgan fayl `useFocusTrap` ni chaqirsin.
     */
    const offenders: string[] = []
    for (const file of files) {
      const text = readFileSync(file, 'utf8')
      if (!text.includes('aria-modal="true"')) continue
      if (text.includes('useFocusTrap')) continue
      offenders.push(file.replace(SRC, ''))
    }
    expect(offenders).toEqual([])
  })

  it('native `input[type=date]` ishlatilmaydi', () => {
    /*
     * Qoida hujjatda bor edi (05 §17.1) — va aynan eng koʻp
     * ishlatiladigan formada, bola qoʻshishda, buzilgan edi. Uni
     * birorta test emas, brauzerdagi E2E topdi: Playwright sanani
     * `dd.mm.yyyy` koʻrinishida kirita olmadi, chunki maydon
     * brauzerning oʻziniki edi va u boshqa tartib kutardi.
     *
     * Shuning uchun qoida endi bu yerda: `components/ui/DateInput`
     * ning oʻzi istisno, qolgan hamma joyda native maydon yoʻq.
     */
    const offenders: string[] = []
    for (const file of files) {
      if (file.endsWith('DateInput.tsx')) continue
      if (/type=["']date["']/.test(readFileSync(file, 'utf8'))) {
        offenders.push(file.replace(SRC, ''))
      }
    }
    expect(offenders).toEqual([])
  })

  it('native `input[type=month]` ishlatilmaydi', () => {
    /*
     * Native oy maydoni oy nomini BRAUZER lokali bo'yicha chiqaradi:
     * butun interfeys o'zbekcha turganda tanlagichda "October 2026"
     * yozilardi (audit, 2026-10-21). Javob `DateInput` bilan bir xil —
     * `components/ui/MonthInput`.
     */
    const offenders: string[] = []
    for (const file of files) {
      if (file.endsWith('MonthInput.tsx')) continue
      if (/type=["']month["']/.test(readFileSync(file, 'utf8'))) {
        offenders.push(file.replace(SRC, ''))
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
