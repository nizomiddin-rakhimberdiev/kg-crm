/**
 * Ulashish rasmlari (og-uz/ru/en.png) — Brendbuk 1.1.
 *
 * Telegram yoki LinkedIn'da havola tashlanganda odam birinchi SHU
 * rasmni ko'radi. Ilgari ular qo'lda chizilgan edi va rebrendingdan
 * keyin eski ko'k brendda qolib ketdi — shuning uchun endi ular
 * skript bilan, sahifaning o'z matnidan (`content.ts`) chiziladi.
 *
 * Fon — Ildiz: brendbuk 02 da to'q fon "sayt va taqdimot muqovasi"
 * uchun aynan shu variant (B) deb belgilangan, va ulashish kartasi
 * muqovadan boshqa narsa emas.
 *
 *   node scripts/og.mjs
 *
 * Talab: Chrome (headless) va tarmoq — shriftlar Google Fonts'dan.
 */

import { execFileSync } from 'node:child_process'
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'

const ROOT = resolve(import.meta.dirname, '..')
const CHROME =
  process.env.CHROME_PATH ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

// content.ts hech narsa import qilmaydi, shuning uchun uni shundayigina
// bundle qilib o'qiymiz — sahifa matni bilan rasm matni ajralib ketmasin.
const bundle = join(mkdtempSync(join(tmpdir(), 'og-')), 'content.mjs')
execFileSync(
  'npx',
  [
    'esbuild',
    'src/features/landing/content.ts',
    '--bundle',
    '--format=esm',
    `--outfile=${bundle}`,
    '--log-level=error',
  ],
  { cwd: ROOT },
)
const { copy } = await import(bundle)

const MARK = readFileSync(join(ROOT, 'public/brand/radix-belgi.svg'), 'utf8')
  // To'q fonda B varianti: kvadrat Nihol rangida (brendbuk 02).
  .replace('#12352F', '#2E9E6B')
const WORDMARK = /<path d="(M80\.53[^"]+)"/.exec(
  readFileSync(join(ROOT, 'public/brand/radix-logo-asosiy.svg'), 'utf8'),
)[1]

const page = (locale) => {
  const t = copy[locale]
  const modules = t.demo.sidebar.slice(1, 7).join(' · ')
  return `<!doctype html>
<html lang="${locale}"><head><meta charset="utf-8">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Onest:wght@500;600;700&family=Golos+Text:wght@400;500&display=swap" rel="stylesheet">
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{width:1200px;height:630px;background:#12352F;color:#fff;
       font-family:'Golos Text',system-ui,sans-serif;overflow:hidden;position:relative}
  /* O'rik — sahifadagi yagona iliq urg'u (nisbat 1). */
  .seed{position:absolute;right:-130px;top:-130px;width:460px;height:460px;border-radius:50%;
        background:radial-gradient(closest-side,rgba(242,155,85,.20),transparent)}
  .wrap{position:relative;padding:72px 80px;height:100%;display:flex;flex-direction:column}
  .logo{display:flex;align-items:center;gap:0}
  .eyebrow{margin-top:auto;font-size:19px;font-weight:500;letter-spacing:.14em;
           text-transform:uppercase;color:#79C4A4}
  h1{margin-top:22px;font-family:'Onest',sans-serif;font-weight:700;font-size:62px;
     line-height:1.08;letter-spacing:-.025em;max-width:22ch;text-wrap:balance}
  .modules{margin-top:26px;font-size:23px;color:#AEC9C2}
  .foot{margin-top:34px;display:flex;align-items:center;gap:14px;font-size:20px;color:#fff}
  .dot{width:9px;height:9px;border-radius:50%;background:#F29B55}
</style></head><body>
  <div class="seed"></div>
  <div class="wrap">
    <div class="logo">
      <svg viewBox="0 0 185 64" height="52" role="img" aria-label="Radix">
        ${MARK.replace(/<\/?svg[^>]*>/g, '')}
        <path d="${WORDMARK}" fill="#FFFFFF"/>
      </svg>
    </div>
    <p class="eyebrow">${t.hero.eyebrow}</p>
    <h1>${t.hero.title}</h1>
    <p class="modules">${modules}</p>
    <p class="foot"><span class="dot"></span>${t.hero.priceFrom}</p>
  </div>
</body></html>`
}

const port = 9333
const profile = mkdtempSync(join(tmpdir(), 'og-chrome-'))
const proc = (await import('node:child_process')).spawn(
  CHROME,
  [
    '--headless=new',
    '--disable-gpu',
    '--hide-scrollbars',
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profile}`,
    'about:blank',
  ],
  { stdio: 'ignore' },
)

const wait = (ms) => new Promise((r) => setTimeout(r, ms))
await wait(2500)

for (const locale of ['uz', 'ru', 'en']) {
  const html = join(profile, `${locale}.html`)
  writeFileSync(html, page(locale))

  const target = await (
    await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' })
  ).json()
  const ws = new WebSocket(target.webSocketDebuggerUrl)
  let id = 0
  const pending = new Map()
  await new Promise((r) => (ws.onopen = r))
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data)
    if (m.id && pending.has(m.id)) pending.get(m.id)(m.result)
  }
  const send = (method, params = {}) =>
    new Promise((res) => {
      const n = ++id
      pending.set(n, res)
      ws.send(JSON.stringify({ id: n, method, params }))
    })

  await send('Emulation.setDeviceMetricsOverride', {
    width: 1200,
    height: 630,
    deviceScaleFactor: 1,
    mobile: false,
  })
  await send('Page.enable')
  await send('Page.navigate', { url: `file://${html}` })

  // Shriftni kutish SHART: `document.fonts.ready` ning o'zi yetmaydi —
  // Google Fonts kirill bo'lagini alohida fayl qilib beradi va u
  // birinchi joylashuvdan KEYIN so'raladi. Kutmasak, ruscha sarlavha
  // zaxira shriftda suratga tushadi (bir marta shunday bo'lgan).
  await send('Runtime.evaluate', {
    awaitPromise: true,
    expression: `(async () => {
      const text = document.querySelector('h1').textContent
      await document.fonts.ready
      await Promise.all([
        document.fonts.load('700 62px Onest', text),
        document.fonts.load('500 19px "Golos Text"', text),
        document.fonts.load('400 23px "Golos Text"', text),
      ])
      await document.fonts.ready
    })()`,
  })
  await wait(700)
  const shot = await send('Page.captureScreenshot', { format: 'png' })
  writeFileSync(join(ROOT, `public/og-${locale}.png`), Buffer.from(shot.data, 'base64'))
  console.log(`og-${locale}.png yozildi`)
  await send('Page.close')
  ws.close()
}

proc.kill()
// Chrome profilini o'chirishdan oldin yopilishini kutamiz — aks holda
// u hali fayl yozayotgan bo'ladi va rm "directory not empty" beradi.
await wait(1200)
try {
  rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 300 })
} catch {
  // Vaqtinchalik papka — qolib ketsa ham zarari yo'q.
}
