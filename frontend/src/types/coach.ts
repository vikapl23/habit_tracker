export interface PendingAction {
  id: number;
  action_type: string;
  summary: string;
  status: 'pending' | 'confirmed' | 'cancelled' | 'expired';
  expires_at: string;
  payload?: Record<string, unknown>;
}

export interface ChatMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  pending_action?: PendingAction | null;
  created_at: string;
}

export interface CoachMessagesResponse {
  remaining_messages: number;
  daily_limit: number;
  results: ChatMessage[];
}

export interface SendMessageResponse {
  user_message: ChatMessage;
  assistant_message: ChatMessage;
  remaining_messages: number;
}
