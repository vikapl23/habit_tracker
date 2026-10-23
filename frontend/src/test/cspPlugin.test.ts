import { describe, it, expect } from 'vitest';
import { cspPlugin } from '../plugins/cspPlugin';

describe('cspPlugin', () => {
  const sampleHtml = '<!doctype html><html><head><title>Test</title></head><body><div id="root"></div></body></html>';

  it('is configured with apply: "build" so dev mode is not broken', () => {
    const plugin = cspPlugin('');
    expect(plugin.apply).toBe('build');
  });

  it('does not include frame-ancestors in the meta tag because browsers ignore it in <meta>', () => {
    const plugin = cspPlugin('https://api.example.com/api/v1');
    const transform = plugin.transformIndexHtml as (html: string) => string;
    const result = transform(sampleHtml);

    expect(result).not.toContain('frame-ancestors');
    expect(result).toContain('<meta http-equiv="Content-Security-Policy"');
  });

  it('in production build, connect-src only contains \'self\' and origin of VITE_API_URL, not localhost:8000', () => {
    const plugin = cspPlugin('https://habit-tracker-api.onrender.com/api/v1');
    const transform = plugin.transformIndexHtml as (html: string) => string;
    const result = transform(sampleHtml);

    expect(result).toContain("connect-src 'self' https://habit-tracker-api.onrender.com");
    expect(result).not.toContain('localhost:8000');
  });
});
