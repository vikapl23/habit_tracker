import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import React from 'react';
import { AuthProvider, useAuth } from '../AuthContext';
import { apiClient } from '../../api/client';

describe('AuthContext timezone auto-sync', () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem('habit_tracker_refresh_token', 'mock-refresh-token');
    vi.restoreAllMocks();
    vi.spyOn(apiClient, 'refreshTokens').mockResolvedValue('mock-access-token');
  });

  it('silently PATCHes profile when timezone_auto is True and browser timezone differs', async () => {
    const mockProfile = {
      id: 1,
      email: 'test@example.com',
      timezone: 'Europe/Kyiv',
      timezone_auto: true,
    };
    vi.spyOn(apiClient, 'getProfile').mockResolvedValue(mockProfile);
    const updateSpy = vi.spyOn(apiClient, 'updateProfile').mockResolvedValue({
      ...mockProfile,
      timezone: 'America/New_York',
    });

    vi.spyOn(Intl, 'DateTimeFormat').mockReturnValue({
      resolvedOptions: () => ({ timeZone: 'America/New_York' }),
    } as unknown as Intl.DateTimeFormat);

    const wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
      <AuthProvider>{children}</AuthProvider>
    );

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(updateSpy).toHaveBeenCalledWith({ timezone: 'America/New_York' });
    expect(result.current.user?.timezone).toBe('America/New_York');
  });

  it('normalizes legacy timezone (Europe/Kiev -> Europe/Kyiv) and does not PATCH if equal', async () => {
    const mockProfile = {
      id: 1,
      email: 'test@example.com',
      timezone: 'Europe/Kyiv',
      timezone_auto: true,
    };
    vi.spyOn(apiClient, 'getProfile').mockResolvedValue(mockProfile);
    const updateSpy = vi.spyOn(apiClient, 'updateProfile');

    vi.spyOn(Intl, 'DateTimeFormat').mockReturnValue({
      resolvedOptions: () => ({ timeZone: 'Europe/Kiev' }),
    } as unknown as Intl.DateTimeFormat);

    const wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
      <AuthProvider>{children}</AuthProvider>
    );

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(updateSpy).not.toHaveBeenCalled();
    expect(result.current.user?.timezone).toBe('Europe/Kyiv');
  });

  it('does nothing when browser timezone matches saved timezone', async () => {
    const mockProfile = {
      id: 1,
      email: 'test@example.com',
      timezone: 'America/New_York',
      timezone_auto: true,
    };
    vi.spyOn(apiClient, 'getProfile').mockResolvedValue(mockProfile);
    const updateSpy = vi.spyOn(apiClient, 'updateProfile');

    vi.spyOn(Intl, 'DateTimeFormat').mockReturnValue({
      resolvedOptions: () => ({ timeZone: 'America/New_York' }),
    } as unknown as Intl.DateTimeFormat);

    const wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
      <AuthProvider>{children}</AuthProvider>
    );

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(updateSpy).not.toHaveBeenCalled();
  });

  it('does NOT update timezone when timezone_auto is false (manual mode)', async () => {
    const mockProfile = {
      id: 1,
      email: 'test@example.com',
      timezone: 'Europe/Kyiv',
      timezone_auto: false,
    };
    vi.spyOn(apiClient, 'getProfile').mockResolvedValue(mockProfile);
    const updateSpy = vi.spyOn(apiClient, 'updateProfile');

    vi.spyOn(Intl, 'DateTimeFormat').mockReturnValue({
      resolvedOptions: () => ({ timeZone: 'America/New_York' }),
    } as unknown as Intl.DateTimeFormat);

    const wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
      <AuthProvider>{children}</AuthProvider>
    );

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(updateSpy).not.toHaveBeenCalled();
    expect(result.current.user?.timezone).toBe('Europe/Kyiv');
  });

  it('silently auto-syncs after login if timezone differs', async () => {
    vi.spyOn(apiClient, 'login').mockResolvedValue({ access: 'acc', refresh: 'ref' });
    const mockProfile = {
      id: 1,
      email: 'test@example.com',
      timezone: 'Europe/Kyiv',
      timezone_auto: true,
    };
    vi.spyOn(apiClient, 'getProfile').mockResolvedValue(mockProfile);
    const updateSpy = vi.spyOn(apiClient, 'updateProfile').mockResolvedValue({
      ...mockProfile,
      timezone: 'Asia/Tokyo',
    });

    vi.spyOn(Intl, 'DateTimeFormat').mockReturnValue({
      resolvedOptions: () => ({ timeZone: 'Asia/Tokyo' }),
    } as unknown as Intl.DateTimeFormat);

    // Initial mount without token
    localStorage.removeItem('habit_tracker_refresh_token');

    const wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
      <AuthProvider>{children}</AuthProvider>
    );

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await result.current.login('test@example.com', 'password123');

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith({ timezone: 'Asia/Tokyo' });
      expect(result.current.user?.timezone).toBe('Asia/Tokyo');
    });
  });
});
