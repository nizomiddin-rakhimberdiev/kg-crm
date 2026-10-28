/**
 * Pul chiqadigan ikki yangi yoʻl (mijoz soʻrovi, 2026-10-28).
 *
 * **Qarzga berilgan pul** (ADR-48) chiqim emas: u kassadan chiqadi,
 * lekin qaytishi kutilmoqda. Test uni berib, keyin qaytaradi — yaʼni
 * demo stendda qoldiq oʻzgarmay qoladi va eng qimmat yoʻl ham
 * sinaladi.
 *
 * **Usulni tuzatish** (ADR-47) — kassirning eng koʻp uchraydigan
 * xatosi: "naqd" bosilgan, pul esa terminaldan tushgan. Test toʻlovni
 * yozadi, usulini tuzatadi va oxirida qaytaradi.
 */

import { expect, test } from '@playwright/test'
import { chooseOption, firstVisible, openSection, signIn, stamp } from './fixtures'

test('qarz beriladi va qaytariladi', async ({ page }) => {
  const person = stamp()

  await signIn(page)
  await openSection(page, /^chiqimlar$/i)

  await page.getByRole('button', { name: /^qarz berish$/i }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByLabel(/^kimga/i).fill(person)
  await dialog.getByLabel(/^summa/i).fill('1000')
  await dialog.getByLabel(/^nima uchun/i).fill('E2E sinov')
  await chooseOption(page, /qaysi hisobdan/i, /kassa|naqd/i)
  await dialog.getByRole('button', { name: /^saqlash$/i }).click()

  // Roʻyxatda paydo boʻldi va qaytmagan deb turibdi.
  const row = page.locator('li').filter({ hasText: person }).first()
  await expect(row).toBeVisible()
  await expect(row.getByText(/qaytmagan/i)).toBeVisible()

  // --- Tozalash: qaytarish ---
  await row.getByRole('button', { name: /^qaytdi$/i }).click()
  const back = page.getByRole('dialog')
  await back.getByRole('button', { name: /^saqlash$/i }).click()

  await expect(
    page
      .locator('li')
      .filter({ hasText: person })
      .first()
      .getByText(/toʻliq qaytdi/i),
  ).toBeVisible()
})

test('toʻlov usuli oʻsha kuni tuzatiladi', async ({ page }) => {
  await signIn(page)
  await openSection(page, /^toʻlovlar$/i)

  const firstRow = page.locator('li > button').first()
  await expect(firstRow).toBeVisible()
  await firstRow.click()

  const dialog = page.getByRole('dialog')
  const amount = dialog.getByLabel(/^summa$/i).first()
  await amount.fill('1000')
  await dialog.getByRole('button', { name: /naqd/i }).first().click()
  await dialog
    .getByRole('button', { name: /qabul qilish/i })
    .last()
    .click()
  // Kvitansiya oynasi toʻlov yozilgandan KEYIN ochiladi — yaʼni uni
  // kutib turish kerak. Usiz "oyna yopildimi?" tekshiruvi oyna hali
  // ochilmagan paytda oʻtib ketardi, keyin esa qoplama jadval
  // ustidagi har bosishni yutardi.
  const receipt = page.getByRole('heading', { name: /kvitansiya/i })
  await expect(receipt).toBeVisible()
  // Ikki oyna ustma-ust turadi (toʻlov oynasi va kvitansiya), shuning
  // uchun yopish tugmasi AYNAN kvitansiyaniki boʻlishi kerak.
  await page
    .getByRole('dialog')
    .filter({ has: receipt })
    .getByRole('button', { name: /yopish/i })
    .first()
    .click()
  await expect(receipt).toBeHidden()

  await page
    .getByRole('button', { name: /^jurnal$/i })
    .first()
    .click()

  // Usulni tuzatish — faqat bugungi toʻlovda chiqadi.
  const correct = firstVisible(page.getByRole('button', { name: /toʻlov usulini tuzatish/i }))
  await expect(correct).toBeVisible()
  await correct.click()

  const fix = page.getByRole('dialog')
  await chooseOption(page, /toʻlov usuli/i, /terminal/i, fix)
  await fix.getByLabel(/^sabab/i).fill('E2E sinov — terminal')
  await fix.getByRole('button', { name: /^saqlash$/i }).click()

  // Jurnal qatori endi terminal deb turibdi.
  //
  // Tekshiruv AYNAN katakda: `getByText(/terminal/i)` yashirin native
  // maydondagi `<option>` ni ham topadi — u hech qachon koʻrinmaydi,
  // va test shu yerda bekorga kutib turardi.
  await expect(firstVisible(page.getByRole('cell', { name: /^terminal$/i }))).toBeVisible()

  // --- Tozalash: qaytarish ---
  const reverse = page.getByRole('button', { name: /^qaytarish$/i }).first()
  await reverse.click()
  await page.getByRole('textbox').last().fill('E2E test — avtomatik qaytarildi')
  await page
    .getByRole('button', { name: /qaytarish|tasdiqlash/i })
    .last()
    .click()
  await expect(page.getByText(/qaytarilgan/i).first()).toBeVisible()
})
