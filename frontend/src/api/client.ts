export class ApiError extends Error {
  status: number;
  data: Record<string, any>;

  constructor(message: string, status: number, data: Record<string, any> = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

export interface Tokens {
  access: string;
  refresh: string;
}

export interface UserProfile {
  id: number;
  email: string;
  timezone: string;
}

// In-memory access token storage (C1: never persisted in localStorage)
let memoryAccessToken: string | null = null;

const REFRESH_TOKEN_KEY = 'habit_tracker_refresh_token';

export const getAccessToken = (): string | null => {
  return memoryAccessToken;
};

export const getRefreshToken = (): string | null => {
  try {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  } catch {
    return null;
  }
};

export const setTokens = (tokens: { access?: string | null; refresh?: string | null }): void => {
  if (tokens.access !== undefined) {
    memoryAccessToken = tokens.access;
  }
  try {
    if (tokens.refresh !== undefined) {
      if (tokens.refresh === null) {
        localStorage.removeItem(REFRESH_TOKEN_KEY);
      } else {
        localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh);
      }
    }
  } catch {
    // Storage access may be restricted
  }
};

export const clearTokens = (): void => {
  memoryAccessToken = null;
  try {
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  } catch {
    // Storage access may be restricted
  }
};

type AuthFailureListener = () => void;
const authFailureListeners = new Set<AuthFailureListener>();

export const onAuthFailure = (listener: AuthFailureListener): (() => void) => {
  authFailureListeners.add(listener);
  return () => authFailureListeners.delete(listener);
};

export const notifyAuthFailure = (): void => {
  authFailureListeners.forEach((listener) => {
    try {
      listener();
    } catch {
      // Ignore listener errors
    }
  });
};

export const getApiBaseUrl = (): string => {
  const envUrl = import.meta.env?.VITE_API_URL;
  const base = envUrl && typeof envUrl === 'string' ? envUrl : 'http://localhost:8000/api/v1';
  return base.replace(/\/+$/, '');
};

// Broadcast channel for multi-tab token synchronization (C2)
const TOKEN_BROADCAST_CHANNEL = 'habit_tracker_token_sync';
let tokenBroadcastChannel: BroadcastChannel | null = null;
try {
  if (typeof window !== 'undefined' && 'BroadcastChannel' in window) {
    tokenBroadcastChannel = new BroadcastChannel(TOKEN_BROADCAST_CHANNEL);
    tokenBroadcastChannel.onmessage = (event) => {
      if (event.data?.type === 'REFRESH_SUCCESS' && event.data?.access) {
        memoryAccessToken = event.data.access;
      } else if (event.data?.type === 'LOGOUT') {
        clearTokens();
        notifyAuthFailure();
      }
    };
  }
} catch {
  // BroadcastChannel unavailable
}

// Singleton promise for token refresh to avoid duplicate concurrent calls in the same tab
let refreshPromise: Promise<string | null> | null = null;

const executeTokenRefresh = async (): Promise<string | null> => {
  const currentRefresh = getRefreshToken();
  if (!currentRefresh) {
    clearTokens();
    notifyAuthFailure();
    return null;
  }

  try {
    const baseUrl = getApiBaseUrl();
    const response = await fetch(`${baseUrl}/auth/token/refresh/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh: currentRefresh }),
    });

    if (!response.ok) {
      // Check if another tab refreshed and updated the refresh token in localStorage in the meantime
      const latestRefresh = getRefreshToken();
      if (latestRefresh && latestRefresh !== currentRefresh) {
        // Retry refresh with the latest token
        const retryRes = await fetch(`${baseUrl}/auth/token/refresh/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ refresh: latestRefresh }),
        });
        if (retryRes.ok) {
          const retryData = await retryRes.json();
          if (retryData.access) {
            setTokens({
              access: retryData.access,
              refresh: retryData.refresh || latestRefresh,
            });
            tokenBroadcastChannel?.postMessage({
              type: 'REFRESH_SUCCESS',
              access: retryData.access,
            });
            return retryData.access as string;
          }
        }
      }

      // I1: Only clear tokens and force logout on 400/401 from refresh endpoint.
      // On 5xx, 429, or network error, keep tokens and throw retryable ApiError.
      if (response.status === 400 || response.status === 401) {
        clearTokens();
        tokenBroadcastChannel?.postMessage({ type: 'LOGOUT' });
        notifyAuthFailure();
        return null;
      }

      throw new ApiError('Token refresh failed temporarily', response.status, {});
    }

    const data = await response.json();
    if (data.access) {
      setTokens({
        access: data.access,
        refresh: data.refresh || currentRefresh,
      });
      tokenBroadcastChannel?.postMessage({
        type: 'REFRESH_SUCCESS',
        access: data.access,
      });
      return data.access as string;
    }

    clearTokens();
    tokenBroadcastChannel?.postMessage({ type: 'LOGOUT' });
    notifyAuthFailure();
    return null;
  } catch (err) {
    if (err instanceof ApiError && (err.status === 0 || err.status >= 500 || err.status === 429)) {
      throw err;
    }
    clearTokens();
    notifyAuthFailure();
    return null;
  }
};

