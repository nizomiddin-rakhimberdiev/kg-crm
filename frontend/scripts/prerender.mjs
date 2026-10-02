/**
 * `dist/` ichiga public sahifalarning tayyor HTML'ini yozadi.
 *
 *   dist/index.html            — SPA qobig'i (o'zgarmaydi)
 *   dist/uz/index.html         — bosh sahifa, o'zbekcha, to'liq matn bilan
 *   dist/ru/index.html, dist/uz/privacy/index.html, …
 *
 * nginx `try_files $uri $uri/ /index.html` — `/uz` so'rovi `uz/index.html`
 * ga tushadi, qolgan hamma manzil avvalgidek SPA qobig'iga.
 *
 * Standalone rejimda (ADR-13) sotuv sahifasi yo'q — hech narsa yozilmaydi.
 */

import { mkdir, readFile, readdir, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const dist = path.join(root, 'dist')

if (process.env.VITE_DEPLOYMENT_MODE === 'standalone') {
  console.log('prerender: standalone rejim — public sahifalar yo‘q, o‘tkazib yuborildi')
  process.exit(0)
}

const FONT_HREF =
  'https://fonts.googleapis.com/css2?family=Onest:wght@400;500;600;700;800&display=swap'

// React 18: «useLayoutEffect does nothing on the server» — Reveal/DeepDive
// shu hook'ni brauzer uchun ishlatadi, serverda u shunchaki o'tkazib
// yuboriladi; bu ogohlantirish har komponent uchun takrorlanib build
// log'ini to'ldiradi. Boshqa xatolar avvalgidek ko'rinadi.
const originalError = console.error
console.error = (...args) => {
  if (typeof args[0] === 'string' && args[0].includes('useLayoutEffect does nothing on the server'))
    return
  originalError(...args)
}

const entry = await import(pathToFileURL(path.join(root, 'dist-ssr', 'entry.js')).href)
const template = await readFile(path.join(dist, 'index.html'), 'utf8')

// Landing chunk'ini oldindan yuklash — React ishga tushganda kontent
// «Yuklanmoqda…» ga almashib, yana qaytib kelmasin (router.tsx, main.tsx).
const assets = await readdir(path.join(dist, 'assets'))
const landingChunk = assets.find((f) => /^LandingPage-.*\.js$/.test(f))
const preload = landingChunk ? `<link rel="modulepreload" href="/assets/${landingChunk}" />` : ''

// Qobiqdagi sukut meta (title, description, og:*) olib tashlanadi — sahifa
// o'zinikini qo'yadi; ikkita <title> bo'lmasin.
const stripDefaultMeta = (html) =>
  html
    .replace(/\s*<title>[^<]*<\/title>/, '')
    .replace(/\s*<meta name="description"[^>]*>/, '')
    .replace(/\s*<meta name="robots"[^>]*>/, '')
    .replace(/\s*<meta property="og:[^"]*"[^>]*>/g, '')
    .replace(/\s*<meta name="twitter:card"[^>]*>/, '')
    .replace(/\s*<!--[\s\S]*?-->/g, '')

let count = 0
for (const page of entry.prerenderPages()) {
  const html = stripDefaultMeta(template)
    .replace('<html lang="uz">', `<html lang="${page.lang}">`)
    .replace(
      '</head>',
      `    ${page.head}\n    <link rel="stylesheet" href="${FONT_HREF}" />\n    ${preload}\n  </head>`,
    )
    .replace('<div id="root"></div>', `<div id="root">${page.body}</div>`)
  const dir = path.join(dist, page.path)
  await mkdir(dir, { recursive: true })
  await writeFile(path.join(dir, 'index.html'), html)
  count += 1
  const words = page.body
    .replace(/<[^>]+>/g, ' ')
    .split(/\s+/)
    .filter(Boolean).length
  console.log(`prerender: ${page.path.padEnd(12)} ${String(words).padStart(5)} so‘z`)
}
// --- 404 (PLAN 5.6) ---
//
// SPA skripti OLIB TASHLANADI: React ishga tushsa, notoʻgʻri manzilni
// oʻzi "tuzatib" kirish sahifasiga yuborardi va `404` maʼnosiz
// boʻlardi. Uslublar (Tailwind CSS) qoladi — sahifa brend koʻrinishida.
const notFound = entry.notFoundPage()
const notFoundHtml = stripDefaultMeta(template)
  .replace(/\s*<script type="module"[^>]*><\/script>/, '')
  .replace('</head>', `    ${notFound.head}\n  </head>`)
  .replace('<div id="root"></div>', `<div id="root">${notFound.body}</div>`)
if (notFoundHtml.includes('type="module"')) {
  throw new Error('prerender: 404.html ichida SPA skripti qoldi')
}
await writeFile(path.join(dist, '404.html'), notFoundHtml)
count += 1
console.log('prerender: /404.html      statik, skriptsiz')

console.log(`prerender: ${count} sahifa yozildi`)
