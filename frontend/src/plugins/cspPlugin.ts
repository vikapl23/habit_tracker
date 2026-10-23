import { Plugin } from 'vite';

export function cspPlugin(apiUrl: string): Plugin {
  return {
    name: 'html-transform-csp',
    apply: 'build',
    transformIndexHtml(html: string) {
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

      const csp = [
        "default-src 'self'",
        `connect-src ${connectSources.join(' ')}`,
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data:",
        "font-src 'self' data:",
        "object-src 'none'",
        "base-uri 'none'",
      ].join('; ');

      const metaCsp = `<meta http-equiv="Content-Security-Policy" content="${csp}" />`;
      return html.replace('<head>', `<head>\n    ${metaCsp}`);
    },
  };
}
