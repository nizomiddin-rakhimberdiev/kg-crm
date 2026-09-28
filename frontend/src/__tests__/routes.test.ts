/**
 * Marshrut tanlovi — render qilmasdan tekshiriladi.
 *
 * Nega alohida test kerak bo'ldi: `radix-crm.uz` ochilganda sotuv sayti
 * emas, login ekrani chiqardi. Sabab ko'zga tashlanmaydigan joyda edi —
 * React Router marshrutni ro'yxatdagi TARTIB bo'yicha emas, BALL bo'yicha
 * tanlaydi va `index` marshrutga +2 ball qo'shadi. Ildiz `path: '/'` deb
 * yozilgani uchun himoyalangan daraxtdagi `index` marshrut undan yuqori
 * ball olib g'olib chiqardi.
 *
 * Buni na typecheck, na lint, na mavjud testlar ushlay olardi: kod
 * to'g'ri, sahifalar joyida, `/uz` esa ishlayverardi. Uni faqat
 * brauzerda ildizni ochib ko'rgandagina sezish mumkin edi — shuning
 * uchun qaror endi shu yerda qotirilgan.
 */

import { matchRoutes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { routes } from '../router'

/** `/` uchun tanlanadigan eng chuqur marshrutning id'si. */
const leafIdFor = (pathname: string) => {
  const matches = matchRoutes(routes, pathname)
  return matches?.[matches.length - 1]?.route.id
}

describe('ildiz marshruti', () => {
  it('`/` sotuv saytiga tegishli, CRM daraxtiga emas', () => {
    expect(leafIdFor('/')).toBe('marketing-root')
  })
})

describe('sotuv sayti marshrutlari', () => {
  it.each(['/uz', '/ru', '/uz/privacy', '/ru/privacy', '/uz/terms', '/ru/terms'])(
    '%s mos keladi',
    (pathname) => {
      expect(matchRoutes(routes, pathname)).not.toBeNull()
    },
  )
})

describe('CRM marshrutlari', () => {
  it.each(['/login', '/dashboard', '/children', '/payments', '/platform/login'])(
    '%s mos keladi',
    (pathname) => {
      expect(matchRoutes(routes, pathname)).not.toBeNull()
    },
  )

  it('`/dashboard` ildiz marshrutiga tushib qolmaydi', () => {
    expect(leafIdFor('/dashboard')).not.toBe('marketing-root')
  })
})

/**
 * Kirishdan keyingi manzil.
 *
 * Bu ham brauzerdan boshqa hech narsa ushlay olmaydigan xatolar
 * turkumidan: ildiz SaaS nusxasida sotuv saytiga tegishli, shuning
 * uchun kirgan xodimni `/` ga yuborish uni CRM emas, reklama
 * sahifasiga olib borardi.
 */
describe('kirish nuqtasi', () => {
  it('`/home` himoyalangan daraxtga tushadi, sotuv saytiga emas', () => {
    expect(leafIdFor('/home')).not.toBe('marketing-root')
    expect(matchRoutes(routes, '/home')).not.toBeNull()
  })
})
