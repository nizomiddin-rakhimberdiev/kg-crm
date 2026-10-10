/**
 * nginx bilan React Router kelishuvi (PLAN 5.6).
 *
 * SaaS nusxasida nginx endi notoʻgʻri manzilga haqiqiy `404` beradi va
 * SPA qobigʻini FAQAT roʻyxatdagi yoʻllarga beradi
 * (`deploy/nginx/_spa_saas.conf`). Bu roʻyxat `router.tsx` dagi
 * yuqori darajali marshrutlar bilan bir xil boʻlishi shart.
 *
 * Nega test: ikki joydagi roʻyxat ertami-kechmi ajraladi, va ajralish
 * eng yomon joyda koʻrinadi — yangi sahifa lokal ishlab chiqishda
 * (Vite hamma narsani SPA'ga beradi) ishlaydi, productionda esa
 * `404` qaytaradi. Uni na typecheck, na boshqa test ushlay olardi.
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import type { RouteObject } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { routes } from '../router'

// `brand.test.ts` bilan bir xil usul: jsdom muhitida `import.meta.url`
// `file://` emas.
const CONF = resolve(__dirname, '../../../deploy/nginx/_spa_saas.conf')

/** `location ~ ^/(a|b|c)(/|$)` dagi roʻyxat. */
function nginxSegments(): Set<string> {
  const text = readFileSync(CONF, 'utf8')
  const match = text.match(/location ~ \^\/\(([a-z|-]+)\)\(\/\|\$\)/)
  if (!match) throw new Error('_spa_saas.conf: SPA yoʻllari roʻyxati topilmadi')
  return new Set(match[1].split('|'))
}

/** Router daraxtidagi har bir yoʻlning BIRINCHI boʻlagi. */
function routerSegments(tree: RouteObject[], parent = ''): Set<string> {
  const found = new Set<string>()
  for (const route of tree) {
    const own = route.path ?? ''
    const full = own.startsWith('/') ? own : `${parent}/${own}`
    const first = full.split('/').filter(Boolean)[0]
    if (first && first !== '*' && !first.startsWith(':')) found.add(first)
    if (route.children) {
      for (const segment of routerSegments(route.children, full.replace(/\/$/, ''))) {
        found.add(segment)
      }
    }
  }
  return found
}

/** Prerender qilingan public sahifalar — nginx ularni FAYL sifatida beradi. */
const PRERENDERED = new Set(['uz', 'ru', 'en'])

/** Bogʻcha manzili (`/t/<slug>/…`) — marshrut emas, `basename` (lib/tenantAddress.ts). */
const TENANT_PREFIX = 't'

describe('nginx SPA roʻyxati', () => {
  it('router.tsx dagi har bir yuqori darajali yoʻl nginx roʻyxatida bor', () => {
    const nginx = nginxSegments()
    const missing = [...routerSegments(routes)].filter(
      (segment) => !PRERENDERED.has(segment) && !nginx.has(segment),
    )
    // Bu yerdagi har bir nom productionda `404` berardi.
    expect(missing).toEqual([])
  })

  it('nginx roʻyxatida ortiqcha yoʻl yoʻq', () => {
    const router = routerSegments(routes)
    const extra = [...nginxSegments()].filter(
      (segment) => segment !== TENANT_PREFIX && !router.has(segment),
    )
    // Ortiqcha nom zararsiz koʻrinadi, lekin u notoʻgʻri manzilga
    // `404` oʻrniga SPA qobigʻini `200` bilan qaytaradi.
    expect(extra).toEqual([])
  })

  it('bogʻcha manzili SPA ga boradi', () => {
    expect(nginxSegments().has(TENANT_PREFIX)).toBe(true)
  })
})

/*
 * `/media/` — ruxsat etilganlar roʻyxati (PLAN 11.5).
 *
 * Ommaviy boʻlishi kerak boʻlgani ikkitagina: logotip va foydalanuvchi
 * rasmi. Qolgani — bolaning tibbiy maʼlumotnomasi va moliyaviy
 * eksportlar — faqat ilovaning ruxsat tekshiradigan endpointi orqali.
 * Ikkalasining ham izohida shunday deb yozilgan edi, lekin nginx
 * ularni baribir berardi; eksport nomlari esa UUID ham emas
 * (`debtors-20260923-1001.csv`), yaʼni sanab chiqsa boʻlardi.
 *
 * Qoida ikkala konfigda ham boʻlishi shart va bittasida unutish oson.
 */
describe('media — faqat ruxsat etilgan kataloglar', () => {
  const configs = [
    ['deploy/nginx/_shared.conf', '/media/'],
    ['deploy/nginx/private-demo.conf', '/private/media/'],
  ] as const

  it.each(configs)('%s faqat brand/ va avatars/ ni beradi', (file, prefix) => {
    const text = readFileSync(resolve(__dirname, '../../..', file), 'utf8')

    // Ruxsat etilgan yoʻl — aynan ikkita katalog bilan.
    const allow = new RegExp(
      `location\\s+~\\s+\\^${prefix.replace(/\//g, '\\/')}\\(\\[\\^\\/\\]\\+\\/\\(\\?:brand\\|avatars\\)`,
    )
    expect(text).toMatch(allow)

    // Va qolgan hammasi — 404.
    const blockStart = text.indexOf(`location ${prefix} {`)
    expect(blockStart).toBeGreaterThan(-1)
    expect(text.slice(blockStart, blockStart + 80)).toMatch(/return\s+404/)
  })

  it.each(configs)('%s da `alias /app/mediafiles/;` qolmagan', (file) => {
    // Yalangʻoch `alias` butun katalogni ochadi — aynan shu nosozlik edi.
    const text = readFileSync(resolve(__dirname, '../../..', file), 'utf8')
    expect(text).not.toMatch(/alias\s+\/app\/mediafiles\/;/)
  })
})
