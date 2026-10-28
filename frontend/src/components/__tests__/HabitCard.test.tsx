import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HabitCard } from '../HabitCard';
import { Habit } from '../../types/habit';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('HabitCard', () => {
  const measurableHabit: Habit = {
    id: 10,
    name: 'Read Pages',
    description: 'Read 20 pages a day',
    color: '#3B82F6',
    emoji: '📖',
    is_archived: false,
    frequency_type: 'daily',
    frequency_days: [],
    habit_type: 'measurable',
    target_value: 20,
    unit: 'pages',
    today_value: 5,
    today_progress: 25,
    current_streak: 3,
    longest_streak: 5,
    is_checked_today: false,
    is_scheduled_today: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  };

  it('type 7999 + Enter -> saved, no navigation', async () => {
    mockNavigate.mockClear();
    const handleToggle = vi.fn();
    const user = userEvent.setup();

    render(<HabitCard habit={measurableHabit} onToggle={handleToggle} />);

    // Verify interactive controls (button/input) are not nested inside role="button"
    const roleButtons = screen.getAllByRole('button');
    for (const btn of roleButtons) {
      expect(btn.closest('[role="button"]') === btn || btn.parentElement?.closest('[role="button"]') === null).toBe(true);
    }

    // Click current amount button to enter exact edit mode
    const editButton = screen.getByRole('button', {
      name: /Current amount 5 of 20 pages\. Tap to enter exact amount/i,
    });
    // The editButton should NOT be nested inside any other role="button"
    expect(editButton.parentElement?.closest('[role="button"]')).toBeNull();

    // Verify touch targets for quick decrement and quick increment buttons
    const decButton = screen.getByRole('button', { name: /Decrease Read Pages/i });
    expect(decButton.className).toMatch(/min-w-\[44px\]/);
    expect(decButton.className).toMatch(/min-h-\[44px\]/);

    const incButton = screen.getByRole('button', { name: /Add 1 pages to Read Pages/i });
    expect(incButton.className).toMatch(/min-w-\[44px\]/);
    expect(incButton.className).toMatch(/min-h-\[44px\]/);

    await user.click(editButton);

    // Verify input is rendered
    const input = screen.getByRole('spinbutton', {
      name: /Enter exact amount for Read Pages/i,
    });
    expect(input).toBeInTheDocument();

    // Type 7999 + Enter
    await user.clear(input);
    await user.type(input, '7999{Enter}');

    // onToggle should be called with mode: 'set' and value: 7999
    expect(handleToggle).toHaveBeenCalledTimes(1);
    expect(handleToggle).toHaveBeenCalledWith(measurableHabit, {
      value: 7999,
      mode: 'set',
    });

    // Parent navigation should not have been triggered
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('saves on blur if valid', async () => {
    const handleToggle = vi.fn();
    const user = userEvent.setup();

    render(<HabitCard habit={measurableHabit} onToggle={handleToggle} />);

    const editButton = screen.getByRole('button', {
      name: /Current amount 5 of 20 pages\. Tap to enter exact amount/i,
    });
    await user.click(editButton);

    const input = screen.getByRole('spinbutton', {
      name: /Enter exact amount for Read Pages/i,
    });
    await user.clear(input);
    await user.type(input, '15');
    await user.tab();

    expect(handleToggle).toHaveBeenCalledWith(measurableHabit, {
      value: 15,
      mode: 'set',
    });
  });

  it('cancels without saving on Escape', async () => {
    const handleToggle = vi.fn();
    const user = userEvent.setup();

    render(<HabitCard habit={measurableHabit} onToggle={handleToggle} />);

    const editButton = screen.getByRole('button', {
      name: /Current amount 5 of 20 pages\. Tap to enter exact amount/i,
    });
    await user.click(editButton);

    const input = screen.getByRole('spinbutton', {
      name: /Enter exact amount for Read Pages/i,
    });
    await user.clear(input);
    await user.type(input, '15{Escape}');

    expect(handleToggle).not.toHaveBeenCalled();
    expect(screen.queryByRole('spinbutton')).not.toBeInTheDocument();
  });

  it('renders reminder bell icon with time when reminder is set', () => {
    const habitWithReminder: Habit = {
      ...measurableHabit,
      reminder_enabled: true,
      reminder_time: '08:15:00',
    };
    render(<HabitCard habit={habitWithReminder} onToggle={vi.fn()} />);

    const badge = screen.getByTestId('habit-reminder-badge');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('08:15');
    expect(badge).toHaveAttribute('aria-label', 'Reminder set for 08:15');
  });

  it('does not render reminder bell icon when reminder is not enabled', () => {
    const habitWithoutReminder: Habit = {
      ...measurableHabit,
      reminder_enabled: false,
      reminder_time: null,
    };
    render(<HabitCard habit={habitWithoutReminder} onToggle={vi.fn()} />);

    expect(screen.queryByTestId('habit-reminder-badge')).not.toBeInTheDocument();
  });

  it('renders habit name for measurable habits', () => {
    render(<HabitCard habit={measurableHabit} onToggle={vi.fn()} />);
    expect(screen.getByRole('heading', { level: 3, name: 'Read Pages' })).toBeInTheDocument();
  });

  it('truncates long habit name and displays long units without breaking structure', () => {
    const longHabit: Habit = {
      ...measurableHabit,
      name: 'Read 20 pages of a book every evening',
      unit: 'kilometers',
      today_value: 0,
      target_value: 5,
    };
    render(<HabitCard habit={longHabit} onToggle={vi.fn()} />);

    const heading = screen.getByRole('heading', { level: 3, name: 'Read 20 pages of a book every evening' });
    expect(heading).toBeInTheDocument();
    expect(heading.className).toContain('truncate');

    expect(screen.getByText(/0 \/ 5 kilometers/i)).toBeInTheDocument();
  });

  it('disables quick decrement button when value is 0', async () => {
    const handleToggle = vi.fn();
    const user = userEvent.setup();
    const zeroHabit: Habit = {
      ...measurableHabit,
      today_value: 0,
    };
    render(<HabitCard habit={zeroHabit} onToggle={handleToggle} />);

    const decButton = screen.getByRole('button', { name: /Decrease Read Pages/i });
    expect(decButton).toBeDisabled();

    await user.click(decButton);
    expect(handleToggle).not.toHaveBeenCalled();
  });

  it('aligns "+" button as a normal 44x44 tap target without -m-2', () => {
    render(<HabitCard habit={measurableHabit} onToggle={vi.fn()} />);

    const incButton = screen.getByRole('button', { name: /Add 1 pages to Read Pages/i });
    expect(incButton.className).toMatch(/min-w-\[44px\]/);
    expect(incButton.className).toMatch(/min-h-\[44px\]/);
    expect(incButton.className).not.toMatch(/-m-2/);
  });
});
