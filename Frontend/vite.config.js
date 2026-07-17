import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const backend =
    (env.VITE_BACKEND_PROXY || 'http://127.0.0.1:8001').replace(/\/$/, '');

  return {
    server: {
      port: 5173,
      open: false,
      proxy: {
        '/api': {
          target: backend,
          changeOrigin: true,
        },
      },
    },
    preview: {
      port: 4173,
      proxy: {
        '/api': {
          target: backend,
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: true,
      assetsDir: 'assets',
    },
  };
});
