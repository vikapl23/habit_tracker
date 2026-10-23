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
  });

  it('renders read-only email and timezone selector preselected with current timezone', async () => {
    renderProfile();

    expect(await screen.findByDisplayValue('tester@example.com')).toBeInTheDocument();
    const emailInput = screen.getByLabelText(/email address/i);
    expect(emailInput).toHaveAttribute('readOnly');

    const tzSelect = screen.getByLabelText(/timezone selector/i);
    await waitFor(() => {
      expect(tzSelect).toHaveValue('Europe/Kyiv');
    });

    // Bottom Navigation present
    expect(screen.getByRole('navigation', { name: /bottom navigation/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /today/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /archive/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /profile/i })).toBeInTheDocument();
  });

  it('updates timezone by calling PATCH /auth/profile/ and shows success message', async () => {
    const user = userEvent.setup();
    const updateSpy = vi.spyOn(apiClient, 'updateProfile').mockResolvedValue({
      id: 1,
      email: 'tester@example.com',
      timezone: 'Europe/Warsaw',
    });

    renderProfile();

    const tzSelect = await screen.findByLabelText(/timezone selector/i);

    // Change timezone
    await user.selectOptions(tzSelect, 'Europe/Warsaw');

    // Save button should now be enabled
    const saveBtn = screen.getByRole('button', { name: /save timezone/i });
    expect(saveBtn).not.toBeDisabled();

    await user.click(saveBtn);

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith({ timezone: 'Europe/Warsaw' });
    });

    expect(await screen.findByText(/timezone updated successfully/i)).toBeInTheDocument();
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
