/**
 * Brauzerdagi E2E (PLAN 11.8).
 *
 * Nega kerak. Unit testlar komponentni, backend testlari esa
 * endpointni tekshiradi — oʻrtadagi narsani hech kim tekshirmaydi:
 * token haqiqatan olinadimi, forma haqiqatan yuboriladimi, javob
 * ekranda haqiqatan koʻrinadimi. Bu sessiyada aynan shunday
 * nosozliklar chiqdi (fokus tutqichi, media yoʻllari, N+1), va
 * ularning birortasi ham mavjud testlarda koʻrinmasdi.
 *
 * **Qaysi stendga qarshi.** Sukut boʻyicha `/private` demo stendi:
 * u aynan shu maqsad uchun turibdi va undagi maʼlumot haqiqiy
 * mijozniki emas. Mijoz stendiga qarshi ishga tushirmang — testlar
 * yozadi.
 *
 * Kirish maʼlumotlari FAQAT env orqali (`.env.example` ga qarang):
 * parol repoda turmasligi kerak.
 */

import { defineConfig, devices } from '@playwright/test'

// Oxiridagi `/` MAJBURIY. Usiz `goto('login')` ham `/private` ni
// almashtirib yuboradi, chunki URL birikishi oxirgi boʻlakni tashlaydi —
// va soʻrovlar jimgina BOSHQA stendga ketadi (bu aynan shunday boʻldi).
const raw = process.env.E2E_BASE_URL ?? 'https://radix-crm.uz/private'
const baseURL = raw.endsWith('/') ? raw : `${raw}/`

export default defineConfig({
  testDir: './e2e',
  // Yozadigan testlar bir-biriga xalaqit bermasin: bitta ishchi.
  // Tezlik bu yerda maqsad emas — ishonch maqsad.
  workers: 1,
  fullyParallel: false,
  // Jonli stend — tarmoq sekin boʻlishi mumkin.
  timeout: 60_000,
  expect: { timeout: 15_000 },
  retries: process.env.CI ? 1 : 0,
  reporter: [['list']],
  use: {
    baseURL,
    locale: 'uz-UZ',
    timezoneId: 'Asia/Tashkent',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    // Telefon — bu mahsulotda asosiy qurilma (PLAN 10).
    { name: 'mobile', use: { ...devices['iPhone 13'] } },
  ],
})
