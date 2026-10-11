/**
 * Bola qoʻshish — tizimdagi birinchi haqiqiy ish.
 *
 * Test oʻzidan keyin tozalaydi: qoʻshilgan bola arxivlanadi. Toʻliq
 * oʻchirish yoʻqdan afzal — moliyaviy izi boʻlgan bola hech qachon
 * oʻchirilmaydi (Q6), va arxivlash aynan mahsulotning oʻz yoʻli.
 */

import { expect, test } from '@playwright/test'
import { openSection, signIn, stamp } from './fixtures'

test('bola qoʻshiladi, roʻyxatda koʻrinadi va arxivlanadi', async ({ page }) => {
  const surname = stamp()

  await signIn(page)
  await openSection(page, /^bolalar$/i)
  await expect(page.getByRole('heading', { name: /^bolalar/i })).toBeVisible()

  await page
    .getByRole('button', { name: /bola qoʻshish|yangi bola/i })
    .first()
    .click()

  await page.locator('#last_name, [name="last_name"]').first().fill(surname)
  await page.locator('#first_name, [name="first_name"]').first().fill('Sinov')
  // Tugʻilgan sana — `DateInput`, dd.mm.yyyy (05 §17.1).
  await page.getByLabel(/tugʻilgan sana/i).fill('12.01.2021')

  await page.getByRole('button', { name: /^saqlash$/i }).click()

  // Roʻyxatda paydo boʻldi.
  await expect(page.getByText(surname).first()).toBeVisible()

  // --- Tozalash ---
  await page.getByText(surname).first().click()
  await page.getByRole('button', { name: /arxivlash/i }).click()
  // Tasdiq oynasi chiqishi mumkin.
  const confirm = page.getByRole('button', { name: /^arxivlash$|^ha$|tasdiqlash/i }).last()
  if (await confirm.isVisible().catch(() => false)) await confirm.click()
  await expect(page.getByText(/arxivlangan|arxivda/i).first()).toBeVisible()
})
