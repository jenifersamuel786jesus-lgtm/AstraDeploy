import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const projectRoot = dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  root: resolve(projectRoot, 'frontend'),
  plugins: [react(), tailwindcss()],
  build: {
    outDir: resolve(projectRoot, 'backend/app/static'),
    emptyOutDir: true,
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined;
          if (id.includes('/recharts/') || id.includes('/victory-vendor/')) return 'charts';
          if (id.includes('/react/') || id.includes('/react-dom/') || id.includes('/scheduler/')) return 'framework';
          return 'vendor';
        },
      },
    },
  },
  server: {
    host: '0.0.0.0', port: 5173, strictPort: true,
    proxy: { '/api': 'http://127.0.0.1:8000', '/manus-routes.json': 'http://127.0.0.1:8000' },
  },
});
