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

  // Guruhni tanlash SHART emas: sahifa birinchisini oʻzi tanlaydi.
  // Lekin guruhlar ham, jurnal ham asinxron keladi — shuning uchun
  // tugmani "bormi?" deb soʻramay, KUTAMIZ. Dastlabki variant
  // `isVisible()` bilan darhol soʻrardi va test jimgina oʻtkazib
  // yuborilardi: yashil, lekin hech narsa sinalmagan.
  const markAll = page.getByRole('button', { name: /hammasi keldi/i })
  await expect(markAll).toBeVisible()
  await markAll.click()

  await page
    .getByRole('button', { name: /^saqlash/i })
    .first()
    .click()
  await expect(page.getByText(/saqlandi|belgilandi/i).first()).toBeVisible()

  // Eng muhimi: qayta yuklashdan keyin ham joyida.
  //
  // Bu qator ikki narsani birdan tekshiradi. Birinchisi — davomat
  // haqiqatan SAQLANGANmi. Ikkinchisi — qayta yuklash foydalanuvchini
  // tizimdan chiqarib yubormaydimi: access token faqat xotirada
  // yashaydi va uni `radix_refresh` cookie tiklaydi (04 §5). Aynan shu
  // yerda nosozlik topilgan edi — cookie yoʻli `/api/v1/auth` deb
  // qotirilgan, standalone nusxada esa API `/private/api/v1/...` da,
  // yaʼni brauzer cookie'ni umuman yubormasdi.
  await page.reload()
  await expect(page.getByRole('heading', { name: /davomat/i })).toBeVisible()
  await expect(page.getByText(/^keldi$/i).first()).toBeVisible()
})
