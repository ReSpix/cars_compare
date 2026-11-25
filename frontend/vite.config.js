import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// Бэкенд не настроен на CORS, поэтому все запросы фронтенда идут
// через прокси Vite и остаются в рамках одного origin.
const BACKEND = process.env.VITE_BACKEND_URL || 'http://localhost:8000'

const PROXY_ROUTES = [
  '/health',
  '/regions',
  '/auctions',
  '/rate-car',
  '/car_compare',
  '/budget-alternatives',
  '/log',
  '/docs',
  '/openapi.json',
]

const proxy = Object.fromEntries(
  PROXY_ROUTES.map((route) => [route, { target: BACKEND, changeOrigin: true }]),
)

const watch = process.env.VITE_USE_POLLING === 'true'
  ? { usePolling: true, interval: 500 }
  : undefined

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            { name: 'react', test: /[\\/]node_modules[\\/](react|react-dom|scheduler)[\\/]/ },
            { name: 'controls', test: /[\\/]node_modules[\\/](@headlessui|@floating-ui|@react-aria|@react-stately)[\\/]/ },
          ],
        },
      },
    },
  },
  server: { port: 5173, proxy, watch },
  preview: { port: 4173, proxy },
})
