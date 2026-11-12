import ReactDOM from 'react-dom/client'
import { installValidationMessages } from './lib/forms/validity'
import { initI18n, t } from './lib/i18n'
import './fonts'
import './index.css'

const rootEl = document.getElementById('root')!

/**
 * Ishga tushirish tartibi:
 *  1. Til lug'ati (ru/en uchun bitta kichik chunk; uz — hech narsa).
 *     Ilova modullari `t(…)` ni import paytida ham chaqiradi, shuning
 *     uchun `App` faqat shundan keyin, dinamik import bilan yuklanadi.
 *  2. Validatsiya xabarlari — brauzerning inglizcha xabari o'rniga
 *     o'zimizning (lib/forms/validity.ts).
 *  3. Prerender qilingan sahifa (kontent allaqachon HTML'da): React ishga
 *     tushishidan OLDIN landing chunk'ini yuklab olamiz, shunda birinchi
 *     render tayyor kontentni «Yuklanmoqda…» ga almashtirmaydi (router.tsx).
 */
async function bootstrap() {
  await initI18n()
  // Brauzer yorlig'i ham tanlangan tilda (audit 2026-11-12, H6): ilova
  // ichida sarlavha `index.html` dagi o'zbekchasida qolardi. Sotuv sayti
  // o'z sarlavhasini `applyPageMeta` bilan baribir yozadi.
  if (document.title === 'Radix CRM — Xususiy bogʻchalarni boshqarish tizimi') {
    document.title = t('Radix CRM — Xususiy bogʻchalarni boshqarish tizimi')
  }
  installValidationMessages()
  const { App, preloadLanding } = await import('./app/App')
  if (rootEl.hasChildNodes() && /^\/(uz|ru|en)(\/|$)/.test(window.location.pathname)) {
    await preloadLanding().catch(() => undefined)
  }
  ReactDOM.createRoot(rootEl).render(<App />)
}

void bootstrap()
