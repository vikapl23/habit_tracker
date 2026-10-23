import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { apiRequest, setTokens, getRefreshToken, ApiError } from '../client';

describe('Group 2 - Auth Flow and Error Handling Tests', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  // I1: Refresh failure on 5xx or network does NOT wipe session / refresh token
  it('I1: keeps refresh token when refresh endpoint returns 500 or 502 (retryable error)', async () => {
    setTokens({ access: 'stale-access', refresh: 'valid-refresh' });

    const mockFetch = vi.fn().mockImplementation(async (url: string) => {
      if (url.includes('/auth/token/refresh/')) {
        return {
          ok: false,
          status: 502,
          headers: new Headers({ 'content-type': 'text/html' }),
          text: async () => 'Bad Gateway',
        };
      }
      return {
        ok: false,
        status: 401,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ detail: 'Token expired' }),
      };
    });
    globalThis.fetch = mockFetch;

    await expect(apiRequest('/protected/')).rejects.toThrow();
    // Must keep refresh token on server error / 5xx!
    expect(getRefreshToken()).toBe('valid-refresh');
  });

  // I8: Guard against non-object or null json response
  it('I8: does not throw TypeError on null or empty JSON response body', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => null,
      text: async () => '',
    });
    globalThis.fetch = mockFetch;

    try {
      await apiRequest('/test-null-body/', { skipAuth: true });
      expect.fail('Should throw ApiError');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      expect((err as ApiError).status).toBe(400);
    }
  });

  // I9: Sanitizes HTML error bodies into friendly messages instead of raw HTML
  it('I9: does not leak raw HTML into ApiError message or detail', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      headers: new Headers({ 'content-type': 'text/html' }),
      text: async () => '<html><body><h1>500 Internal Server Error</h1></body></html>',
    });
    globalThis.fetch = mockFetch;

    try {
      await apiRequest('/test-html-error/', { skipAuth: true });
      expect.fail('Should throw ApiError');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      expect((err as ApiError).message).not.toContain('<html>');
      expect((err as ApiError).message).toMatch(/server error/i);
    }
  });
});
