import ReactDOM from 'react-dom/client'
import { initI18n } from './lib/i18n'
import './fonts'
import './index.css'

const rootEl = document.getElementById('root')!

/**
 * Ishga tushirish tartibi:
 *  1. Til lug'ati (ru/en uchun bitta kichik chunk; uz — hech narsa).
 *     Ilova modullari `t(…)` ni import paytida ham chaqiradi, shuning
 *     uchun `App` faqat shundan keyin, dinamik import bilan yuklanadi.
 *  2. Prerender qilingan sahifa (kontent allaqachon HTML'da): React ishga
 *     tushishidan OLDIN landing chunk'ini yuklab olamiz, shunda birinchi
 *     render tayyor kontentni «Yuklanmoqda…» ga almashtirmaydi (router.tsx).
 */
async function bootstrap() {
  await initI18n()
  const { App, preloadLanding } = await import('./app/App')
  if (rootEl.hasChildNodes() && /^\/(uz|ru|en)(\/|$)/.test(window.location.pathname)) {
    await preloadLanding().catch(() => undefined)
  }
  ReactDOM.createRoot(rootEl).render(<App />)
}

void bootstrap()
