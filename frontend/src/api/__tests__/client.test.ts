import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  apiClient,
  apiRequest,
  getAccessToken,
  getRefreshToken,
  setTokens,
  refreshTokens,
  onAuthFailure,
  ApiError,
} from '../client';

describe('API Client and Auth / Token Refresh logic', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('adds Authorization: Bearer <access> header when access token exists', async () => {
    setTokens({ access: 'valid-access-token', refresh: 'valid-refresh-token' });

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ message: 'success' }),
    });
    globalThis.fetch = mockFetch;

    const res = await apiRequest<{ message: string }>('/test-endpoint/');

    expect(res).toEqual({ message: 'success' });
    expect(mockFetch).toHaveBeenCalledTimes(1);
    const headers = mockFetch.mock.calls[0][1].headers;
    expect(headers.get('Authorization')).toBe('Bearer valid-access-token');
  });

  it('omits Authorization header when skipAuth is true', async () => {
    setTokens({ access: 'valid-access-token', refresh: 'valid-refresh-token' });

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ message: 'public' }),
    });
    globalThis.fetch = mockFetch;

    await apiRequest('/public-endpoint/', { skipAuth: true });

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const headers = mockFetch.mock.calls[0][1].headers;
    expect(headers.get('Authorization')).toBeNull();
  });

  it('on 401 calls /auth/token/refresh/ once, saves BOTH new access and refresh tokens, and retries request', async () => {
    setTokens({ access: 'expired-access-token', refresh: 'old-refresh-token' });

    let callCount = 0;
    const recordedCalls: Array<{ url: string; authHeader: string | null; body: any }> = [];

    const mockFetch = vi.fn().mockImplementation(async (url: string, init: any) => {
      const authHeader = init?.headers?.get ? init.headers.get('Authorization') : init?.headers?.['Authorization'] || null;
      let parsedBody = null;
      if (init?.body) {
        try {
          parsedBody = JSON.parse(init.body);
        } catch {
          parsedBody = init.body;
        }
      }
      recordedCalls.push({ url, authHeader, body: parsedBody });

      if (url.includes('/test-resource/')) {
        callCount++;
        if (callCount === 1) {
          // First attempt fails with 401
          return {
            ok: false,
            status: 401,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: async () => ({ detail: 'Given token not valid for any token type' }),
          };
        }
        // Second attempt (retry) succeeds with new token
        return {
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({ data: 'protected-data' }),
        };
      }

      if (url.includes('/auth/token/refresh/')) {
        return {
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            access: 'new-access-token-123',
            refresh: 'new-refresh-token-456',
          }),
        };
      }

      throw new Error(`Unexpected URL: ${url}`);
    });
    globalThis.fetch = mockFetch;

    const result = await apiRequest<{ data: string }>('/test-resource/');

    expect(result).toEqual({ data: 'protected-data' });
    expect(callCount).toBe(2);

    // Assert fetch call arguments outside mockFetch callback
    const refreshCall = recordedCalls.find((c) => c.url.includes('/auth/token/refresh/'));
    expect(refreshCall?.body).toEqual({ refresh: 'old-refresh-token' });

    const retryCall = recordedCalls.filter((c) => c.url.includes('/test-resource/'))[1];
    expect(retryCall?.authHeader).toBe('Bearer new-access-token-123');

    // Both new tokens must be stored in localStorage
    expect(getAccessToken()).toBe('new-access-token-123');
    expect(getRefreshToken()).toBe('new-refresh-token-456');
  });

  it('handles several parallel requests getting 401 at the same time with only ONE refresh call', async () => {
    setTokens({ access: 'expired-access-token', refresh: 'initial-refresh-token' });

    let refreshCallCount = 0;
    let resource1Calls = 0;
    let resource2Calls = 0;
    let resource3Calls = 0;
    const recordedRetryAuths: string[] = [];

    const mockFetch = vi.fn().mockImplementation(async (url: string, init: any) => {
      if (url.includes('/auth/token/refresh/')) {
        refreshCallCount++;
        // Simulate network latency
        await new Promise((resolve) => setTimeout(resolve, 20));
        return {
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            access: 'refreshed-access-token',
            refresh: 'refreshed-refresh-token',
          }),
        };
      }

      if (url.includes('/resource-1/')) {
        resource1Calls++;
        if (resource1Calls === 1) {
          return {
            ok: false,
            status: 401,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: async () => ({ detail: 'Token expired' }),
          };
        }
        const auth = init?.headers?.get ? init.headers.get('Authorization') : init?.headers?.['Authorization'];
        recordedRetryAuths.push(auth);
        return {
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({ id: 1, name: 'Res1' }),
        };
      }

      if (url.includes('/resource-2/')) {
        resource2Calls++;
        if (resource2Calls === 1) {
          return {
            ok: false,
            status: 401,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: async () => ({ detail: 'Token expired' }),
          };
        }
        const auth = init?.headers?.get ? init.headers.get('Authorization') : init?.headers?.['Authorization'];
        recordedRetryAuths.push(auth);
        return {
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({ id: 2, name: 'Res2' }),
        };
      }

      if (url.includes('/resource-3/')) {
        resource3Calls++;
        if (resource3Calls === 1) {
          return {
            ok: false,
            status: 401,
            headers: new Headers({ 'content-type': 'application/json' }),
            json: async () => ({ detail: 'Token expired' }),
          };
        }
        const auth = init?.headers?.get ? init.headers.get('Authorization') : init?.headers?.['Authorization'];
        recordedRetryAuths.push(auth);
        return {
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({ id: 3, name: 'Res3' }),
        };
      }

      throw new Error(`Unexpected URL: ${url}`);
    });
    globalThis.fetch = mockFetch;

    // Fire 3 requests in parallel
    const [res1, res2, res3] = await Promise.all([
      apiRequest<{ id: number; name: string }>('/resource-1/'),
      apiRequest<{ id: number; name: string }>('/resource-2/'),
      apiRequest<{ id: number; name: string }>('/resource-3/'),
    ]);

    expect(res1).toEqual({ id: 1, name: 'Res1' });
    expect(res2).toEqual({ id: 2, name: 'Res2' });
    expect(res3).toEqual({ id: 3, name: 'Res3' });

    // Assert that retry requests used the new refreshed access token outside mockFetch
    expect(recordedRetryAuths).toEqual([
      'Bearer refreshed-access-token',
      'Bearer refreshed-access-token',
      'Bearer refreshed-access-token',
    ]);

    // CRITICAL: Exactly ONE refresh call made despite 3 parallel 401s
    expect(refreshCallCount).toBe(1);
    expect(getAccessToken()).toBe('refreshed-access-token');
    expect(getRefreshToken()).toBe('refreshed-refresh-token');
  });

  it('if refresh fails, clears tokens, notifies failure callback, and throws error', async () => {
    setTokens({ access: 'bad-access', refresh: 'bad-refresh' });

    const authFailureSpy = vi.fn();
    const unsub = onAuthFailure(authFailureSpy);

    const mockFetch = vi.fn().mockImplementation(async (url: string) => {
      if (url.includes('/test-fail/')) {
        return {
          ok: false,
          status: 401,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({ detail: 'Invalid token' }),
        };
      }

      if (url.includes('/auth/token/refresh/')) {
        return {
          ok: false,
          status: 401,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({ detail: 'Refresh token invalid or blacklisted' }),
        };
      }

      throw new Error(`Unexpected URL: ${url}`);
    });
    globalThis.fetch = mockFetch;

    await expect(apiRequest('/test-fail/')).rejects.toThrow();

    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
    expect(authFailureSpy).toHaveBeenCalled();

    unsub();
  });

  it('logout calls /auth/logout/ with refresh token and clears tokens', async () => {
    setTokens({ access: 'my-access-token', refresh: 'my-refresh-token' });

    let logoutPayload: any = null;
    const mockFetch = vi.fn().mockImplementation(async (url: string, init: any) => {
      if (url.includes('/auth/logout/')) {
        logoutPayload = JSON.parse(init.body);
        return {
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({}),
        };
      }
      throw new Error(`Unexpected URL: ${url}`);
    });
    globalThis.fetch = mockFetch;

    await apiClient.logout();

    expect(logoutPayload).toEqual({ refresh: 'my-refresh-token' });
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });

  it('keeps access token only in memory (does not persist access token to localStorage)', () => {
    setTokens({ access: 'secret-in-memory-access', refresh: 'stored-refresh' });
    expect(getAccessToken()).toBe('secret-in-memory-access');
    expect(localStorage.getItem('habit_tracker_access_token')).toBeNull();
    expect(localStorage.getItem('habit_tracker_refresh_token')).toBe('stored-refresh');
    expect(getRefreshToken()).toBe('stored-refresh');
  });

  it('coordinates cross-tab refresh: if another tab already refreshed, uses newer refresh token without blacklisting 401', async () => {
    setTokens({ access: null, refresh: 'initial-refresh' });

    let _refreshCallCount = 0;
    const mockFetch = vi.fn().mockImplementation(async (url: string, init: any) => {
      if (url.includes('/auth/token/refresh/')) {
        _refreshCallCount++;
        const body = JSON.parse(init.body);
        return {
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            access: `access-for-${body.refresh}`,
            refresh: `rotated-after-${body.refresh}`,
          }),
        };
      }
      return {
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ ok: true }),
      };
    });
    globalThis.fetch = mockFetch;

    // Simulate Tab A refreshing first
    const token1 = await refreshTokens();
    expect(token1).toBe('access-for-initial-refresh');
    expect(getRefreshToken()).toBe('rotated-after-initial-refresh');

    // Simulate Tab B had started with 'initial-refresh' before lock,
    // but by the time it acquires the lock, localStorage already has 'rotated-after-initial-refresh'
    // It should refresh using the new token or notice storage changed
    const token2 = await refreshTokens();
    expect(token2).toBe('access-for-rotated-after-initial-refresh');
    expect(getRefreshToken()).toBe('rotated-after-rotated-after-initial-refresh');
  });

  it('register sends timezone, auto-logs in, and returns message and tokens', async () => {
    let registerBody: any = null;
    let loginBody: any = null;

    const mockFetch = vi.fn().mockImplementation(async (url: string, init: any) => {
      if (url.includes('/auth/register/')) {
        registerBody = JSON.parse(init.body);
        return {
          ok: true,
          status: 201,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({ detail: 'User registered successfully.' }),
        };
      }

      if (url.includes('/auth/token/')) {
        loginBody = JSON.parse(init.body);
        return {
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: async () => ({
            access: 'auto-login-access',
            refresh: 'auto-login-refresh',
          }),
        };
      }

      throw new Error(`Unexpected URL: ${url}`);
    });
    globalThis.fetch = mockFetch;

    const result = await apiClient.register('user@example.com', 'Pass1234!', 'America/New_York');

    expect(registerBody).toEqual({
      email: 'user@example.com',
      password: 'Pass1234!',
      timezone: 'America/New_York',
    });
    expect(loginBody).toEqual({
      email: 'user@example.com',
      password: 'Pass1234!',
    });
    expect(result.tokens).toEqual({
      access: 'auto-login-access',
      refresh: 'auto-login-refresh',
    });
    expect(getAccessToken()).toBe('auto-login-access');
    expect(getRefreshToken()).toBe('auto-login-refresh');
  });

  it('exposes backend validation errors via ApiError', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        email: ['Enter a valid email address.'],
        password: ['Password is too common.'],
      }),
    });
    globalThis.fetch = mockFetch;

    try {
      await apiRequest('/auth/register/', { method: 'POST', body: '{}' });
      expect.fail('Should have thrown an error');
    } catch (err: any) {
      expect(err).toBeInstanceOf(ApiError);
      expect(err.status).toBe(400);
      expect(err.data).toEqual({
        email: ['Enter a valid email address.'],
        password: ['Password is too common.'],
      });
    }
  });

  it('updateProfile calls PATCH /auth/profile/ with updated data', async () => {
    let patchUrl = '';
    let patchBody: any = null;
    let patchMethod = '';

    const mockFetch = vi.fn().mockImplementation(async (url: string, init: any) => {
      patchUrl = url;
      patchMethod = init.method;
      patchBody = JSON.parse(init.body);
      return {
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ id: 1, email: 'user@example.com', timezone: 'Europe/Kyiv' }),
      };
    });
    globalThis.fetch = mockFetch;

    const res = await apiClient.updateProfile({ timezone: 'Europe/Kyiv' });
    expect(patchUrl).toContain('/auth/profile/');
    expect(patchMethod).toBe('PATCH');
    expect(patchBody).toEqual({ timezone: 'Europe/Kyiv' });
    expect(res.timezone).toBe('Europe/Kyiv');
  });
});
