import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HabitCard } from '../HabitCard';
import { Habit } from '../types/habit';

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

    // Click current amount button to enter exact edit mode
    const editButton = screen.getByRole('button', {
      name: /Current amount 5 of 20 pages\. Tap to enter exact amount/i,
    });
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
});
