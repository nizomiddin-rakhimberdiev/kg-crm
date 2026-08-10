import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
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
