import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { StatsPage } from '../StatsPage';
import { AuthProvider } from '../../context/AuthContext';
import { habitsApi } from '../../api/habits';
import { StatisticsSummary } from '../../types/habit';

const mockSummary: StatisticsSummary = {
  overall_completion_rate_week: 0.8571,
  overall_completion_rate_month: 0.7333,
  best_habit: {
    id: 42,
    name: 'Morning Meditation',
    emoji: '🧘',
    color: '#8B5CF6',
    completion_rate_30d: 0.9,
  },
  total_active_habits: 5,
  total_check_ins: 128,
};

const renderStatsPage = () => {
  return render(
    <MemoryRouter
      initialEntries={['/stats']}
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <AuthProvider>
        <Routes>
          <Route path="/stats" element={<StatsPage />} />
          <Route path="/habits/:id" element={<div>Habit Detail Page</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>
  );
};

describe('StatsPage (Phase 4)', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date'], shouldAdvanceTime: true });
    vi.setSystemTime(new Date(2026, 9, 26, 12, 0, 0));
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders loading skeleton while fetching statistics summary', () => {
    vi.spyOn(habitsApi, 'getStatisticsSummary').mockReturnValue(new Promise(() => {}));
    renderStatsPage();
    expect(screen.getByTestId('stats-loading-skeleton')).toBeInTheDocument();
  });

  it('renders error state when request fails and allows retry', async () => {
    const user = userEvent.setup();
    const getSummarySpy = vi
      .spyOn(habitsApi, 'getStatisticsSummary')
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValueOnce(mockSummary);

    renderStatsPage();

    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/Failed to load statistics/i)).toBeInTheDocument();

    const retryButton = screen.getByRole('button', { name: /Retry/i });
    await user.click(retryButton);

    await waitFor(() => {
      expect(getSummarySpy).toHaveBeenCalledTimes(2);
    });

    expect(await screen.findByLabelText(/this week completion 86%/i)).toBeInTheDocument();
  });

  it('renders summary statistics cards with week, month, best habit, active habits and check-ins', async () => {
    vi.spyOn(habitsApi, 'getStatisticsSummary').mockResolvedValue(mockSummary);

    renderStatsPage();

    expect(await screen.findByRole('heading', { level: 1, name: 'Statistics' })).toBeInTheDocument();

    // Rates: week (86%) and month (73%)
    expect(screen.getByLabelText(/this week completion 86%/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/this month completion 73%/i)).toBeInTheDocument();

    // Best habit
    expect(screen.getByText('Morning Meditation')).toBeInTheDocument();
    expect(screen.getByText('90%')).toBeInTheDocument();
    expect(screen.getByText('🧘')).toBeInTheDocument();

    // Counters: active habits and total check-ins
    expect(screen.getByLabelText(/total active habits 5/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/total check-ins 128/i)).toBeInTheDocument();
  });

  it('renders empty best habit placeholder when no best habit exists', async () => {
    vi.spyOn(habitsApi, 'getStatisticsSummary').mockResolvedValue({
      ...mockSummary,
      best_habit: null,
    });

    renderStatsPage();

    expect(await screen.findByText(/No best habit yet/i)).toBeInTheDocument();
  });
});
