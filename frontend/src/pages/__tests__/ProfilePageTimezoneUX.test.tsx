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

describe('ProfilePage timezone UX', () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem('habit_tracker_refresh_token', 'mock-refresh-token');
    vi.restoreAllMocks();
    vi.spyOn(apiClient, 'refreshTokens').mockResolvedValue('mock-access-token');
    vi.spyOn(apiClient, 'getProfile').mockResolvedValue(mockProfile);

    // Mock Intl DateTimeFormat with deterministic values (Kyiv)
    vi.spyOn(Intl, 'DateTimeFormat').mockImplementation(() => {
      return {
        resolvedOptions: () => ({ timeZone: 'Europe/Kyiv' }),
        formatToParts: () => [
          { type: 'timeZoneName', value: 'GMT+02:00' },
        ],
        format: () => '2026-10-26',
      } as unknown as Intl.DateTimeFormat;
    });
  });

  it('renders automatic timezone toggle showing Europe/Kyiv (UTC+02:00) when timezone_auto is true', async () => {
    renderProfile();

    expect(await screen.findByDisplayValue('tester@example.com')).toBeInTheDocument();

    const toggle = screen.getByRole('switch', { name: /set timezone automatically/i });
    expect(toggle).toBeChecked();

    // Check that automatic timezone info is displayed
    expect(screen.getByText(/Europe\/Kyiv \(UTC\+02:00\)/i)).toBeInTheDocument();

    // Searchable picker should NOT be visible when toggle is on
    expect(screen.queryByPlaceholderText(/search timezone/i)).not.toBeInTheDocument();
  });

  it('switching toggle off shows searchable timezone picker with detected timezone suggested first', async () => {
    const user = userEvent.setup();
    renderProfile();

    const toggle = await screen.findByRole('switch', { name: /set timezone automatically/i });
    expect(toggle).toBeChecked();

    await user.click(toggle);
    expect(toggle).not.toBeChecked();

    // Searchable picker should now be visible
    const searchInput = screen.getByPlaceholderText(/search timezone/i);
    expect(searchInput).toBeInTheDocument();

    // Detected timezone option is suggested first with badge
    const options = screen.getAllByRole('option');
    expect(options[0]).toHaveTextContent(/Europe\/Kyiv/i);
    expect(options[0]).toHaveTextContent(/detected/i);
  });

  it('type to filter filters the timezone list (e.g. "kyiv", "new york")', async () => {
    const user = userEvent.setup();
    renderProfile();

    const toggle = await screen.findByRole('switch', { name: /set timezone automatically/i });
    await user.click(toggle);

    const searchInput = screen.getByPlaceholderText(/search timezone/i);
    await user.type(searchInput, 'new york');

    const options = screen.getAllByRole('option');
    expect(options.length).toBe(1);
    expect(options[0]).toHaveTextContent(/America\/New_York/i);

    await user.clear(searchInput);
    await user.type(searchInput, 'kyiv');
    const kyivOptions = screen.getAllByRole('option');
    expect(kyivOptions.length).toBe(1);
    expect(kyivOptions[0]).toHaveTextContent(/Europe\/Kyiv/i);
  });

  it('shows small toast "Timezone updated to ..." when timezone is updated', async () => {
    const user = userEvent.setup();
    const updateSpy = vi.spyOn(apiClient, 'updateProfile').mockResolvedValue({
      id: 1,
      email: 'tester@example.com',
      timezone: 'America/New_York',
      timezone_auto: false,
    });

    renderProfile();

    const toggle = await screen.findByRole('switch', { name: /set timezone automatically/i });
    await user.click(toggle);

    const searchInput = screen.getByPlaceholderText(/search timezone/i);
    await user.type(searchInput, 'new york');

    const nyOption = screen.getByRole('option', { name: /America\/New_York/i });
    await user.click(nyOption);

    const saveBtn = screen.getByRole('button', { name: /save timezone/i });
    await user.click(saveBtn);

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith({
        timezone: 'America/New_York',
        timezone_auto: false,
      });
    });

    expect(await screen.findByText(/timezone updated to America\/New_York/i)).toBeInTheDocument();
  });
});
