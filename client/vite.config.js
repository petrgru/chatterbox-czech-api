import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 4173,
    // Dev proxy: forward API routes to FastAPI
    proxy: {
      '/v1': {
        target: process.env.VITE_API_BASE || process.env.API_TARGET || 'http://api:8000',
        changeOrigin: true,
      },
      '/health': {
        target: process.env.VITE_API_BASE || process.env.API_TARGET || 'http://api:8000',
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: '0.0.0.0',
    port: 4173,
    allowedHosts: ['aivoice.sspu-opava.cz'],
  },
});
