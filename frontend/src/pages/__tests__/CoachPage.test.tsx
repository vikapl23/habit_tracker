import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { CoachPage } from '../CoachPage';
import { AuthProvider } from '../../context/AuthContext';
import { coachApi } from '../../api/coach';
import { CoachMessagesResponse, SendMessageResponse } from '../../types/coach';

const mockEmptyResponse: CoachMessagesResponse = {
  remaining_messages: 20,
  daily_limit: 20,
  results: [],
};

const mockHistoryResponse: CoachMessagesResponse = {
  remaining_messages: 18,
  daily_limit: 20,
  results: [
    {
      id: 1,
      role: 'user',
      content: 'How do I start running?',
      created_at: '2026-10-28T09:00:00Z',
    },
    {
      id: 2,
      role: 'assistant',
      content: 'Start with 10 minutes of light jogging three times a week!',
      created_at: '2026-10-28T09:00:02Z',
    },
  ],
};

const renderCoachPage = () => {
  return render(
    <MemoryRouter
      initialEntries={['/coach']}
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <AuthProvider>
        <Routes>
          <Route path="/coach" element={<CoachPage />} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>
  );
};

describe('CoachPage (Step 10.4)', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('renders loading state initially', () => {
    vi.spyOn(coachApi, 'getMessages').mockReturnValue(new Promise(() => {}));
    renderCoachPage();
    expect(screen.getByTestId('coach-loading')).toBeInTheDocument();
  });

  it('renders empty state with welcome message and starter questions', async () => {
    vi.spyOn(coachApi, 'getMessages').mockResolvedValue(mockEmptyResponse);
    renderCoachPage();

    await waitFor(() => {
      expect(screen.queryByTestId('coach-loading')).not.toBeInTheDocument();
    });

    expect(
      screen.getByRole('heading', { name: /AI Habit Coach/i, level: 1 })
    ).toBeInTheDocument();
    expect(screen.getByText(/20 \/ 20 left today/i)).toBeInTheDocument();
    expect(screen.getByText(/How am I doing this week\?/i)).toBeInTheDocument();
    expect(screen.getByText(/Help me build a morning routine/i)).toBeInTheDocument();
  });

  it('renders existing conversation messages', async () => {
    vi.spyOn(coachApi, 'getMessages').mockResolvedValue(mockHistoryResponse);
    renderCoachPage();

    await waitFor(() => {
      expect(screen.getByText('How do I start running?')).toBeInTheDocument();
    });

    expect(
      screen.getByText('Start with 10 minutes of light jogging three times a week!')
    ).toBeInTheDocument();
    expect(screen.getByText(/18 \/ 20 left today/i)).toBeInTheDocument();
  });

  it('sends message via starter question chip', async () => {
    const user = userEvent.setup();
    vi.spyOn(coachApi, 'getMessages').mockResolvedValue(mockEmptyResponse);
    const mockSendResponse: SendMessageResponse = {
      user_message: {
        id: 3,
        role: 'user',
        content: 'How am I doing this week?',
        created_at: '2026-10-28T09:05:00Z',
      },
      assistant_message: {
        id: 4,
        role: 'assistant',
        content: 'You completed 85% of your scheduled habits this week!',
        created_at: '2026-10-28T09:05:02Z',
      },
      remaining_messages: 19,
    };
    const sendSpy = vi.spyOn(coachApi, 'sendMessage').mockResolvedValue(mockSendResponse);

    renderCoachPage();

    await waitFor(() => {
      expect(screen.getByText(/How am I doing this week\?/i)).toBeInTheDocument();
    });

    const chip = screen.getByText(/How am I doing this week\?/i);
    await user.click(chip);

    expect(sendSpy).toHaveBeenCalledWith('How am I doing this week?');

    await waitFor(() => {
      expect(
        screen.getByText('You completed 85% of your scheduled habits this week!')
      ).toBeInTheDocument();
    });
    expect(screen.getByText(/19 \/ 20 left today/i)).toBeInTheDocument();
  });

  it('sends custom message typed into input field', async () => {
    const user = userEvent.setup();
    vi.spyOn(coachApi, 'getMessages').mockResolvedValue(mockEmptyResponse);
    const mockSendResponse: SendMessageResponse = {
      user_message: {
        id: 5,
        role: 'user',
        content: 'I want to drink more water',
        created_at: '2026-10-28T09:10:00Z',
      },
      assistant_message: {
        id: 6,
        role: 'assistant',
        content: 'Try keeping a 1L water bottle at your desk!',
        created_at: '2026-10-28T09:10:02Z',
      },
      remaining_messages: 19,
    };
    const sendSpy = vi.spyOn(coachApi, 'sendMessage').mockResolvedValue(mockSendResponse);

    renderCoachPage();

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Ask your coach/i)).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText(/Ask your coach/i);
    await user.type(input, 'I want to drink more water');

    const sendBtn = screen.getByTestId('coach-send-button');
    expect(sendBtn).not.toBeDisabled();
    await user.click(sendBtn);

    expect(sendSpy).toHaveBeenCalledWith('I want to drink more water');

    await waitFor(() => {
      expect(
        screen.getByText('Try keeping a 1L water bottle at your desk!')
      ).toBeInTheDocument();
    });
  });

  it('disables input when quota is exhausted', async () => {
    vi.spyOn(coachApi, 'getMessages').mockResolvedValue({
      remaining_messages: 0,
      daily_limit: 20,
      results: [],
    });

    renderCoachPage();

    await waitFor(() => {
      expect(screen.getByText(/Daily limit reached/i)).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText(/Daily limit reached/i);
    expect(input).toBeDisabled();
  });

  it('clears chat history after confirming modal', async () => {
    const user = userEvent.setup();
    vi.spyOn(coachApi, 'getMessages').mockResolvedValue(mockHistoryResponse);
    const clearSpy = vi.spyOn(coachApi, 'clearMessages').mockResolvedValue();

    renderCoachPage();

    await waitFor(() => {
      expect(screen.getByText('How do I start running?')).toBeInTheDocument();
    });

    const clearBtn = screen.getByTestId('coach-clear-button');
    await user.click(clearBtn);

    expect(screen.getByText(/Clear conversation\?/i)).toBeInTheDocument();

    const confirmBtn = screen.getByRole('button', { name: /Clear chat/i });
    await user.click(confirmBtn);

    expect(clearSpy).toHaveBeenCalled();

    await waitFor(() => {
      expect(screen.queryByText('How do I start running?')).not.toBeInTheDocument();
    });
  });

  describe('Action Cards (Step 10.5)', () => {
    const mockActionResponse: CoachMessagesResponse = {
      remaining_messages: 17,
      daily_limit: 20,
      results: [
        {
          id: 1,
          role: 'user',
          content: 'Create a meditation habit for me',
          created_at: '2026-10-28T09:00:00Z',
        },
        {
          id: 2,
          role: 'assistant',
          content: "I've proposed a daily meditation habit for you. Please confirm below!",
          pending_action: {
            id: 10,
            action_type: 'create_habit',
            summary: 'Create habit: Meditation, 5 minutes, daily, reminder 08:00',
            status: 'pending',
            expires_at: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
          },
          created_at: '2026-10-28T09:00:03Z',
        },
      ],
    };

    it('renders pending action card inside assistant message', async () => {
      vi.spyOn(coachApi, 'getMessages').mockResolvedValue(mockActionResponse);

      renderCoachPage();

      await waitFor(() => {
        expect(
          screen.getByText('Create habit: Meditation, 5 minutes, daily, reminder 08:00')
        ).toBeInTheDocument();
      });

      expect(screen.getByRole('button', { name: /confirm/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    });

    it('confirms action and updates status to confirmed', async () => {
      const user = userEvent.setup();
      vi.spyOn(coachApi, 'getMessages').mockResolvedValue(mockActionResponse);
      const confirmSpy = vi.spyOn(coachApi, 'confirmAction').mockResolvedValue({
        status: 'confirmed',
        action_id: 10,
        action_type: 'create_habit',
        result: { habit_id: 42, name: 'Meditation' },
      });

      renderCoachPage();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /confirm/i })).toBeInTheDocument();
      });

      const confirmBtn = screen.getByRole('button', { name: /confirm/i });
      await user.click(confirmBtn);

      expect(confirmSpy).toHaveBeenCalledWith(10);

      await waitFor(() => {
        expect(screen.queryByRole('button', { name: /confirm/i })).not.toBeInTheDocument();
        expect(screen.getByText(/confirmed/i)).toBeInTheDocument();
      });
    });

    it('cancels action and updates status to cancelled', async () => {
      const user = userEvent.setup();
      vi.spyOn(coachApi, 'getMessages').mockResolvedValue(mockActionResponse);
      const cancelSpy = vi.spyOn(coachApi, 'cancelAction').mockResolvedValue({
        status: 'cancelled',
        action_id: 10,
      });

      renderCoachPage();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
      });

      const cancelBtn = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelBtn);

      expect(cancelSpy).toHaveBeenCalledWith(10);

      await waitFor(() => {
        expect(screen.queryByRole('button', { name: /cancel/i })).not.toBeInTheDocument();
        expect(screen.getByText(/cancelled/i)).toBeInTheDocument();
      });
    });
  });
});
