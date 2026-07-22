import { defineConfig, loadEnv } from 'vite';
import { ensureBackendRunning } from './scripts/ensure-backend.mjs';

export default defineConfig(async ({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  // Auto-start local backend in dev so you never switch terminals manually.
  let backend = (env.VITE_BACKEND_PROXY || 'http://127.0.0.1:8000').replace(/\/$/, '');
  if (mode === 'development') {
    try {
      const port = await ensureBackendRunning();
      backend = `http://127.0.0.1:${port}`;
    } catch (err) {
      console.warn('[ushirika]', err?.message || err);
    }
  }

  return {
    server: {
      port: 5173,
      open: false,
      proxy: {
        '/api': {
          target: backend,
          changeOrigin: true,
          timeout: 120000,
        },
      },
    },
    preview: {
      port: 4173,
      proxy: {
        '/api': {
          target: backend,
          changeOrigin: true,
          timeout: 120000,
        },
      },
    },
    build: {
      outDir: 'dist',
      // Do not ship source maps in production (harder to reverse-engineer).
      sourcemap: mode === 'development',
      assetsDir: 'assets',
    },
  };
});
