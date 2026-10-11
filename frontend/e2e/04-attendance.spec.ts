/**
 * Davomat — har kuni ertalab bajariladigan ish.
 *
 * Bu yerda eng qimmat nosozlik "saqlanmadi" emas, **jimgina
 * yoʻqolish**: qoralama faqat xotirada va sahifa almashsa yoʻqoladi
 * (PLAN 10.2). Shuning uchun test saqlashdan keyin sahifani QAYTA
 * yuklaydi va belgilangani joyida turganini tekshiradi.
 *
 * Test oʻz shartini OʻZI yaratadi. Dastlabki variant toʻgʻridan-toʻgʻri
 * "Hammasi keldi" ni bosardi va saqlashni kutardi — lekin ikkinchi
 * ishga tushirishda hamma allaqachon belgilangan boʻlib, hech narsa
 * oʻzgarmasdi: "Saqlash" oʻchirilganicha qolar va test qotib qolardi.
 * Stendning holatiga tayangan test — bir marta ishlaydigan test.
 */

import { expect, test } from '@playwright/test'
import { firstVisible, openSection, signIn } from './fixtures'

test.slow()

test('davomat belgilanadi, saqlanadi va qayta yuklashdan keyin qoladi', async ({ page }) => {
  await signIn(page)
  await openSection(page, /^davomat$/i)
  await expect(page.getByRole('heading', { name: /davomat/i })).toBeVisible()

  // Guruhni tanlash SHART emas: sahifa birinchisini oʻzi tanlaydi.
  // Lekin guruhlar ham, jurnal ham asinxron keladi — shuning uchun
  // KUTAMIZ, "bormi?" deb soʻramaymiz: `isVisible()` bilan darhol
  // soʻrash testni jimgina oʻtkazib yuborardi (yashil, lekin hech
  // narsa sinalmagan).
  const markAll = page.getByRole('button', { name: /hammasi keldi/i })
  await expect(markAll).toBeVisible()

  // Telefon va desktop uchun IKKITA saqlash tugmasi bor — biri har
  // doim yashirin (`firstVisible` izohiga qarang).
  const save = () => firstVisible(page.getByRole('button', { name: /^saqlash/i }))

  // --- Oʻzgarish yaratamiz: bitta bolani "Kelmagan" qilamiz ---
  const absent = firstVisible(page.getByRole('button', { name: /: kelmagan$/i }))
  await absent.click()
  await expect(save()).toBeEnabled()
  await save().click()
  await expect(save()).toBeDisabled()

  // --- Endi hammasini qaytaramiz ---
  await markAll.click()
  await expect(save()).toBeEnabled()
  await save().click()
  await expect(save()).toBeDisabled()

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
  await expect(firstVisible(page.getByText(/^keldi$/i))).toBeVisible()
  // Belgilanmaganlar nolga tushgan boʻlsin.
  await expect(firstVisible(page.getByRole('button', { name: /: kelmagan$/i }))).toHaveAttribute(
    'aria-pressed',
    'false',
  )
})
