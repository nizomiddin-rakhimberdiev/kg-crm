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
import { firstVisible, openSection, signIn } from './fixtures'

test('toʻlov qabul qilinadi va qaytariladi', async ({ page }) => {
  await signIn(page)
  await openSection(page, /^toʻlovlar$/i)
  await expect(page.getByRole('heading', { name: /toʻlov/i }).first()).toBeVisible()

  // Doskadagi birinchi bola. Qator tugmasining oʻz nomi yoʻq — unda
  // bolaning ismi turadi — shuning uchun tuzilma boʻyicha olinadi.
  const firstRow = page.locator('li > button').first()
  await expect(firstRow).toBeVisible()
  await firstRow.click()

  // Oyna ichida qolamiz: sahifada ham "Naqd kassa" bor va ankorsiz
  // qidiruv undan ham ushlab qolardi.
  const dialog = page.getByRole('dialog')
  const amount = dialog.getByLabel(/^summa$/i).first()
  await expect(amount).toBeVisible()
  await amount.fill('1000')

  // Usul tugmasining nomi faqat "Naqd" emas — ichida summa ham bor,
  // shuning uchun ankorsiz.
  await dialog.getByRole('button', { name: /naqd/i }).first().click()
  await dialog
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
  //
  // Qaytarish tugmasi JURNAL yorligʻida — doskada emas. Doskada
  // toʻlov qabul qilinadi, jurnalda esa yozuvlar koʻrinadi.
  await page
    .getByRole('button', { name: /^jurnal$/i })
    .first()
    .click()
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
  // Qarzdorlar — Toʻlovlar ichidagi tab (audit, 2026-10-21). Alohida
  // menyu punkti yoʻq; eski `/debtors` havolasi shu tabga
  // yoʻnaltiradi.
  await openSection(page, /^toʻlovlar$/i)
  await page.getByRole('button', { name: /^qarzdorlar$/i }).click()

  // Roʻyxat ham, "qarzdor yoʻq" ham toʻgʻri javob — sahifa qotmasin.
  //
  // `visible: true` MAJBURIY: jadval telefonda `hidden sm:block` bilan
  // yashiringan, lekin DOM'da turadi — `.first()` aynan oʻshani
  // tanlab, "element bor, lekin koʻrinmaydi" deb yiqilardi.
  const anyAmount = firstVisible(page.getByText(/soʻm/))
  const emptyState = firstVisible(page.getByText(/qarzdor yoʻq/i))
  await expect(anyAmount.or(emptyState)).toBeVisible()
})

test('eski /debtors havolasi tabga yoʻnaltiradi', async ({ page }) => {
  await signIn(page)
  // Radix Intelligence yozuvlarida bu havola BAZADA turadi
  // (`rules.py`: `/debtors?overdue_days=15`), ya'ni u ishlashi shart.
  // Nisbiy yoʻl MAJBURIY: boshida `/` boʻlsa, Playwright uni
  // baseURL'ning YOʻLINI almashtirib yuboradi va soʻrov `/private`
  // stendi oʻrniga mijoz stendiga ketadi (`playwright.config.ts`
  // dagi izoh — aynan shu tuzoq).
  await page.goto('debtors?overdue_days=15')
  await expect(page).toHaveURL(/payments\?tab=debtors&overdue_days=15/)
})
