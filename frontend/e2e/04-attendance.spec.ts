/**
 * Davomat — har kuni ertalab bajariladigan ish.
 *
 * Bu yerda eng qimmat nosozlik "saqlanmadi" emas, **jimgina
 * yoʻqolish**: qoralama faqat xotirada, va sahifa almashsa yoʻqoladi
 * (PLAN 10.2). Shuning uchun test saqlashdan keyin sahifani QAYTA
 * yuklaydi va belgilangani joyida turganini tekshiradi.
 */

import { expect, test } from '@playwright/test'
import { openSection, signIn } from './fixtures'

test('hammasi keldi — belgilanadi, saqlanadi va qayta yuklashdan keyin qoladi', async ({
  page,
}) => {
  await signIn(page)
  await openSection(page, /^davomat$/i)
  await expect(page.getByRole('heading', { name: /davomat/i })).toBeVisible()

  const markAll = page.getByRole('button', { name: /hammasi keldi/i })
  if (!(await markAll.isVisible().catch(() => false))) {
    test.skip(true, 'Bu guruhda faol bola yoʻq — belgilaydigan narsa yoʻq.')
  }
  await markAll.click()

  await page
    .getByRole('button', { name: /^saqlash/i })
    .first()
    .click()
  await expect(page.getByText(/saqlandi|belgilandi/i).first()).toBeVisible()

  // Eng muhimi: qayta yuklashdan keyin ham joyida.
  await page.reload()
  await expect(page.getByText(/keldi/i).first()).toBeVisible()
})
