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
  daily_reminder_enabled: false,
  daily_reminder_time: '20:00:00',
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

describe('ProfilePage Notifications Section (Phase 9 Part 2)', () => {
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

  it('renders notifications section with toggles for daily reminder and weekly summary and reminder time picker', async () => {
    renderProfile();

    expect(await screen.findByDisplayValue('tester@example.com')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /notifications/i })).toBeInTheDocument();

    const dailyToggle = screen.getByRole('switch', { name: /daily reminder/i });
    expect(dailyToggle).toBeInTheDocument();
    expect(dailyToggle).not.toBeChecked();

    const timeInput = screen.getByLabelText(/reminder time/i);
    expect(timeInput).toBeInTheDocument();
    expect(timeInput).toHaveValue('20:00');

    const weeklyToggle = screen.getByRole('switch', { name: /weekly summary/i });
    expect(weeklyToggle).toBeInTheDocument();
    expect(weeklyToggle).not.toBeChecked();

    const saveBtn = screen.getByRole('button', { name: /save notifications/i });
    expect(saveBtn).toBeDisabled();
  });

  it('populates initial active settings from profile', async () => {
    vi.spyOn(apiClient, 'getProfile').mockResolvedValue({
      id: 2,
      email: 'active@example.com',
      timezone: 'Europe/Kyiv',
      timezone_auto: true,
      daily_reminder_enabled: true,
      daily_reminder_time: '07:30:00',
      weekly_summary_enabled: true,
    });

    renderProfile();

    expect(await screen.findByDisplayValue('active@example.com')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /notifications/i })).toBeInTheDocument();

    const dailyToggle = screen.getByRole('switch', { name: /daily reminder/i });
    expect(dailyToggle).toBeChecked();

    const timeInput = screen.getByLabelText(/reminder time/i);
    expect(timeInput).toHaveValue('07:30');

    const weeklyToggle = screen.getByRole('switch', { name: /weekly summary/i });
    expect(weeklyToggle).toBeChecked();
  });

  it('updates daily reminder toggle and saves via PATCH /auth/profile/', async () => {
    const user = userEvent.setup();
    const updateSpy = vi.spyOn(apiClient, 'updateProfile').mockResolvedValue({
      ...mockProfile,
      daily_reminder_enabled: true,
    });

    renderProfile();

    const dailyToggle = await screen.findByRole('switch', { name: /daily reminder/i });
    expect(dailyToggle).not.toBeChecked();

    await user.click(dailyToggle);
    expect(dailyToggle).toBeChecked();

    const saveBtn = screen.getByRole('button', { name: /save notifications/i });
    expect(saveBtn).not.toBeDisabled();

    await user.click(saveBtn);

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith({
        daily_reminder_enabled: true,
        daily_reminder_time: '20:00',
        weekly_summary_enabled: false,
      });
    });

    expect(await screen.findByText(/notification preferences saved successfully!/i)).toBeInTheDocument();
  });

  it('updates reminder time picker and saves via PATCH /auth/profile/', async () => {
    const user = userEvent.setup();
    const updateSpy = vi.spyOn(apiClient, 'updateProfile').mockResolvedValue({
      ...mockProfile,
      daily_reminder_time: '08:45',
    });

    renderProfile();

    const timeInput = await screen.findByLabelText(/reminder time/i);
    await user.clear(timeInput);
    await user.type(timeInput, '08:45');

    const saveBtn = screen.getByRole('button', { name: /save notifications/i });
    expect(saveBtn).not.toBeDisabled();

    await user.click(saveBtn);

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith({
        daily_reminder_enabled: false,
        daily_reminder_time: '08:45',
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
        daily_reminder_enabled: false,
        daily_reminder_time: '20:00',
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
