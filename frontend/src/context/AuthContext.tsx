import React, { createContext, useEffect, useState, useCallback } from 'react';
import {
  apiClient,
  getAccessToken,
  getRefreshToken,
  onAuthFailure,
  UserProfile,
} from '../api/client';

export interface AuthContextType {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, timezone?: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshProfile: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchProfile = useCallback(async (): Promise<boolean> => {
    try {
      const profile = await apiClient.getProfile();
      setUser(profile);
      return true;
    } catch {
      setUser(null);
      return false;
    }
  }, []);

  useEffect(() => {
    let isMounted = true;

    const initAuth = async () => {
      const token = getAccessToken();
      const refresh = getRefreshToken();

      if (token || refresh) {
        await fetchProfile();
      }
      if (isMounted) {
        setIsLoading(false);
      }
    };

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
  }, [fetchProfile]);

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
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export { useAuth } from './useAuth';

