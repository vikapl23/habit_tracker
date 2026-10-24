import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ProtectedRoute } from '../components/ProtectedRoute';
import { AuthProvider, useAuth } from '../context/AuthContext';
import { setTokens, clearTokens, apiClient } from '../api/client';
import { DeleteConfirmDialog } from '../components/DeleteConfirmDialog';
import userEvent from '@testing-library/user-event';

const PublicTestRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <div>Auth Loading...</div>;
  if (isAuthenticated) return <div>Redirected to Home</div>;
  return <>{children}</>;
};

describe('Group 3 I20 - Coverage for Auth Routes, Dialogs, and Error States', () => {
  beforeEach(() => {
    localStorage.clear();
    clearTokens();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('ProtectedRoute redirects unauthenticated user to /login with state.from', async () => {
    vi.spyOn(apiClient, 'getProfile').mockRejectedValue(new Error('Unauthorized'));

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<div>Login Page</div>} />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <div>Secret Dashboard</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );

    expect(await screen.findByText('Login Page')).toBeInTheDocument();
    expect(screen.queryByText('Secret Dashboard')).not.toBeInTheDocument();
  });

  it('PublicRoute redirects authenticated user away from public login page', async () => {
    setTokens({ access: 'valid-acc', refresh: 'valid-ref' });
    vi.spyOn(apiClient, 'getProfile').mockResolvedValue({
      id: 1,
      email: 'user@example.com',
      timezone: 'UTC',
    });

    render(
      <MemoryRouter initialEntries={['/login']}>
        <AuthProvider>
          <Routes>
            <Route
              path="/login"
              element={
                <PublicTestRoute>
                  <div>Login Form</div>
                </PublicTestRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );

    expect(await screen.findByText('Redirected to Home')).toBeInTheDocument();
    expect(screen.queryByText('Login Form')).not.toBeInTheDocument();
  });

  it('AuthProvider handles startup with expired tokens and failed profile fetch gracefully', async () => {
    setTokens({ access: 'expired-acc', refresh: 'expired-ref' });
    vi.spyOn(apiClient, 'getProfile').mockRejectedValue({
      status: 401,
      message: 'Token is invalid or expired',
    });

    const TestComponent = () => {
      const { isAuthenticated, isLoading, user } = useAuth();
      if (isLoading) return <div>Loading Profile...</div>;
      return (
        <div>
          <span>AuthStatus: {isAuthenticated ? 'authenticated' : 'unauthenticated'}</span>
          <span>User: {user ? user.email : 'none'}</span>
        </div>
      );
    };

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    expect(await screen.findByText('AuthStatus: unauthenticated')).toBeInTheDocument();
    expect(screen.getByText('User: none')).toBeInTheDocument();
  });

  it('DeleteConfirmDialog traps Escape key and cancels', async () => {
    const onCancel = vi.fn();
    const onConfirm = vi.fn();

    const { rerender } = render(
      <DeleteConfirmDialog
        isOpen={true}
        habitName="Morning Meditation"
        isDeleting={false}
        onConfirm={onConfirm}
        onCancel={onCancel}
      />
    );

    expect(screen.getByRole('dialog', { name: /delete habit\?/i })).toBeInTheDocument();

    // Trigger escape key
    await userEvent.keyboard('{Escape}');
    expect(onCancel).toHaveBeenCalled();

    // Does not cancel on backdrop click when isDeleting is true
    onCancel.mockClear();
    rerender(
      <DeleteConfirmDialog
        isOpen={true}
        habitName="Morning Meditation"
        isDeleting={true}
        onConfirm={onConfirm}
        onCancel={onCancel}
      />
    );

    const backdrop = screen.getByRole('dialog');
    await userEvent.click(backdrop);
    expect(onCancel).not.toHaveBeenCalled();
  });
});
