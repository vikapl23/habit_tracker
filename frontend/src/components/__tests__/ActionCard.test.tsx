import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ActionCard } from '../ActionCard';
import { PendingAction } from '../../types/coach';

const futureDate = new Date(Date.now() + 15 * 60 * 1000).toISOString();
const pastDate = new Date(Date.now() - 1000).toISOString();

const mockPendingAction: PendingAction = {
  id: 10,
  action_type: 'create_habit',
  summary: 'Create habit: Meditation, 5 minutes, daily, reminder 08:00',
  status: 'pending',
  expires_at: futureDate,
};

describe('ActionCard Component (Step 10.5)', () => {
  it('renders pending action card with summary and action buttons', () => {
    const onConfirm = vi.fn().mockResolvedValue(undefined);
    const onCancel = vi.fn().mockResolvedValue(undefined);

    render(
      <ActionCard
        action={mockPendingAction}
        onConfirm={onConfirm}
        onCancel={onCancel}
      />
    );

    expect(
      screen.getByText('Create habit: Meditation, 5 minutes, daily, reminder 08:00')
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /confirm/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
  });

  it('calls onConfirm when Confirm button is clicked', async () => {
    const user = userEvent.setup();
    let resolveConfirm!: () => void;
    const confirmPromise = new Promise<void>((resolve) => {
      resolveConfirm = resolve;
    });
    const onConfirm = vi.fn().mockReturnValue(confirmPromise);
    const onCancel = vi.fn().mockResolvedValue(undefined);

    render(
      <ActionCard
        action={mockPendingAction}
        onConfirm={onConfirm}
        onCancel={onCancel}
      />
    );

    const confirmBtn = screen.getByRole('button', { name: /confirm/i });
    await user.click(confirmBtn);

    expect(onConfirm).toHaveBeenCalledWith(10);
    expect(screen.getByRole('button', { name: /confirming/i })).toBeDisabled();

    resolveConfirm();
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /confirming/i })).not.toBeInTheDocument();
    });
  });

  it('calls onCancel when Cancel button is clicked', async () => {
    const user = userEvent.setup();
    let resolveCancel!: () => void;
    const cancelPromise = new Promise<void>((resolve) => {
      resolveCancel = resolve;
    });
    const onConfirm = vi.fn().mockResolvedValue(undefined);
    const onCancel = vi.fn().mockReturnValue(cancelPromise);

    render(
      <ActionCard
        action={mockPendingAction}
        onConfirm={onConfirm}
        onCancel={onCancel}
      />
    );

    const cancelBtn = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelBtn);

    expect(onCancel).toHaveBeenCalledWith(10);
    expect(screen.getByRole('button', { name: /cancelling/i })).toBeDisabled();

    resolveCancel();
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /cancelling/i })).not.toBeInTheDocument();
    });
  });

  it('renders confirmed badge when status is confirmed', () => {
    const confirmedAction: PendingAction = {
      ...mockPendingAction,
      status: 'confirmed',
    };

    render(
      <ActionCard
        action={confirmedAction}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );

    expect(screen.queryByRole('button', { name: /confirm/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /cancel/i })).not.toBeInTheDocument();
    expect(screen.getByText(/confirmed/i)).toBeInTheDocument();
  });

  it('renders cancelled badge when status is cancelled', () => {
    const cancelledAction: PendingAction = {
      ...mockPendingAction,
      status: 'cancelled',
    };

    render(
      <ActionCard
        action={cancelledAction}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );

    expect(screen.queryByRole('button', { name: /confirm/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /cancel/i })).not.toBeInTheDocument();
    expect(screen.getByText(/cancelled/i)).toBeInTheDocument();
  });

  it('renders expired badge when status is explicitly expired', () => {
    const expiredAction: PendingAction = {
      ...mockPendingAction,
      status: 'expired',
    };

    render(
      <ActionCard
        action={expiredAction}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );

    expect(screen.queryByRole('button', { name: /confirm/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /cancel/i })).not.toBeInTheDocument();
    expect(screen.getByText(/expired/i)).toBeInTheDocument();
  });

  it('renders expired badge when expires_at timestamp has passed', () => {
    const pastAction: PendingAction = {
      ...mockPendingAction,
      status: 'pending',
      expires_at: pastDate,
    };

    render(
      <ActionCard
        action={pastAction}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );

    expect(screen.queryByRole('button', { name: /confirm/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /cancel/i })).not.toBeInTheDocument();
    expect(screen.getByText(/expired/i)).toBeInTheDocument();
  });

  it('displays error message when action fails', async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn().mockRejectedValue(new Error('Action expired or invalid'));

    render(
      <ActionCard
        action={mockPendingAction}
        onConfirm={onConfirm}
        onCancel={vi.fn()}
      />
    );

    const confirmBtn = screen.getByRole('button', { name: /confirm/i });
    await user.click(confirmBtn);

    await waitFor(() => {
      expect(screen.getByText(/Action expired or invalid/i)).toBeInTheDocument();
    });
  });
});
