/**
 * Umumiy yordamchilar: kirish va noyob nom.
 *
 * Kirish HAR BIR testda qaytadan bajariladi, saqlangan sessiyadan
 * emas. Sekinroq, lekin kirishning oʻzi ham sinaladi — va aynan u
 * buzilsa, qolgan hamma narsa ishlamaydi.
 */

import { expect, type Page } from '@playwright/test'

export const CREDENTIALS = {
  email: process.env.E2E_EMAIL ?? '',
  password: process.env.E2E_PASSWORD ?? '',
}

/** Har bir ishga tushirishda boshqacha — test yozuvlari bir-biriga tegmasin. */
export const stamp = (): string => `E2E-${Date.now().toString().slice(-8)}`

export async function signIn(page: Page): Promise<void> {
  if (!CREDENTIALS.email || !CREDENTIALS.password) {
    throw new Error('E2E_EMAIL va E2E_PASSWORD env oʻzgaruvchilari kerak (.env.example).')
  }
  await page.goto('login')
  await page.locator('#email').fill(CREDENTIALS.email)
  await page.locator('#password').fill(CREDENTIALS.password)
  await page
    .locator('form')
    .getByRole('button', { name: /kirish/i })
    .click()
  // Dashboard'ning oʻz sarlavhasi — URL emas: URL token kelishidan
  // oldin ham oʻzgarishi mumkin.
  await expect(page.getByRole('heading', { name: /boshqaruv paneli/i })).toBeVisible()
}

/**
 * Telefonda yon menyu yopiq turadi — avval uni ochish kerak.
 * Keng ekranda tugma umuman yoʻq, shuning uchun tekshirib oʻtamiz.
 */
export async function openSection(page: Page, name: RegExp): Promise<void> {
  const burger = page.getByRole('button', { name: /menyuni ochish/i })
  if (await burger.isVisible().catch(() => false)) {
    await burger.click()
  }
  await page.getByRole('link', { name }).first().click()
}
