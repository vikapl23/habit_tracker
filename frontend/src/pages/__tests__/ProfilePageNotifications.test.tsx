import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ProfilePage } from '../ProfilePage';
import { AuthProvider } from '../../context/AuthContext';
import { apiClient, ApiError } from '../../api/client';

const mockProfile = {
  id: 1,
  email: 'tester@example.com',
  timezone: 'Europe/Kyiv',
  timezone_auto: true,
  notifications_enabled: true,
  weekly_summary_enabled: false,
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

describe('ProfilePage Notifications Section', () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem('habit_tracker_refresh_token', 'mock-refresh-token');
    vi.restoreAllMocks();
    vi.spyOn(apiClient, 'refreshTokens').mockResolvedValue('mock-access-token');
    vi.spyOn(apiClient, 'getProfile').mockResolvedValue({ ...mockProfile });

    vi.spyOn(Intl, 'DateTimeFormat').mockImplementation(() => {
      return {
        resolvedOptions: () => ({ timeZone: 'Europe/Kyiv' }),
        formatToParts: () => [{ type: 'timeZoneName', value: 'GMT+02:00' }],
        format: () => '2026-10-26',
      } as unknown as Intl.DateTimeFormat;
    });
  });

  it('renders notifications section with master switch "Email notifications" and weekly summary toggle', async () => {
    renderProfile();

    expect(await screen.findByDisplayValue('tester@example.com')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /notifications/i })).toBeInTheDocument();

    const masterSwitch = screen.getByRole('switch', { name: /email notifications/i });
    expect(masterSwitch).toBeInTheDocument();
    expect(masterSwitch).toBeChecked();

    const weeklyToggle = screen.getByRole('switch', { name: /weekly summary/i });
    expect(weeklyToggle).toBeInTheDocument();
    expect(weeklyToggle).not.toBeChecked();

    const saveBtn = screen.getByRole('button', { name: /save notifications/i });
    expect(saveBtn).toBeDisabled();
  });

  it('populates initial active settings from profile', async () => {
    vi.spyOn(apiClient, 'getProfile').mockResolvedValue({
      id: 2,
      email: 'custom@example.com',
      timezone: 'Europe/Kyiv',
      timezone_auto: true,
      notifications_enabled: false,
      weekly_summary_enabled: true,
    });

    renderProfile();

    expect(await screen.findByDisplayValue('custom@example.com')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /notifications/i })).toBeInTheDocument();

    const masterSwitch = screen.getByRole('switch', { name: /email notifications/i });
    expect(masterSwitch).not.toBeChecked();

    const weeklyToggle = screen.getByRole('switch', { name: /weekly summary/i });
    expect(weeklyToggle).toBeChecked();
  });

  it('updates master switch "Email notifications" and saves via PATCH /auth/profile/', async () => {
    const user = userEvent.setup();
    const updateSpy = vi.spyOn(apiClient, 'updateProfile').mockResolvedValue({
      ...mockProfile,
      notifications_enabled: false,
    });

    renderProfile();

    const masterSwitch = await screen.findByRole('switch', { name: /email notifications/i });
    expect(masterSwitch).toBeChecked();

    await user.click(masterSwitch);
    expect(masterSwitch).not.toBeChecked();

    const saveBtn = screen.getByRole('button', { name: /save notifications/i });
    expect(saveBtn).not.toBeDisabled();

    await user.click(saveBtn);

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith({
        notifications_enabled: false,
        weekly_summary_enabled: false,
      });
    });

    expect(await screen.findByText(/notification preferences saved successfully!/i)).toBeInTheDocument();
  });

  it('updates weekly summary toggle and saves via PATCH /auth/profile/', async () => {
    const user = userEvent.setup();
    const updateSpy = vi.spyOn(apiClient, 'updateProfile').mockResolvedValue({
      ...mockProfile,
      weekly_summary_enabled: true,
    });

    renderProfile();

    const weeklyToggle = await screen.findByRole('switch', { name: /weekly summary/i });
    expect(weeklyToggle).not.toBeChecked();

    await user.click(weeklyToggle);
    expect(weeklyToggle).toBeChecked();

    const saveBtn = screen.getByRole('button', { name: /save notifications/i });
    expect(saveBtn).not.toBeDisabled();

    await user.click(saveBtn);

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith({
        notifications_enabled: true,
        weekly_summary_enabled: true,
      });
    });

    expect(await screen.findByText(/notification preferences saved successfully!/i)).toBeInTheDocument();
  });

  it('displays error message if updateProfile fails', async () => {
    const user = userEvent.setup();
    vi.spyOn(apiClient, 'updateProfile').mockRejectedValue(
      new ApiError('Failed to update', 400, { detail: 'Network error or invalid preference payload.' })
    );

    renderProfile();

    const weeklyToggle = await screen.findByRole('switch', { name: /weekly summary/i });
    await user.click(weeklyToggle);

    const saveBtn = screen.getByRole('button', { name: /save notifications/i });
    await user.click(saveBtn);

    expect(await screen.findByText(/network error or invalid preference payload\./i)).toBeInTheDocument();
  });
});