export const refreshTokens = async (): Promise<string | null> => {
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    try {
      // Use Web Locks API if available to coordinate across tabs
      if (typeof navigator !== 'undefined' && navigator.locks?.request) {
        return await navigator.locks.request('habit-tracker-token-refresh', async () => {
          return await executeTokenRefresh();
        });
      }
      return await executeTokenRefresh();
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
};

export interface RequestOptions extends RequestInit {
  skipAuth?: boolean;
  _isRetry?: boolean;
}

export const apiRequest = async <T = any>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> => {
  const baseUrl = getApiBaseUrl();
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const url = `${baseUrl}${cleanEndpoint}`;

  const headers = new Headers(options.headers || {});
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const token = getAccessToken();
  if (token && !options.skipAuth && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (err: any) {
    throw new ApiError(err?.message || 'Network request failed', 0, {});
  }

  // Handle 401 Unauthorized
  if (response.status === 401) {
    const isAuthEndpoint =
      cleanEndpoint.includes('/auth/token/') ||
      cleanEndpoint.includes('/auth/register/');

    if (!options._isRetry && !isAuthEndpoint) {
      const newAccessToken = await refreshTokens();
      if (newAccessToken) {
        const retryHeaders = new Headers(options.headers || {});
        if (!retryHeaders.has('Content-Type') && !(options.body instanceof FormData)) {
          retryHeaders.set('Content-Type', 'application/json');
        }
        retryHeaders.set('Authorization', `Bearer ${newAccessToken}`);

        return apiRequest<T>(endpoint, {
          ...options,
          headers: retryHeaders,
          _isRetry: true,
        });
      }
    }
  }

  let data: any = null;
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    try {
      data = await response.json();
    } catch {
      data = null;
    }
  } else {
    try {
      const text = await response.text();
      // I9: Ignore non-JSON bodies (HTML 500/502/404) so raw HTML is not stored as detail
      data = text && !text.trim().startsWith('<') ? { detail: text } : {};
    } catch {
      data = {};
    }
  }

  if (!response.ok) {
    let errorMsg = 'Request failed';
    if (data && typeof data === 'object') {
      if (typeof data.detail === 'string' && !data.detail.trim().startsWith('<')) {
        errorMsg = data.detail;
      } else if (Object.keys(data).length > 0) {
        errorMsg = 'Validation error';
      }
    } else {
      data = {};
    }

    if (errorMsg === 'Request failed') {
      if (response.status >= 500) {
        errorMsg = 'Server error occurred. Please try again later.';
      } else if (response.status === 404) {
        errorMsg = 'Not found';
      } else if (response.status === 403) {
        errorMsg = 'Forbidden';
      } else if (response.status === 429) {
        errorMsg = 'Too many requests';
      } else if (response.statusText) {
        errorMsg = response.statusText;
      }
    }

    throw new ApiError(errorMsg, response.status, data || {});
  }

  return data as T;
};

// Convenience methods
export const apiClient = {
  get: <T = any>(endpoint: string, options?: RequestOptions) =>
    apiRequest<T>(endpoint, { ...options, method: 'GET' }),

  post: <T = any>(endpoint: string, body?: any, options?: RequestOptions) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: 'POST',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),

  put: <T = any>(endpoint: string, body?: any, options?: RequestOptions) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),

  patch: <T = any>(endpoint: string, body?: any, options?: RequestOptions) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }),

  delete: <T = any>(endpoint: string, options?: RequestOptions) =>
    apiRequest<T>(endpoint, { ...options, method: 'DELETE' }),

  // Auth specific methods
  login: async (email: string, password: string): Promise<Tokens> => {
    const tokens = await apiClient.post<Tokens>(
      '/auth/token/',
      { email, password },
      { skipAuth: true }
    );
    setTokens(tokens);
    return tokens;
  },

  register: async (
    email: string,
    password: string,
    timezone?: string
  ): Promise<{ message: string; tokens: Tokens }> => {
    const tz = timezone || Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
    const regRes = await apiClient.post<{ detail: string }>(
      '/auth/register/',
      { email, password, timezone: tz },
      { skipAuth: true }
    );

    // Auto-login after registration
    try {
      const tokens = await apiClient.login(email, password);
      return {
        message: regRes.detail || 'User registered successfully.',
        tokens,
      };
    } catch {
      // If login fails (e.g. rate limit / auth throttle), return null tokens so caller can redirect with notice
      return {
        message: regRes.detail || 'User registered successfully.',
        tokens: null as any,
      };
    }
  },

  logout: async (): Promise<void> => {
    const refresh = getRefreshToken();
    if (refresh) {
      try {
        await apiClient.post(
          '/auth/logout/',
          { refresh },
          { skipAuth: false }
        );
      } catch {
        // Even if server blacklisting fails, clear local tokens
      }
    }
    clearTokens();
    notifyAuthFailure();
  },

  getProfile: async (): Promise<UserProfile> => {
    return apiClient.get<UserProfile>('/auth/profile/');
  },

  updateProfile: async (data: Partial<UserProfile>): Promise<UserProfile> => {
    return apiClient.patch<UserProfile>('/auth/profile/', data);
  },

  refreshTokens,
};
