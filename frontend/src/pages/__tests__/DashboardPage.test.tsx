import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { DashboardPage } from '../DashboardPage';
import { AuthProvider } from '../../context/AuthContext';
import { habitsApi } from '../../api/habits';
import { Habit } from '../../types/habit';
import { ApiError } from '../../api/client';

const mockScheduledHabit: Habit = {
  id: 1,
  name: 'Drink Water',
  description: '8 glasses daily',
  color: '#3B82F6',
  emoji: '💧',
  is_archived: false,
  frequency_type: 'daily',
  frequency_days: [],
  current_streak: 5,
  longest_streak: 12,
  is_checked_today: false,
  is_scheduled_today: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const mockCheckedScheduledHabit: Habit = {
  id: 2,
  name: 'Morning Meditation',
  description: '10 minutes mindfulness',
  color: '#10B981',
  emoji: '🧘',
  is_archived: false,
  frequency_type: 'daily',
  frequency_days: [],
  current_streak: 8,
  longest_streak: 15,
  is_checked_today: true,
  is_scheduled_today: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const mockNotScheduledHabit: Habit = {
  id: 3,
  name: 'Gym Workout',
  description: 'Full body strength',
  color: '#EF4444',
  emoji: '🏋️',
  is_archived: false,
  frequency_type: 'custom',
  frequency_days: [1, 3, 5],
  current_streak: 3,
  longest_streak: 6,
  is_checked_today: false,
  is_scheduled_today: false,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const renderDashboard = (props: { onCreateHabit?: () => void } = {}) => {
  return render(
    <MemoryRouter
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <AuthProvider>
        <DashboardPage {...props} />
      </AuthProvider>
    </MemoryRouter>
  );
};

describe('DashboardPage Mobile View', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('renders loading skeleton while habits are fetching', async () => {
    // Keep promise pending
    vi.spyOn(habitsApi, 'getAllHabits').mockReturnValue(new Promise(() => {}));

    renderDashboard();

    expect(screen.getByRole('status', { name: /loading dashboard/i })).toBeInTheDocument();
  });

  it('renders habits list with emoji, name, color accent, streak badge, and best streak', async () => {
    vi.spyOn(habitsApi, 'getAllHabits').mockResolvedValue([
      mockScheduledHabit,
      mockCheckedScheduledHabit,
    ]);

    renderDashboard();

    // Wait for habits to load
    expect(await screen.findByText('Drink Water')).toBeInTheDocument();
    expect(screen.getByText('Morning Meditation')).toBeInTheDocument();

    // Emojis
    expect(screen.getByText('💧')).toBeInTheDocument();
    expect(screen.getByText('🧘')).toBeInTheDocument();

    // Streak badge and best streak
    expect(screen.getByText(/🔥 5/)).toBeInTheDocument();
    expect(screen.getByText(/best 12d/)).toBeInTheDocument();
    expect(screen.getByText(/🔥 8/)).toBeInTheDocument();
    expect(screen.getByText(/best 15d/)).toBeInTheDocument();

    // Best current streak in summary card (max between 5 and 8 is 8)
    const bestStreakHeading = screen.getByText('Current Streak');
    expect(bestStreakHeading).toBeInTheDocument();
    expect(screen.getByText('8')).toBeInTheDocument();

    // Header progress counts only scheduled habits: 1 checked out of 2 scheduled
    expect(screen.getByText('1 of 2 done today')).toBeInTheDocument();
    const progressbar = screen.getByRole('progressbar');
    expect(progressbar).toHaveAttribute('aria-valuenow', '1');
    expect(progressbar).toHaveAttribute('aria-valuemax', '2');
  });

  it('splits scheduled habits into Today and unscheduled into collapsed Not Today section', async () => {
    const user = userEvent.setup();
    vi.spyOn(habitsApi, 'getAllHabits').mockResolvedValue([
      mockScheduledHabit,
      mockNotScheduledHabit,
    ]);

    renderDashboard();

    expect(await screen.findByText('Drink Water')).toBeInTheDocument();

    // Not today habit should initially not be visible
    expect(screen.queryByText('Gym Workout')).not.toBeInTheDocument();

    // Find and expand "Not today" toggle button
    const notTodayToggle = screen.getByRole('button', { name: /not today/i });
    expect(notTodayToggle).toHaveAttribute('aria-expanded', 'false');

    await user.click(notTodayToggle);

    expect(notTodayToggle).toHaveAttribute('aria-expanded', 'true');
    expect(await screen.findByText('Gym Workout')).toBeInTheDocument();
    expect(screen.getByText('🏋️')).toBeInTheDocument();

    // Collapsing it again hides it
    await user.click(notTodayToggle);
    expect(screen.queryByText('Gym Workout')).not.toBeInTheDocument();
  });

  it('optimistically toggles check-in and confirms with API', async () => {
    const user = userEvent.setup();
    vi.spyOn(habitsApi, 'getAllHabits').mockResolvedValue([mockScheduledHabit]);
    const checkSpy = vi.spyOn(habitsApi, 'checkHabit').mockResolvedValue({
      status: 'created',
      habit_id: 1,
      date: '2026-10-23',
      current_streak: 9,
      longest_streak: 12,
    });

    renderDashboard();

    const habitCard = await screen.findByRole('button', {
      name: /toggle drink water, currently incomplete/i,
    });
    expect(habitCard).toHaveAttribute('aria-pressed', 'false');

    // Click card to check
    await user.click(habitCard);

    await waitFor(() => {
      expect(checkSpy).toHaveBeenCalledWith(1);
      expect(habitCard).toHaveAttribute('aria-pressed', 'true');
    });
    // Server streak (9) applied, verifying it doesn't only stay on the optimistic 5+1=6
    expect(await screen.findByText(/🔥 9/)).toBeInTheDocument();

    // Check progress updated: 1 of 1 done today
    expect(screen.getByText('1 of 1 done today')).toBeInTheDocument();
  });

  it('toggles check-in off (uncheck) for an already checked habit', async () => {
    const user = userEvent.setup();
    vi.spyOn(habitsApi, 'getAllHabits').mockResolvedValue([mockCheckedScheduledHabit]);
    const uncheckSpy = vi.spyOn(habitsApi, 'uncheckHabit').mockResolvedValue({
      status: 'removed',
      habit_id: 2,
      date: '2026-10-23',
      current_streak: 7,
      longest_streak: 15,
    });

    renderDashboard();

    const habitCard = await screen.findByRole('button', {
      name: /toggle morning meditation, currently completed/i,
    });
    expect(habitCard).toHaveAttribute('aria-pressed', 'true');

    // Click card to uncheck
    await user.click(habitCard);

    await waitFor(() => {
      expect(uncheckSpy).toHaveBeenCalledWith(2);
      expect(habitCard).toHaveAttribute('aria-pressed', 'false');
    });

    // Progress updated: 0 of 1 done today
    expect(screen.getByText('0 of 1 done today')).toBeInTheDocument();
  });

  it('rolls back optimistic update and shows toast error when check API fails', async () => {
    const user = userEvent.setup();
    vi.spyOn(habitsApi, 'getAllHabits').mockResolvedValue([mockScheduledHabit]);

    let rejectPromise!: (err: unknown) => void;
    vi.spyOn(habitsApi, 'checkHabit').mockReturnValue(
      new Promise((_, reject) => {
        rejectPromise = reject;
      })
    );

    renderDashboard();

    const habitCard = await screen.findByRole('button', {
      name: /toggle drink water, currently incomplete/i,
    });
    expect(habitCard).toHaveAttribute('aria-pressed', 'false');

    await user.click(habitCard);

    // Optimistically pressed first while request is in-flight
    expect(habitCard).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText(/🔥 6/)).toBeInTheDocument();

    // Trigger rejection
    rejectPromise(new ApiError('Network connection lost', 500, { detail: 'Server error' }));

    // Waits for rejection and rollback
    await waitFor(() => {
      expect(habitCard).toHaveAttribute('aria-pressed', 'false');
    });

    // Reverted streak
    expect(screen.getByText(/🔥 5/)).toBeInTheDocument();

    // Toast error alert is displayed
    const toastAlert = await screen.findByRole('alert');
    expect(toastAlert).toBeInTheDocument();
    expect(screen.getByText('Server error')).toBeInTheDocument();
  });

  it('renders empty state when there are no habits and handles create button click', async () => {
    const user = userEvent.setup();
    vi.spyOn(habitsApi, 'getAllHabits').mockResolvedValue([]);
    const onCreateHabit = vi.fn();

    renderDashboard({ onCreateHabit });

    expect(await screen.findByText('No habits yet')).toBeInTheDocument();
    const createButton = screen.getByRole('button', { name: /create your first habit/i });
    expect(createButton).toBeInTheDocument();

    await user.click(createButton);
    expect(onCreateHabit).toHaveBeenCalledTimes(1);
  });

  it('renders error state with retry button when fetching habits fails', async () => {
    const user = userEvent.setup();
    const getAllSpy = vi
      .spyOn(habitsApi, 'getAllHabits')
      .mockRejectedValueOnce(new Error('Network error: server unreachable'))
      .mockResolvedValueOnce([mockScheduledHabit]);

    renderDashboard();

    expect(await screen.findByText('Unable to load habits')).toBeInTheDocument();
    expect(screen.getByText(/network error: server unreachable/i)).toBeInTheDocument();

    const retryButton = screen.getByRole('button', { name: /retry/i });
    expect(retryButton).toBeInTheDocument();

    await user.click(retryButton);

    expect(getAllSpy).toHaveBeenCalledTimes(2);
    expect(await screen.findByText('Drink Water')).toBeInTheDocument();
  });

  it('renders bottom navigation with Today, Archive, and Profile, with FAB above navigation', async () => {
    vi.spyOn(habitsApi, 'getAllHabits').mockResolvedValue([mockScheduledHabit]);

    renderDashboard();

    expect(await screen.findByText('Drink Water')).toBeInTheDocument();

    const bottomNav = screen.getByRole('navigation', { name: /bottom navigation/i });
    expect(bottomNav).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /today/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /archive/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /profile/i })).toBeInTheDocument();

    // Check that FAB is rendered and positioned above bottom navigation bar
    const fab = screen.getByRole('button', { name: /new habit/i });
    expect(fab).toBeInTheDocument();
    expect(fab.parentElement?.className).toContain('bottom-[');
  });

  it('tapping on habit name/emoji triggers view details rather than toggling check-in', async () => {
    const user = userEvent.setup();
    vi.spyOn(habitsApi, 'getAllHabits').mockResolvedValue([mockScheduledHabit]);
    const checkSpy = vi.spyOn(habitsApi, 'checkHabit');

    renderDashboard();

    const detailsBtn = await screen.findByRole('button', {
      name: /view details for drink water/i,
    });
    expect(detailsBtn).toBeInTheDocument();

    // Tap habit details button
    await user.click(detailsBtn);

    // checkHabit should NOT have been called
    expect(checkSpy).not.toHaveBeenCalled();
  });
});
