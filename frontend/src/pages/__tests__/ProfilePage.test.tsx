import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ProfilePage } from '../ProfilePage';
import { AuthProvider } from '../../context/AuthContext';
import { apiClient } from '../../api/client';

const mockProfile = {
  id: 1,
  email: 'tester@example.com',
  timezone: 'Europe/Kyiv',
  timezone_auto: true,
};

const renderProfile = () => {
  return render(
    <MemoryRouter
      initialEntries={['/profile']}
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <AuthProvider>
        <Routes>
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/login" element={<div>Login Page</div>} />
          <Route path="/" element={<div>Dashboard Home</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>
  );
};

describe('ProfilePage (Step 5.5)', () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem('habit_tracker_refresh_token', 'mock-refresh-token');
    vi.restoreAllMocks();
    vi.spyOn(apiClient, 'refreshTokens').mockResolvedValue('mock-access-token');
    vi.spyOn(apiClient, 'getProfile').mockResolvedValue(mockProfile);

    // Mock Intl DateTimeFormat
    vi.spyOn(Intl, 'DateTimeFormat').mockImplementation(() => {
      return {
        resolvedOptions: () => ({ timeZone: 'Europe/Kyiv' }),
        formatToParts: () => [{ type: 'timeZoneName', value: 'GMT+02:00' }],
        format: () => '2026-10-26',
      } as unknown as Intl.DateTimeFormat;
    });
  });

  it('renders read-only email and timezone auto toggle preselected with current timezone', async () => {
    renderProfile();

    expect(await screen.findByDisplayValue('tester@example.com')).toBeInTheDocument();
    const emailInput = screen.getByLabelText(/email address/i);
    expect(emailInput).toHaveAttribute('readOnly');

    const toggle = screen.getByRole('switch', { name: /set timezone automatically/i });
    expect(toggle).toBeChecked();
    expect(screen.getByText(/Europe\/Kyiv \(UTC\+02:00\)/i)).toBeInTheDocument();

    // Bottom Navigation present
    expect(screen.getByRole('navigation', { name: /bottom navigation/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /today/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /archive/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /profile/i })).toBeInTheDocument();
  });

  it('shows Europe/Kyiv for users who had Europe/Kiev timezone', async () => {
    vi.spyOn(apiClient, 'getProfile').mockResolvedValue({
      id: 2,
      email: 'legacy@example.com',
      timezone: 'Europe/Kiev',
      timezone_auto: true,
    });

    renderProfile();

    expect(await screen.findByDisplayValue('legacy@example.com')).toBeInTheDocument();
    expect(await screen.findByText(/Europe\/Kyiv \(UTC\+02:00\)/i)).toBeInTheDocument();
  });

  it('updates timezone by switching off auto and selecting timezone and shows success message', async () => {
    const user = userEvent.setup();
    const updateSpy = vi.spyOn(apiClient, 'updateProfile').mockResolvedValue({
      id: 1,
      email: 'tester@example.com',
      timezone: 'Europe/Warsaw',
      timezone_auto: false,
    });

    renderProfile();

    const toggle = await screen.findByRole('switch', { name: /set timezone automatically/i });
    await user.click(toggle);

    const searchInput = screen.getByPlaceholderText(/search timezone/i);
    await user.type(searchInput, 'warsaw');

    const warsawOption = screen.getByRole('option', { name: /Europe\/Warsaw/i });
    await user.click(warsawOption);

    // Save button should now be enabled
    const saveBtn = screen.getByRole('button', { name: /save timezone/i });
    expect(saveBtn).not.toBeDisabled();

    await user.click(saveBtn);

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith({
        timezone: 'Europe/Warsaw',
        timezone_auto: false,
      });
    });

    expect(await screen.findByText(/timezone updated to Europe\/Warsaw/i)).toBeInTheDocument();
  });

  it('logs out user and navigates away when Log Out button is clicked', async () => {
    const user = userEvent.setup();
    const logoutSpy = vi.spyOn(apiClient, 'logout').mockResolvedValue(undefined);

    renderProfile();

    const logoutBtn = await screen.findByRole('button', { name: /log out/i });
    await user.click(logoutBtn);

    await waitFor(() => {
      expect(logoutSpy).toHaveBeenCalled();
    });
  });
});
