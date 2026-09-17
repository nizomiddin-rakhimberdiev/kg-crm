import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  /*
   * Ilova qaysi yo'ldan boshlanadi.
   *
   * Sukut `/` — o'z domenida yashaydigan har qanday o'rnatma uchun
   * (SaaS ham, mijozning alohida serveri ham). Demo nusxasi esa
   * mavjud domenning bir qismida turadi (`radix-crm.uz/private`), va
   * o'shanda bu qiymat `/private/` bo'lishi SHART: aks holda Vite
   * `/assets/...` deb yozadi, brauzer esa uni SaaS saytining
   * ildizidan qidirib, bo'sh ekran ko'rsatardi.
   *
   * React Router ham xuddi shu qiymatni `import.meta.env.BASE_URL`
   * orqali o'qiydi (`lib/tenantAddress.ts`) — ikkalasi bitta manbadan.
   */
  base: process.env.VITE_BASE_PATH || '/',
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    // Port band bo'lsa Vite jimgina 5174/5175 ga o'tib ketmasin: backend CORS
    // faqat 5173 ni taniydi, va boshqa portdagi sahifa "serverga ulanib
    // bo'lmadi" deb ishdan chiqadi. Ochiq xato — jim buzilishdan yaxshi.
    strictPort: true,
    open: true,
  },
})
