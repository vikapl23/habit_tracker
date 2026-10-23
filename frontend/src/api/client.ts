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

const ACCESS_TOKEN_KEY = 'habit_tracker_access_token';
const REFRESH_TOKEN_KEY = 'habit_tracker_refresh_token';

export const getAccessToken = (): string | null => {
  try {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  } catch {
    return null;
  }
};

export const getRefreshToken = (): string | null => {
  try {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  } catch {
    return null;
  }
};

export const setTokens = (tokens: { access?: string | null; refresh?: string | null }): void => {
  try {
    if (tokens.access) {
      localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access);
    }
    if (tokens.refresh) {
      localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh);
    }
  } catch {
    // Storage access may be restricted
  }
};

export const clearTokens = (): void => {
  try {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
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

  if (typeof window !== 'undefined' && !import.meta.env?.VITEST) {
    if (window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
  }
};

export const getApiBaseUrl = (): string => {
  const envUrl = import.meta.env?.VITE_API_URL;
  const base = envUrl && typeof envUrl === 'string' ? envUrl : 'http://localhost:8000/api/v1';
  return base.replace(/\/+$/, '');
};

// Singleton promise for token refresh to avoid duplicate concurrent calls
let refreshPromise: Promise<string | null> | null = null;

export const refreshTokens = async (): Promise<string | null> => {
  if (refreshPromise) {
    return refreshPromise;
  }

  const currentRefresh = getRefreshToken();
  if (!currentRefresh) {
    clearTokens();
    notifyAuthFailure();
    return null;
  }

  refreshPromise = (async () => {
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
        clearTokens();
        notifyAuthFailure();
        return null;
      }

      const data = await response.json();
      if (data.access) {
        setTokens({
          access: data.access,
          refresh: data.refresh || currentRefresh,
        });
        return data.access as string;
      }

      clearTokens();
      notifyAuthFailure();
      return null;
    } catch {
      clearTokens();
      notifyAuthFailure();
      return null;
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
      data = text ? { detail: text } : {};
    } catch {
      data = {};
    }
  }

  if (!response.ok) {
    const errorMsg =
      data?.detail ||
      (typeof data === 'object' && Object.keys(data).length > 0
        ? 'Validation error'
        : response.statusText || 'Request failed');
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
    const tokens = await apiClient.login(email, password);
    return {
      message: regRes.detail || 'User registered successfully.',
      tokens,
    };
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
};
