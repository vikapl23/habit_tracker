import React, { createContext, useEffect, useState, useCallback } from 'react';
import {
  apiClient,
  getAccessToken,
  getRefreshToken,
  onAuthFailure,
  UserProfile,
  ApiError,
} from '../api/client';

export interface AuthContextType {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, timezone?: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshProfile: () => Promise<void>;
  updateProfile: (data: Partial<UserProfile>) => Promise<UserProfile>;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [initError, setInitError] = useState<string | null>(null);

  const fetchProfile = useCallback(async (): Promise<boolean> => {
    try {
      const profile = await apiClient.getProfile();
      setUser(profile);
      return true;
    } catch (err) {
      setUser(null);
      throw err;
    }
  }, []);

  const initAuth = useCallback(async () => {
    setIsLoading(true);
    setInitError(null);
    const refresh = getRefreshToken();
    const access = getAccessToken();

    try {
      if (access) {
        await fetchProfile();
      } else if (refresh) {
        // Silently refresh to get a fresh in-memory access token on page reload
        await apiClient.refreshTokens();
        await fetchProfile();
      }
    } catch (err: any) {
      if (err instanceof ApiError && (err.status === 0 || err.status >= 500)) {
        setInitError('Unable to reach server. Please check your network connection.');
      } else {
        setUser(null);
      }
    } finally {
      setIsLoading(false);
    }
  }, [fetchProfile]);

  useEffect(() => {
    let isMounted = true;

    initAuth();

    // Listen for 401 unrecoverable failures
    const unsubscribe = onAuthFailure(() => {
      if (isMounted) {
        setUser(null);
      }
    });

    return () => {
      isMounted = false;
      unsubscribe();
    };
  }, [initAuth]);

  if (initError) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-4">
        <div className="w-full max-w-[400px] bg-white rounded-2xl shadow-sm border border-slate-200 p-6 text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-amber-50 text-amber-600 flex items-center justify-center mx-auto text-xl font-bold">
            ⚠️
          </div>
          <div className="space-y-1">
            <h2 className="text-base font-bold text-slate-900">Can't reach server</h2>
            <p className="text-xs text-slate-500">{initError}</p>
          </div>
          <button
            type="button"
            onClick={initAuth}
            className="min-h-[44px] inline-flex items-center justify-center px-5 py-2.5 rounded-xl bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 active:bg-blue-800 transition"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  const login = async (email: string, password: string) => {
    await apiClient.login(email, password);
    await fetchProfile();
  };

  const register = async (email: string, password: string, timezone?: string) => {
    await apiClient.register(email, password, timezone);
    await fetchProfile();
  };

  const logout = async () => {
    try {
      await apiClient.logout();
    } finally {
      setUser(null);
    }
  };

  const refreshProfile = async () => {
    await fetchProfile();
  };

  const updateProfile = async (data: Partial<UserProfile>): Promise<UserProfile> => {
    const updated = await apiClient.updateProfile(data);
    setUser(updated);
    return updated;
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
        refreshProfile,
        updateProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export { useAuth } from './useAuth';

