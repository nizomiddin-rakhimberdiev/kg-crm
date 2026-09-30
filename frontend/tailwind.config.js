/**
 * Radix brend tokenlari — Brendbuk 1.1 (sentyabr 2026).
 *
 * BU FAYL BRENDNING YAGONA MANBASI. Ekranlarda rang "qo'lda" yozilmaydi:
 * hamma joy shu yerdagi shkalalardan oladi, shuning uchun brend bitta
 * fayldan boshqariladi.
 *
 * Palitra — bog' va daraxtdan olingan besh rang:
 *
 *   Ildiz  #12352F  belgi, sarlavha, to'q yuza
 *   Nihol  #2E9E6B  tugmalar, havolalar, "to'langan"
 *   O'rik  #F29B55  urug' nuqta, kichik urg'u
 *   Sut    #F6F7F4  asosiy fon
 *   Tosh   #1B2421  matn, piktogrammalar
 *
 * Har sahifadagi nisbat: Sut 60 · Ildiz 25 · Nihol 10 · Tosh 4 · O'rik 1.
 * Qarzdorlik uchun alohida ogohlantirish rangi #B45F1E — u brend rangi
 * emas, faqat tizim ichida ishlatiladi (`orik-700`).
 *
 * KO'K VA BINAFSHA ATAYLAB ISHLATILMAYDI — raqobatchi CRM tizimlarining
 * deyarli hammasi shu ranglarda. Shu sababli Tailwind'ning `blue`,
 * `sky`, `indigo`, `cyan`, `violet`, `purple`, `fuchsia` shkalalari
 * o'chirilmadi, balki BRENDGA QAYTA YO'NALTIRILDI (pastga qarang): eski
 * yoki yangi kod tasodifan `bg-sky-50` yozsa ham ekranda ko'k chiqmaydi.
 * Yangi kod esa brend nomlarini ishlatadi: `nihol`, `ildiz`, `orik`,
 * `sut`, `tosh`. Buni `src/__tests__/brand.test.ts` tekshirib turadi.
 */

/** Nihol — asosiy yashil. 500 brendbukdagi aniq qiymat, 900 esa Ildiz. */
const nihol = {
  50: '#eef7f2',
  100: '#d4ede0',
  200: '#aadcc5',
  300: '#79c4a4',
  400: '#4cae85',
  500: '#2e9e6b', // Nihol — brendbuk
  // 600 tugma yuzasi: oq matn bilan 4.75:1 (AA). Sof Nihol'da 3.4:1
  // bo'lardi — 14px yarim qalin matn uchun bu yetarli emas.
  600: '#26825a',
  700: '#1e6748',
  800: '#1a5039',
  900: '#12352f', // Ildiz — brendbuk
  950: '#0a211d',
}

/** Ildiz — chuqur, bosiq yashil. To'q yuzalar va "qayd etilgan" holat. */
const ildiz = {
  50: '#edf3f1',
  100: '#d6e4e0',
  200: '#aec9c2',
  300: '#7da79d',
  400: '#4f8478',
  500: '#2f6257',
  600: '#245047',
  700: '#1b423a',
  800: '#163a33',
  900: '#12352f', // Ildiz — brendbuk
  950: '#0a1f1b',
}

/** O'rik — yagona iliq rang. 400 brendbukdagi qiymat, 700 qarzdorlik. */
const orik = {
  50: '#fdf3ea',
  100: '#fbe4d0',
  200: '#f7c7a2',
  300: '#f4b076',
  400: '#f29b55', // O'rik — brendbuk
  500: '#e07f35',
  600: '#c86c26',
  700: '#b45f1e', // Qarzdorlik ogohlantirishi — brendbuk
  800: '#8f4b18',
  900: '#6e3a14',
  950: '#3e200b',
}

/**
 * Tosh — betaraf shkala. 50 Sut, 900 Tosh: ikkalasi ham brendbukdan.
 * Tailwind'ning `slate`'i ko'kka moyil, shuning uchun u shu yashil-kulrang
 * shkala bilan almashtirildi — ilovaning har bir yuzasi va matni shundan.
 */
const tosh = {
  50: '#f6f7f4', // Sut — brendbuk
  100: '#edefea',
  200: '#dde1db',
  300: '#c4cbc2',
  400: '#98a398',
  500: '#67736a',
  600: '#515c55',
  700: '#3e4842',
  800: '#2a332e',
  900: '#1b2421', // Tosh — brendbuk
  950: '#0f1512',
}

/** Xato va o'chirish — tizim rangi, brend rangi emas. Iliq tomonga surilgan. */
const danger = {
  50: '#fdf1ef',
  100: '#fbdfda',
  200: '#f6bfb6',
  300: '#ee9484',
  400: '#e26a55',
  500: '#d24a33',
  600: '#b93a25',
  700: '#9a2e1d',
  800: '#7c2718',
  900: '#5e1f14',
  950: '#340f09',
}

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        // Matn — Golos Text 400/500. Sarlavhalar `font-display` (Onest);
        // `index.css` uni h1–h3 ga o'zi qo'yadi.
        sans: ['Golos Text', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        display: ['Onest', 'Golos Text', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      colors: {
        // Brend nomlari — yangi kod shularni ishlatadi.
        nihol,
        ildiz,
        orik,
        tosh,
        sut: '#f6f7f4',

        // Asosiy: tugma, havola, faol holat.
        brand: nihol,

        // --- Tailwind shkalalarini brendga qayta yo'naltirish ---
        // Quyidagilar mavjud ekranlar uchun: bitta ham fayl qolib
        // ketmasin va yangi kod ham ko'k/binafsha chiqara olmasin.
        slate: tosh,
        gray: tosh,
        zinc: tosh,
        neutral: tosh,
        stone: tosh,

        emerald: nihol, // "to'langan" — brendbukda Nihol
        green: nihol,
        teal: nihol,
        lime: nihol,

        amber: orik, // kutilmoqda, ogohlantirish, qarzdorlik
        orange: orik,
        yellow: orik,

        sky: ildiz, // KO'K EMAS — "qayd etilgan" holat Ildiz rangida
        blue: ildiz,
        indigo: ildiz,
        cyan: ildiz,

        violet: orik, // BINAFSHA EMAS
        purple: orik,
        fuchsia: orik,

        red: danger,
        rose: danger,
      },
      boxShadow: {
        // Soya Tosh rangidan — neytral qora ko'kimtir ko'rinardi.
        card: '0 1px 2px 0 rgb(27 36 33 / 0.05), 0 1px 3px 0 rgb(27 36 33 / 0.07)',
        lift: '0 18px 40px -22px rgb(18 53 47 / 0.35)',
      },
      borderRadius: {
        // Brendbuk 03: tugma va kartochkalarda 12–16 px yumaloqlik.
        lg: '0.75rem', // 12px — tugma, input
        xl: '0.875rem', // 14px
        '2xl': '1rem', // 16px — kartochka
      },
      fontSize: {
        // Brendbuk 05 dagi shkala: H1 48/52, H2 32/38, H3 20/28, matn 16/26.
        'h1-brand': ['3rem', { lineHeight: '3.25rem', letterSpacing: '-0.03em' }],
        'h2-brand': ['2rem', { lineHeight: '2.375rem', letterSpacing: '-0.02em' }],
        'h3-brand': ['1.25rem', { lineHeight: '1.75rem', letterSpacing: '-0.01em' }],
        'body-brand': ['1rem', { lineHeight: '1.625rem' }],
      },
    },
  },
  plugins: [],
}
