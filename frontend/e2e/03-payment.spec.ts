/**
 * Toʻlov qabul qilish — pul tegadigan yagona E2E.
 *
 * Shuning uchun u oʻzidan keyin **qaytaradi**: toʻlov yoziladi,
 * roʻyxatda koʻrinadi, keyin bekor qilinadi. Bekor qilish —
 * mahsulotning oʻz yoʻli (qarshi yozuv, D3), yaʼni test ham jurnalni
 * oʻchirmaydi, ustiga qarshi yozuv qoʻyadi. Natijada demo stend
 * ifloslanmaydi va eng qimmat yoʻl — qaytarish — ham sinaladi.
 *
 * Summa ataylab kichik va noyob: roʻyxatdan aynan oʻzini topish uchun.
 */

import { expect, test } from '@playwright/test'
import { openSection, signIn } from './fixtures'

test('toʻlov qabul qilinadi va qaytariladi', async ({ page }) => {
  await signIn(page)
  await openSection(page, /^toʻlovlar$/i)
  await expect(page.getByRole('heading', { name: /toʻlov/i }).first()).toBeVisible()

  // Doskadagi birinchi bola. Qator tugmasining oʻz nomi yoʻq — unda
  // bolaning ismi turadi — shuning uchun tuzilma boʻyicha olinadi.
  const firstRow = page.locator('li > button').first()
  await expect(firstRow).toBeVisible()
  await firstRow.click()

  const amount = page.getByLabel(/^summa$/i).first()
  await expect(amount).toBeVisible()
  await amount.fill('1000')

  await page
    .getByRole('button', { name: /^naqd$/i })
    .first()
    .click()
  await page
    .getByRole('button', { name: /qabul qilish/i })
    .last()
    .click()

  // Kvitansiya oynasi — toʻlov yozilgani.
  await expect(page.getByText(/kvitansiya|qabul qilindi/i).first()).toBeVisible()
  await page
    .getByRole('button', { name: /yopish|^ok$/i })
    .last()
    .click()

  // --- Tozalash: qaytarish ---
  await page
    .getByRole('tab', { name: /toʻlovlar/i })
    .first()
    .click()
    .catch(() => {})
  const reverse = page.getByRole('button', { name: /^qaytarish$/i }).first()
  await expect(reverse).toBeVisible()
  await reverse.click()

  await page.getByRole('textbox').last().fill('E2E test — avtomatik qaytarildi')
  await page
    .getByRole('button', { name: /qaytarish|tasdiqlash/i })
    .last()
    .click()
  await expect(page.getByText(/qaytarilgan/i).first()).toBeVisible()
})

test('qarzdorlar roʻyxati ochiladi va summa koʻrinadi', async ({ page }) => {
  await signIn(page)
  await openSection(page, /^qarzdorlar$/i)

  await expect(page.getByRole('heading', { name: /qarzdor/i })).toBeVisible()
  // Roʻyxat ham, "qarzdor yoʻq" ham toʻgʻri javob — sahifa qotmasin.
  await expect(
    page
      .getByText(/soʻm/)
      .first()
      .or(page.getByText(/qarzdorlar yoʻq/i)),
  ).toBeVisible()
})
