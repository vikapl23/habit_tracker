export type FrequencyType = 'daily' | 'custom';

export interface Habit {
  id: number;
  name: string;
  description?: string;
  color: string;
  emoji: string;
  is_archived: boolean;
  frequency_type: FrequencyType;
  frequency_days: number[];
  current_streak: number;
  longest_streak: number;
  is_checked_today: boolean;
  is_scheduled_today: boolean;
  created_at: string;
  updated_at: string;
}

export interface HabitFormData {
  name: string;
  description?: string;
  color: string;
  emoji: string;
  frequency_type: FrequencyType;
  frequency_days: number[];
}

export interface CheckInResponse {
  status: string;
  habit_id: number;
  date: string;
  current_streak: number;
  longest_streak: number;
}

export interface ArchiveResponse {
  id: number;
  is_archived: boolean;
}

export interface CheckInRecord {
  id: number;
  date: string;
  created_at: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
