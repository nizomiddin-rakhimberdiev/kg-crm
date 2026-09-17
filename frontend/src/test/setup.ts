import '@testing-library/jest-dom/vitest'

/**
 * `IntersectionObserver` — jsdom'da yo'q.
 *
 * Marketing sahifasi scroll bo'ylab ochiladigan bloklardan iborat
 * (framer-motion `whileInView`), va u ichida shu API'ni chaqiradi.
 * Polyfillsiz test muhiti "ReferenceError" bilan yiqiladi — mahsulotda
 * esa hech qanday muammo yo'q, chunki barcha maqsadli brauzerlarda bu
 * API mavjud.
 *
 * Stub ATAYLAB darhol "ko'rinadi" deb xabar beradi: testlar kontentni
 * scroll qilmasdan tekshirishi kerak, aks holda har bir tekshiruv
 * animatsiya tugashini kutib o'tirardi.
 */
class IntersectionObserverStub implements IntersectionObserver {
  readonly root: Element | Document | null = null
  readonly rootMargin: string = ''
  readonly thresholds: ReadonlyArray<number> = []

  constructor(private readonly callback: IntersectionObserverCallback) {}

  observe(target: Element): void {
    this.callback(
      [{ isIntersecting: true, target } as IntersectionObserverEntry],
      this as IntersectionObserver,
    )
  }

  unobserve(): void {}
  disconnect(): void {}
  takeRecords(): IntersectionObserverEntry[] {
    return []
  }
}

globalThis.IntersectionObserver =
  IntersectionObserverStub as unknown as typeof IntersectionObserver
