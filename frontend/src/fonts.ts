/**
 * Shriftlar — O'Z serverimizdan (PLAN 5.7 davomi, egasining qarori
 * 2026-10-03).
 *
 * Ilgari Google Fonts'dan yuklanardi: har bir tashrif brauzer IP
 * manzilini Google'ga yuborardi (maxfiylik siyosatida alohida band
 * bo'lib turardi), CSP'da ikkita tashqi manba ochiq edi, va Google
 * sekin yoki bloklangan tarmoqda birinchi ekran shriftsiz chizilardi.
 *
 * `@fontsource` har vazn uchun `unicode-range` bilan bo'laklangan
 * fayllar beradi — brauzer faqat sahifada uchragan bo'lakni yuklaydi
 * (lotin, kirill). O'zbek apostroflari (U+02BB, U+02BC) lotin bo'lagida.
 * Public sayt faqat Onest ishlatadi, shuning uchun u yerda boshqa
 * shriftlar yuklanmaydi (`.marketing`, index.css) — `@font-face` e'loni
 * yuklash emas.
 *
 * Vaznlar — ishlatilganlari: Onest 400–800 (sayt sarlavhalari 800 gacha),
 * Golos Text 400–700 (ilova matni), JetBrains Mono 400–600 (`.num`).
 */

import '@fontsource/onest/400.css'
import '@fontsource/onest/500.css'
import '@fontsource/onest/600.css'
import '@fontsource/onest/700.css'
import '@fontsource/onest/800.css'
import '@fontsource/golos-text/400.css'
import '@fontsource/golos-text/500.css'
import '@fontsource/golos-text/600.css'
import '@fontsource/golos-text/700.css'
import '@fontsource/jetbrains-mono/400.css'
import '@fontsource/jetbrains-mono/500.css'
import '@fontsource/jetbrains-mono/600.css'
