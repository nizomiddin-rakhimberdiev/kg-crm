/**
 * ESLint — 11 500 qator TypeScript uzoq vaqt hech qanday linterdan
 * o'tmagan edi (P1-007).
 *
 * Qoidalar ATAYLAB tor: faqat HAQIQIY xatolarni ushlaydiganlar.
 * Uslub qoidalari qo'shilsa, birinchi ishga tushirishda yuzlab
 * ogohlantirish chiqadi va ular orasidan haqiqiy muammoni ajratib
 * bo'lmaydi — natijada linter shovqinga aylanadi va e'tiborsiz
 * qoldiriladi.
 */

import js from '@eslint/js'
import globals from 'globals'
import tseslint from 'typescript-eslint'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'

export default tseslint.config(
  { ignores: ['dist', 'coverage', 'vite.config.js', 'vite.config.d.ts'] },
  {
    files: ['**/*.{ts,tsx}'],
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,

      // Hook bog'liqliklari — bu qoida haqiqiy xatolarni ushlaydi:
      // eskirgan qiymat ustida ishlaydigan effekt eng chalkash
      // turdagi nosozlik, chunki u faqat ba'zan yuz beradi.
      'react-hooks/exhaustive-deps': 'warn',

      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],

      // Ishlatilmagan o'zgaruvchi — ko'pincha yarim qolgan tahrir
      // belgisi. `_` bilan boshlanadiganlar ataylab qoldirilgan.
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],

      // `any` — tip tizimini o'chirish tugmasi. Ogohlantirish, xato
      // emas: mavjud kodda bir nechtasi bor va ularni bir vaqtda
      // tozalash bu vazifaning doirasidan tashqarida.
      '@typescript-eslint/no-explicit-any': 'warn',
    },
  },
)
