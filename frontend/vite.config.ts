import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import process from 'node:process';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/github': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/mcp': {
        target: 'http://127.0.0.1:8766',
        changeOrigin: true,
        configure: (proxy) => {
          const token = process.env.GREENCODE_MCP_TOKEN;
          if (token) {
            proxy.on('proxyReq', (request) => {
              request.setHeader('Authorization', `Bearer ${token}`);
            });
          }
        },
      },
    },
  },
  build: {
    outDir: 'dist',
    target: 'esnext',
  },
});
