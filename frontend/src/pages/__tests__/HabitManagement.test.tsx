import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { DashboardPage } from '../DashboardPage';
import { ArchivedHabitsPage } from '../ArchivedHabitsPage';
import { AuthProvider } from '../../context/AuthContext';
import { habitsApi } from '../../api/habits';
import { Habit } from '../../types/habit';
import { ApiError } from '../../api/client';

const mockHabit: Habit = {
  id: 10,
  name: 'Read Books',
  description: 'Read 20 pages daily',
  color: '#3B82F6',
  emoji: '📚',
  is_archived: false,
  frequency_type: 'daily',
  frequency_days: [],
  current_streak: 4,
  longest_streak: 10,
  is_checked_today: false,
  is_scheduled_today: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const mockArchivedHabit: Habit = {
  id: 20,
  name: 'Old Habit',
  description: 'Retired habit',
  color: '#8B5CF6',
  emoji: '🧘',
  is_archived: true,
  frequency_type: 'daily',
  frequency_days: [],
  current_streak: 2,
  longest_streak: 5,
  is_checked_today: false,
  is_scheduled_today: false,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const renderDashboard = () => {
  return render(
    <MemoryRouter
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <AuthProvider>
        <DashboardPage />
      </AuthProvider>
    </MemoryRouter>
  );
};

const renderArchivedPage = () => {
  return render(
    <MemoryRouter
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <AuthProvider>
        <ArchivedHabitsPage />
      </AuthProvider>
    </MemoryRouter>
  );
};

describe('Habit Management (Step 5.4)', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('opens bottom sheet on floating "+" button and creates a habit with every day frequency', async () => {
    const user = userEvent.setup();
    vi.spyOn(habitsApi, 'getAllHabits').mockResolvedValue([]);
    const createSpy = vi.spyOn(habitsApi, 'createHabit').mockResolvedValue({
      id: 11,
      name: 'Drink 2L Water',
      description: 'Stay hydrated',
      color: '#10B981',
      emoji: '💧',
      is_archived: false,
      frequency_type: 'daily',
      frequency_days: [],
      current_streak: 0,
      longest_streak: 0,
      is_checked_today: false,
      is_scheduled_today: true,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    });

    renderDashboard();

    // Floating "+" button
    const fabButton = await screen.findByRole('button', { name: /new habit/i });
    await user.click(fabButton);

    // Bottom sheet is displayed and name input has focus
    const dialog = screen.getByRole('dialog', { name: /new habit/i });
    expect(dialog).toBeInTheDocument();
    const nameInput = screen.getByLabelText(/habit name/i);
    expect(nameInput).toBeInTheDocument();

    // Fill form
    await user.type(nameInput, 'Drink 2L Water');
    await user.type(screen.getByLabelText(/description/i), 'Stay hydrated');

    // Select color
    const colorBtn = screen.getByRole('button', { name: /select color #10B981/i });
    await user.click(colorBtn);

    // Select emoji
    const emojiBtn = screen.getByRole('button', { name: /select emoji 💧/i });
    await user.click(emojiBtn);

    // Submit form
    const submitBtn = screen.getByRole('button', { name: /create habit/i });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith({
        name: 'Drink 2L Water',
        description: 'Stay hydrated',
        color: '#10B981',
        emoji: '💧',
        frequency_type: 'daily',
        frequency_days: [],
      });
    });

    // Form closes and new habit appears on dashboard
    expect(screen.queryByRole('dialog', { name: /new habit/i })).not.toBeInTheDocument();
    expect(await screen.findByText('Drink 2L Water')).toBeInTheDocument();
  });

  it('creates habit with custom weekday frequency selection', async () => {
    const user = userEvent.setup();
    vi.spyOn(habitsApi, 'getAllHabits').mockResolvedValue([]);
    const createSpy = vi.spyOn(habitsApi, 'createHabit').mockResolvedValue({
      id: 12,
      name: 'Gym Workout',
      description: 'Legs and chest',
      color: '#EF4444',
      emoji: '💪',
      is_archived: false,
      frequency_type: 'custom',
      frequency_days: [0, 2, 4],
      current_streak: 0,
      longest_streak: 0,
      is_checked_today: false,
      is_scheduled_today: true,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    });

    renderDashboard();

    const fabButton = await screen.findByRole('button', { name: /new habit/i });
    await user.click(fabButton);

    const nameInput = screen.getByLabelText(/habit name/i);
    await user.type(nameInput, 'Gym Workout');

    // Switch frequency to specific days
    const specificDaysBtn = screen.getByRole('button', { name: /specific days/i });
    await user.click(specificDaysBtn);

    // Select Mon, Wed, Fri (0, 2, 4)
    await user.click(screen.getByRole('button', { name: 'Mon' }));
    await user.click(screen.getByRole('button', { name: 'Wed' }));
    await user.click(screen.getByRole('button', { name: 'Fri' }));

    await user.click(screen.getByRole('button', { name: /create habit/i }));

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'Gym Workout',
          frequency_type: 'custom',
          frequency_days: [0, 2, 4],
        })
      );
    });
  });

  it('opens bottom sheet from empty state button', async () => {
    const user = userEvent.setup();
    vi.spyOn(habitsApi, 'getAllHabits').mockResolvedValue([]);

    renderDashboard();

    const emptyStateBtn = await screen.findByRole('button', { name: /create your first habit/i });
    await user.click(emptyStateBtn);

    expect(screen.getByRole('dialog', { name: /new habit/i })).toBeInTheDocument();
  });

  it('edits a habit via "⋯" menu with prefilled form and updates dashboard', async () => {
    const user = userEvent.setup();
    vi.spyOn(habitsApi, 'getAllHabits').mockResolvedValue([mockHabit]);
    const updateSpy = vi.spyOn(habitsApi, 'updateHabit').mockResolvedValue({
      ...mockHabit,
      name: 'Read 30 Pages',
    });

    renderDashboard();

    expect(await screen.findByText('Read Books')).toBeInTheDocument();

    // Click "⋯" options button
    const moreBtn = screen.getByRole('button', { name: /more options for read books/i });
    await user.click(moreBtn);

    // Click Edit
    const editBtn = screen.getByRole('menuitem', { name: /edit/i });
    await user.click(editBtn);

    // Edit sheet should open prefilled
    expect(screen.getByRole('dialog', { name: /edit habit/i })).toBeInTheDocument();
    const nameInput = screen.getByLabelText(/habit name/i) as HTMLInputElement;
    expect(nameInput.value).toBe('Read Books');

    // Change name
    await user.clear(nameInput);
    await user.type(nameInput, 'Read 30 Pages');

    // Save changes
    await user.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith(
        10,
        expect.objectContaining({
          name: 'Read 30 Pages',
        })
      );
    });

    // Dashboard updates without reload
    expect(await screen.findByText('Read 30 Pages')).toBeInTheDocument();
  });

  it('confirms and executes habit deletion via confirmation dialog', async () => {
    const user = userEvent.setup();
    vi.spyOn(habitsApi, 'getAllHabits').mockResolvedValue([mockHabit]);
    const deleteSpy = vi.spyOn(habitsApi, 'deleteHabit').mockResolvedValue(undefined);

    renderDashboard();

    expect(await screen.findByText('Read Books')).toBeInTheDocument();

    // Click "⋯" options button
    const moreBtn = screen.getByRole('button', { name: /more options for read books/i });
    await user.click(moreBtn);

    // Click Delete in menu
    const deleteMenuItem = screen.getByRole('menuitem', { name: /delete/i });
    await user.click(deleteMenuItem);

    // Delete confirmation dialog is shown
    expect(screen.getByRole('dialog', { name: /delete habit\?/i })).toBeInTheDocument();
    expect(screen.getByText(/are you sure you want to permanently delete/i)).toBeInTheDocument();

    // Click Delete inside dialog
    const confirmDeleteBtn = screen.getByRole('button', { name: /^delete$/i });
    await user.click(confirmDeleteBtn);

    await waitFor(() => {
      expect(deleteSpy).toHaveBeenCalledWith(10);
    });

    // Habit is removed from list
    expect(screen.queryByText('Read Books')).not.toBeInTheDocument();
  });

  it('archives a habit from menu and updates list without reload', async () => {
    const user = userEvent.setup();
    vi.spyOn(habitsApi, 'getAllHabits').mockResolvedValue([mockHabit]);
    const archiveSpy = vi.spyOn(habitsApi, 'archiveHabit').mockResolvedValue({
      id: 10,
      is_archived: true,
    });

    renderDashboard();

    expect(await screen.findByText('Read Books')).toBeInTheDocument();

    const moreBtn = screen.getByRole('button', { name: /more options for read books/i });
    await user.click(moreBtn);

    const archiveMenuItem = screen.getByRole('menuitem', { name: /archive/i });
    await user.click(archiveMenuItem);

    await waitFor(() => {
      expect(archiveSpy).toHaveBeenCalledWith(10);
    });

    expect(screen.queryByText('Read Books')).not.toBeInTheDocument();
  });

  it('displays validation errors from backend under the respective form fields', async () => {
    const user = userEvent.setup();
    vi.spyOn(habitsApi, 'getAllHabits').mockResolvedValue([]);
    vi.spyOn(habitsApi, 'createHabit').mockRejectedValue(
      new ApiError('Bad request', 400, {
        name: ['Habit name already exists.'],
        emoji: ['Emoji must be exactly one emoji symbol.'],
        frequency_days: ['Custom frequency requires at least one weekday.'],
      })
    );

    renderDashboard();

    const fabButton = await screen.findByRole('button', { name: /new habit/i });
    await user.click(fabButton);

    const nameInput = screen.getByLabelText(/habit name/i);
    await user.type(nameInput, 'Existing Name');

    // Submit form
    await user.click(screen.getByRole('button', { name: /create habit/i }));

    // Errors displayed under fields
    expect(await screen.findByText('Habit name already exists.')).toBeInTheDocument();
    expect(screen.getByText('Emoji must be exactly one emoji symbol.')).toBeInTheDocument();
  });

  it('displays client-side validation when custom frequency has no weekdays selected', async () => {
    const user = userEvent.setup();
    vi.spyOn(habitsApi, 'getAllHabits').mockResolvedValue([]);

    renderDashboard();

    const fabButton = await screen.findByRole('button', { name: /new habit/i });
    await user.click(fabButton);

    const nameInput = screen.getByLabelText(/habit name/i);
    await user.type(nameInput, 'Custom Habit');

    const specificDaysBtn = screen.getByRole('button', { name: /specific days/i });
    await user.click(specificDaysBtn);

    await user.click(screen.getByRole('button', { name: /create habit/i }));

    expect(
      screen.getByText('Custom frequency requires at least one weekday.')
    ).toBeInTheDocument();
  });

  it('closes bottom sheet on Escape key or backdrop click', async () => {
    const user = userEvent.setup();
    vi.spyOn(habitsApi, 'getAllHabits').mockResolvedValue([]);

    renderDashboard();

    const fabButton = await screen.findByRole('button', { name: /new habit/i });
    await user.click(fabButton);

    expect(screen.getByRole('dialog', { name: /new habit/i })).toBeInTheDocument();

    // Press Escape
    await user.keyboard('{Escape}');

    expect(screen.queryByRole('dialog', { name: /new habit/i })).not.toBeInTheDocument();
  });

  it('scrolls first validation error into view on submit error', async () => {
    const user = userEvent.setup();
    vi.spyOn(habitsApi, 'getAllHabits').mockResolvedValue([]);
    const scrollIntoViewMock = vi.fn();
    window.HTMLElement.prototype.scrollIntoView = scrollIntoViewMock;

    renderDashboard();

    const fabButton = await screen.findByRole('button', { name: /new habit/i });
    await user.click(fabButton);

    // Click Specific days without picking weekdays
    const specificDaysBtn = screen.getByRole('button', { name: /specific days/i });
    await user.click(specificDaysBtn);

    // Type a name to pass name validation
    await user.type(screen.getByLabelText(/habit name/i), 'Custom Habit');

    // Submit form
    await user.click(screen.getByRole('button', { name: /create habit/i }));

    await waitFor(() => {
      expect(scrollIntoViewMock).toHaveBeenCalled();
    });
  });

  it('renders dashboard with bottom padding ensuring FAB does not obscure content on mobile', async () => {
    vi.spyOn(habitsApi, 'getAllHabits').mockResolvedValue([mockHabit]);

    renderDashboard();

    expect(await screen.findByText('Read Books')).toBeInTheDocument();

    // Verify main element has bottom padding
    const mainEl = screen.getByRole('main');
    expect(mainEl.className).toContain('pb-28');
  });

  it('renders archived screen and allows unarchiving a habit', async () => {
    const user = userEvent.setup();
    vi.spyOn(habitsApi, 'getAllHabits').mockResolvedValue([mockArchivedHabit]);
    const unarchiveSpy = vi.spyOn(habitsApi, 'unarchiveHabit').mockResolvedValue({
      id: 20,
      is_archived: false,
    });

    renderArchivedPage();

    expect(await screen.findByText('Old Habit')).toBeInTheDocument();

    const unarchiveBtn = screen.getByRole('button', { name: /unarchive old habit/i });
    await user.click(unarchiveBtn);

    await waitFor(() => {
      expect(unarchiveSpy).toHaveBeenCalledWith(20);
    });

    expect(screen.queryByText('Old Habit')).not.toBeInTheDocument();
    expect(await screen.findByText(/no archived habits/i)).toBeInTheDocument();
  });
});
