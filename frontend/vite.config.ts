/// <reference types="vitest" />
import { defineConfig, loadEnv, Plugin } from 'vite';
import react from '@vitejs/plugin-react';

function cspPlugin(apiUrl: string): Plugin {
  return {
    name: 'html-transform-csp',
    transformIndexHtml(html) {
      // Allow self and the API URL (plus localhost in dev/fallback)
      const connectSources = ["'self'"];
      if (apiUrl) {
        try {
          const origin = new URL(apiUrl).origin;
          if (!connectSources.includes(origin)) {
            connectSources.push(origin);
          }
        } catch {
          connectSources.push(apiUrl);
        }
      }
      if (!connectSources.includes('http://localhost:8000')) {
        connectSources.push('http://localhost:8000');
      }

      const csp = [
        "default-src 'self'",
        `connect-src ${connectSources.join(' ')}`,
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data:",
        "font-src 'self' data:",
        "object-src 'none'",
        "base-uri 'none'",
        "frame-ancestors 'none'",
      ].join('; ');

      const metaCsp = `<meta http-equiv="Content-Security-Policy" content="${csp}" />`;
      return html.replace('<head>', `<head>\n    ${metaCsp}`);
    },
  };
}

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiUrl = env.VITE_API_URL || '';

  return {
    plugins: [react(), cspPlugin(apiUrl)],
    server: {
      port: 5173,
      host: true,
    },
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: './src/test/setup.ts',
      css: false,
    },
  };
});
