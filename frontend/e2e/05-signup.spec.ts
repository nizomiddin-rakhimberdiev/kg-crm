/**
 * Roʻyxatdan oʻtish — pulning kirish eshigi.
 *
 * **Forma YUBORILMAYDI.** Yuborish `signup_request` va `Lead` yozadi
 * (ADR-28), yaʼni har bir test ishga tushirilganda sotuv roʻyxatiga
 * axlat qoʻshilardi. Shuning uchun bu yerda konversiya uchun eng
 * muhim narsa tekshiriladi: sahifa ochiladimi, maydonlar bormi va
 * **rozilikni belgilamasdan oʻtib boʻlmaydimi**.
 *
 * Roʻyxatdan oʻtish faqat SaaS nusxasida marshrutlanadi (ADR-13), shuning
 * uchun demo stendida bu test oʻtkazib yuboriladi.
 */

import { expect, test } from '@playwright/test'

// `E2E_BASE_URL` berilmasa konfigdagi SUKUT qiymat ishlaydi, ya'ni
// bo'sh satrga qarab bo'lmaydi — aks holda demo stendida ham
// "bu SaaS" deb hisoblanardi va testlar shu yerda yiqilardi.
const BASE = process.env.E2E_BASE_URL ?? 'https://radix-crm.uz/private'
const SAAS = !BASE.includes('/private')

test.skip(!SAAS, 'Roʻyxatdan oʻtish standalone nusxasida yoʻq (ADR-13).')

test('roʻyxatdan oʻtish formasi va rozilik majburiyligi', async ({ page }) => {
  await page.goto('signup')

  await expect(page.getByRole('heading', { name: /15 kunlik sinov/i })).toBeVisible()
  await expect(page.getByLabel(/bogʻcha nomi/i)).toBeVisible()
  await expect(page.getByLabel(/^email$/i)).toBeVisible()

  // Rozilik belgilanmagan — brauzer formani yubormasligi kerak.
  const consent = page.getByRole('checkbox')
  await expect(consent).not.toBeChecked()

  await page.getByLabel(/bogʻcha nomi/i).fill('Sinov bogʻcha')
  await page.getByLabel(/ismingiz/i).fill('Sinov')
  await page.getByLabel(/^email$/i).fill('e2e@example.invalid')
  await page.getByRole('button', { name: /bogʻchani ochish/i }).click()

  // Hali ham shu sahifada: rozilik `required`.
  await expect(page.getByRole('heading', { name: /15 kunlik sinov/i })).toBeVisible()
})

test('kirish va roʻyxatdan oʻtish bir-biriga havola qiladi', async ({ page }) => {
  await page.goto('login')
  await page.getByRole('link', { name: /15 kunlik sinovni boshlang/i }).click()
  await expect(page.getByRole('heading', { name: /15 kunlik sinov/i })).toBeVisible()

  await page.getByRole('link', { name: /^kirish$/i }).click()
  await expect(page.locator('#password')).toBeVisible()
})
