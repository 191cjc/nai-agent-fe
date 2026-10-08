import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import basicSsl from '@vitejs/plugin-basic-ssl'

const basePath = process.env.NAI_WEB_BASE_PATH || '/'
if (!/^\/(?:[A-Za-z0-9_-]+\/)*$/.test(basePath)) {
  throw new Error('NAI_WEB_BASE_PATH must be a same-origin path ending in /')
}

export default defineConfig({
  base: basePath,
  plugins: [react(), basicSsl()],
  server: {
    host: 'localhost',
    port: 5173,
    strictPort: true,
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})
