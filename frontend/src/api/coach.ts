import { apiClient } from './client';
import {
  CoachMessagesResponse,
  SendMessageResponse,
} from '../types/coach';

export interface ActionConfirmResponse {
  status: 'confirmed';
  action_id: number;
  action_type: string;
  result: Record<string, unknown>;
}

export interface ActionCancelResponse {
  status: 'cancelled';
  action_id: number;
}

export const coachApi = {
  getMessages: async (): Promise<CoachMessagesResponse> => {
    return apiClient.get<CoachMessagesResponse>('/coach/messages/');
  },

  sendMessage: async (content: string): Promise<SendMessageResponse> => {
    return apiClient.post<SendMessageResponse>('/coach/messages/', { content });
  },

  clearMessages: async (): Promise<void> => {
    return apiClient.delete<void>('/coach/messages/');
  },

  confirmAction: async (actionId: number): Promise<ActionConfirmResponse> => {
    return apiClient.post<ActionConfirmResponse>(`/coach/actions/${actionId}/confirm/`);
  },

  cancelAction: async (actionId: number): Promise<ActionCancelResponse> => {
    return apiClient.post<ActionCancelResponse>(`/coach/actions/${actionId}/cancel/`);
  },
};
