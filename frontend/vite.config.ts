import { defineConfig } from 'vitest/config';
import { fileURLToPath, URL } from 'node:url';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    proxy: {
      '/api/v1/topologies/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
      // Live pcap streams can sit idle for a long time: no proxy timeout.
      '^/api/v1/captures/[^/]+/pcap': {
        target: 'http://localhost:8000',
      },
      '/api': {
        target: 'http://localhost:8000',
        timeout: 300000,
        proxyTimeout: 300000,
      },
    },
  },
  build: {
    chunkSizeWarningLimit: 700,
    rollupOptions: {
      output: {
        manualChunks: {
          react: ['react', 'react-dom', 'react-router'],
          flow: ['@xyflow/react', '@dagrejs/dagre'],
          ui: ['radix-ui', 'cmdk', 'sonner', 'lucide-react', 'react-resizable-panels'],
          forms: ['react-hook-form', 'zod', '@hookform/resolvers'],
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
});
