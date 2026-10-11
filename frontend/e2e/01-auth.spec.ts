/**
 * Kirish — qolgan hamma narsaning sharti.
 *
 * Access token faqat XOTIRADA yashaydi, refresh esa `httpOnly`
 * cookie'da (04 §5). Yaʼni "kirish ishladi" degani — token olindi VA
 * u bilan birinchi soʻrov oʻtdi degani; buni faqat brauzerda
 * tekshirib boʻladi.
 */

import { expect, test } from '@playwright/test'
import { CREDENTIALS, signIn } from './fixtures'

test('kirish va dashboard yuklanishi', async ({ page }) => {
  await signIn(page)
  // Sahifa shunchaki ochilgani yetarli emas — maʼlumot kelgan boʻlsin.
  await expect(page.getByText(/kassadagi qoldiq|bugungi davomat/i).first()).toBeVisible()
})

test('notoʻgʻri parol — xato koʻrinadi, sahifa qotmaydi', async ({ page }) => {
  await page.goto('login')
  await page.locator('#email').fill(CREDENTIALS.email)
  await page.locator('#password').fill('butunlay-notogri-parol')
  await page
    .locator('form')
    .getByRole('button', { name: /kirish/i })
    .click()

  await expect(page.getByRole('alert')).toBeVisible()
  // Va foydalanuvchi hali ham kirish sahifasida — jimgina ichkariga
  // oʻtkazib yuborilmagan.
  await expect(page.locator('#password')).toBeVisible()
})

test('tizimga kirmasdan ichki sahifa ochilmaydi', async ({ page }) => {
  await page.goto('children')
  await expect(page.locator('#password')).toBeVisible()
})
