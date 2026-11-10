import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// COOP/COEP unsafe-none prevents opener blocking with Google Identity Services popups.
// Any remaining "Cross-Origin-Opener-Policy policy would block window.postMessage" console
// warning originates inside Google's cross-origin GSI iframe and does not impact credential exchange.
export default defineConfig({
  plugins: [react()],
  server: {
    headers: {
      'Cross-Origin-Opener-Policy': 'unsafe-none',
      'Cross-Origin-Embedder-Policy': 'unsafe-none',
    },
  },
  preview: {
    headers: {
      'Cross-Origin-Opener-Policy': 'unsafe-none',
      'Cross-Origin-Embedder-Policy': 'unsafe-none',
    },
  },
})
