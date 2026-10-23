import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { LoginPage } from '../LoginPage';
import { RegisterPage } from '../RegisterPage';
import { AuthProvider } from '../../context/AuthContext';
import { apiClient, ApiError } from '../../api/client';

describe('Auth Forms (Login and Register)', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  describe('LoginPage', () => {
    it('renders login form elements with 375px mobile-friendly design', () => {
      render(
        <MemoryRouter>
          <AuthProvider>
            <LoginPage />
          </AuthProvider>
        </MemoryRouter>
      );

      expect(screen.getByRole('heading', { name: /sign in to your account/i })).toBeInTheDocument();
      expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /sign up/i })).toBeInTheDocument();
    });

    it('shows client-side validation errors when submitting empty fields', async () => {
      const user = userEvent.setup();

      render(
        <MemoryRouter>
          <AuthProvider>
            <LoginPage />
          </AuthProvider>
        </MemoryRouter>
      );

      await user.click(screen.getByRole('button', { name: /sign in/i }));

      expect(await screen.findByText(/email is required/i)).toBeInTheDocument();
      expect(await screen.findByText(/password is required/i)).toBeInTheDocument();
    });

    it('submits credentials and navigates on success', async () => {
      const user = userEvent.setup();
      const loginSpy = vi.spyOn(apiClient, 'login').mockResolvedValue({
        access: 'mock-access',
        refresh: 'mock-refresh',
      });
      vi.spyOn(apiClient, 'getProfile').mockResolvedValue({
        id: 1,
        email: 'test@example.com',
        timezone: 'Europe/Kyiv',
      });

      render(
        <MemoryRouter initialEntries={['/login']}>
          <AuthProvider>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/" element={<div>Dashboard Screen</div>} />
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      );

      await user.type(screen.getByLabelText(/email address/i), 'test@example.com');
      await user.type(screen.getByLabelText(/^password$/i), 'SecretPass123!');
      await user.click(screen.getByRole('button', { name: /sign in/i }));

      await waitFor(() => {
        expect(loginSpy).toHaveBeenCalledWith('test@example.com', 'SecretPass123!');
      });

      expect(await screen.findByText(/dashboard screen/i)).toBeInTheDocument();
    });

    it('displays backend detail validation error in alert banner', async () => {
      const user = userEvent.setup();
      vi.spyOn(apiClient, 'login').mockRejectedValue(
        new ApiError('Unauthorized', 401, {
          detail: 'No active account found with the given credentials',
        })
      );

      render(
        <MemoryRouter>
          <AuthProvider>
            <LoginPage />
          </AuthProvider>
        </MemoryRouter>
      );

      await user.type(screen.getByLabelText(/email address/i), 'wrong@example.com');
      await user.type(screen.getByLabelText(/^password$/i), 'wrongpass');
      await user.click(screen.getByRole('button', { name: /sign in/i }));

      expect(
        await screen.findByText(/no active account found with the given credentials/i)
      ).toBeInTheDocument();
    });
  });

  describe('RegisterPage', () => {
    it('renders registration form elements', () => {
      render(
        <MemoryRouter>
          <AuthProvider>
            <RegisterPage />
          </AuthProvider>
        </MemoryRouter>
      );

      expect(screen.getByRole('heading', { name: /create your account/i })).toBeInTheDocument();
      expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /sign in/i })).toBeInTheDocument();
    });

    it('validates password mismatch on client-side', async () => {
      const user = userEvent.setup();

      render(
        <MemoryRouter>
          <AuthProvider>
            <RegisterPage />
          </AuthProvider>
        </MemoryRouter>
      );

      await user.type(screen.getByLabelText(/email address/i), 'newuser@example.com');
      await user.type(screen.getByLabelText(/^password$/i), 'SuperSecret123!');
      await user.type(screen.getByLabelText(/confirm password/i), 'DifferentPassword!');
      await user.click(screen.getByRole('button', { name: /create account/i }));

      expect(await screen.findByText(/passwords do not match/i)).toBeInTheDocument();
    });

    it('shows backend validation errors under fields', async () => {
      const user = userEvent.setup();
      vi.spyOn(apiClient, 'register').mockRejectedValue(
        new ApiError('Bad Request', 400, {
          email: ['Enter a valid email address.'],
          password: ['This password is too short.'],
        })
      );

      render(
        <MemoryRouter>
          <AuthProvider>
            <RegisterPage />
          </AuthProvider>
        </MemoryRouter>
      );

      await user.type(screen.getByLabelText(/email address/i), 'invalid-email');
      await user.type(screen.getByLabelText(/^password$/i), 'short123');
      await user.type(screen.getByLabelText(/confirm password/i), 'short123');
      await user.click(screen.getByRole('button', { name: /create account/i }));

      expect(await screen.findByText(/enter a valid email address/i)).toBeInTheDocument();
      expect(await screen.findByText(/this password is too short/i)).toBeInTheDocument();
    });

    it('submits registration with timezone and navigates to dashboard on success', async () => {
      const user = userEvent.setup();
      const registerSpy = vi.spyOn(apiClient, 'register').mockResolvedValue({
        message: 'User registered successfully.',
        tokens: { access: 'tok-access', refresh: 'tok-refresh' },
      });
      vi.spyOn(apiClient, 'getProfile').mockResolvedValue({
        id: 2,
        email: 'registered@example.com',
        timezone: 'UTC',
      });

      render(
        <MemoryRouter initialEntries={['/register']}>
          <AuthProvider>
            <Routes>
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/" element={<div>Dashboard Screen</div>} />
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      );

      await user.type(screen.getByLabelText(/email address/i), 'registered@example.com');
      await user.type(screen.getByLabelText(/^password$/i), 'StrongPass123!');
      await user.type(screen.getByLabelText(/confirm password/i), 'StrongPass123!');
      await user.click(screen.getByRole('button', { name: /create account/i }));

      await waitFor(() => {
        expect(registerSpy).toHaveBeenCalled();
      });

      expect(await screen.findByText(/dashboard screen/i)).toBeInTheDocument();
    });
  });
});
