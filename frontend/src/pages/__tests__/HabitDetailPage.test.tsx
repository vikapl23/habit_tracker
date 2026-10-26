import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { HabitDetailPage } from '../HabitDetailPage';
import { AuthProvider } from '../../context/AuthContext';
import { habitsApi } from '../../api/habits';
import { Habit } from '../../types/habit';

const mockDetailHabit: Habit = {
  id: 1,
  name: 'Drink Water',
  description: '8 glasses daily for hydration',
  color: '#3B82F6',
  emoji: '💧',
  is_archived: false,
  frequency_type: 'custom',
  frequency_days: [0, 1, 2, 3, 4], // Mon to Fri scheduled, Sat/Sun muted
  current_streak: 5,
  longest_streak: 12,
  is_checked_today: false,
  is_scheduled_today: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const renderHabitDetail = (habitId = 1) => {
  return render(
    <MemoryRouter
      initialEntries={[`/habits/${habitId}`]}
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <AuthProvider>
        <Routes>
          <Route path="/habits/:id" element={<HabitDetailPage />} />
          <Route path="/" element={<div>Dashboard Home</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>
  );
};

describe('HabitDetailPage (Step 5.5)', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date'], shouldAdvanceTime: true });
    vi.setSystemTime(new Date(2026, 9, 23, 12, 0, 0));
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders habit detail, streak cards, and month calendar with checked days and muted non-scheduled days', async () => {
    vi.spyOn(habitsApi, 'getHabit').mockResolvedValue(mockDetailHabit);
    vi.spyOn(habitsApi, 'getHabitStatistics').mockResolvedValue({
      habit_id: 1,
      completion_rate_7d: 0.7143,
      completion_rate_30d: 0.8,
      total_check_ins: 24,
      current_streak: 5,
      longest_streak: 12,
    });
    vi.spyOn(habitsApi, 'getHabitCheckIns').mockResolvedValue([
      { id: 101, date: '2026-10-05', created_at: '2026-10-05T00:00:00Z' },
      { id: 102, date: '2026-10-06', created_at: '2026-10-06T00:00:00Z' },
    ]);

    renderHabitDetail();

    // Verify Habit Title and Streaks
    expect(await screen.findByRole('heading', { level: 1, name: 'Drink Water' })).toBeInTheDocument();
    expect(screen.getAllByText('💧')[0]).toBeInTheDocument();
    expect(screen.getByText('8 glasses daily for hydration')).toBeInTheDocument();

    expect(screen.getByLabelText(/current streak 5 days/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/longest streak 12 days/i)).toBeInTheDocument();

    // Verify Statistics Cards
    expect(await screen.findByLabelText(/7-day completion 71%/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/30-day completion 80%/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/total check-ins 24/i)).toBeInTheDocument();

    // Verify Month Calendar is rendered
    const calendarHeading = screen.getByRole('heading', { level: 2, name: /2026/i });
    expect(calendarHeading).toBeInTheDocument();

    // Check weekday labels
    expect(screen.getByText('Mon')).toBeInTheDocument();
    expect(screen.getByText('Sun')).toBeInTheDocument();

    // Check checked day 2026-10-05 has habit color and completed label
    const checkedDayBtn = await screen.findByRole('button', {
      name: /2026-10-05, completed/i,
    });
    expect(checkedDayBtn).toHaveStyle({ backgroundColor: '#3B82F6' });
    expect(checkedDayBtn).toHaveAttribute('aria-pressed', 'true');

    // Check non-scheduled day is visually muted (e.g. October 11, 2026 is Sunday, not in [0..4])
    const sundayBtn = await screen.findByRole('button', {
      name: /2026-10-11.*not scheduled/i,
    });
    expect(sundayBtn).toHaveClass('opacity-40');
  });

  it('toggles an unchecked past day by calling checkHabit and updates streak cards', async () => {
    const user = userEvent.setup();
    vi.spyOn(habitsApi, 'getHabit').mockResolvedValue(mockDetailHabit);
    vi.spyOn(habitsApi, 'getHabitCheckIns').mockResolvedValue([]);
    const checkSpy = vi.spyOn(habitsApi, 'checkHabit').mockResolvedValue({
      status: 'created',
      habit_id: 1,
      date: '2026-10-02',
      current_streak: 6,
      longest_streak: 12,
    });

    renderHabitDetail();

    const pastDayBtn = await screen.findByRole('button', {
      name: /2026-10-02, incomplete/i,
    });
    expect(pastDayBtn).toHaveAttribute('aria-pressed', 'false');

    // Tap the past day to check in
    await user.click(pastDayBtn);

    await waitFor(() => {
      expect(checkSpy).toHaveBeenCalledWith(1, '2026-10-02');
      expect(pastDayBtn).toHaveAttribute('aria-pressed', 'true');
    });
    // Streaks updated to 6
    expect(await screen.findByLabelText(/current streak 6 days/i)).toBeInTheDocument();
  });

  it('toggles an already checked past day by calling uncheckHabit', async () => {
    const user = userEvent.setup();
    vi.spyOn(habitsApi, 'getHabit').mockResolvedValue(mockDetailHabit);
    vi.spyOn(habitsApi, 'getHabitCheckIns').mockResolvedValue([
      { id: 101, date: '2026-10-02', created_at: '2026-10-02T00:00:00Z' },
    ]);
    const uncheckSpy = vi.spyOn(habitsApi, 'uncheckHabit').mockResolvedValue({
      status: 'removed',
      habit_id: 1,
      date: '2026-10-02',
      current_streak: 4,
      longest_streak: 12,
    });

    renderHabitDetail();

    const checkedDayBtn = await screen.findByRole('button', {
      name: /2026-10-02, completed/i,
    });
    expect(checkedDayBtn).toHaveAttribute('aria-pressed', 'true');

    // Tap to uncheck
    await user.click(checkedDayBtn);

    await waitFor(() => {
      expect(uncheckSpy).toHaveBeenCalledWith(1, '2026-10-02');
      expect(checkedDayBtn).toHaveAttribute('aria-pressed', 'false');
    });
    expect(await screen.findByLabelText(/current streak 4 days/i)).toBeInTheDocument();
  });

  it('disables future days from being tapped', async () => {
    vi.spyOn(habitsApi, 'getHabit').mockResolvedValue(mockDetailHabit);
    vi.spyOn(habitsApi, 'getHabitCheckIns').mockResolvedValue([]);

    renderHabitDetail();

    // Any day clearly in the future relative to 2026-10-23, e.g. October 30, 2026
    const futureBtn = await screen.findByRole('button', {
      name: /2026-10-30.*disabled/i,
    });
    expect(futureBtn).toBeDisabled();
    expect(futureBtn).toHaveClass('cursor-not-allowed');
  });

  it('navigates to previous and next month and fetches month check-ins', async () => {
    const user = userEvent.setup();
    vi.spyOn(habitsApi, 'getHabit').mockResolvedValue(mockDetailHabit);
    const checkInsSpy = vi.spyOn(habitsApi, 'getHabitCheckIns').mockResolvedValue([]);

    renderHabitDetail();

    await screen.findByRole('heading', { level: 1, name: 'Drink Water' });

    // Click previous month button
    const prevBtn = screen.getByRole('button', { name: /previous month/i });
    await user.click(prevBtn);

    await waitFor(() => {
      expect(checkInsSpy).toHaveBeenCalledWith(1, '2026-09-01', '2026-09-30');
    });

    // Click next month button to go back to October
    const nextBtn = screen.getByRole('button', { name: /next month/i });
    await user.click(nextBtn);

    await waitFor(() => {
      expect(checkInsSpy).toHaveBeenCalledWith(1, '2026-10-01', '2026-10-31');
    });
  });

  it('navigates back to dashboard when back arrow is clicked', async () => {
    const user = userEvent.setup();
    vi.spyOn(habitsApi, 'getHabit').mockResolvedValue(mockDetailHabit);
    vi.spyOn(habitsApi, 'getHabitCheckIns').mockResolvedValue([]);

    renderHabitDetail();

    const backBtn = await screen.findByRole('button', { name: /back to dashboard/i });
    await user.click(backBtn);

    expect(await screen.findByText('Dashboard Home')).toBeInTheDocument();
  });
});
