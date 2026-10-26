export type FrequencyType = 'daily' | 'custom';
export type HabitType = 'boolean' | 'measurable';

export interface Habit {
  id: number;
  name: string;
  description?: string;
  color: string;
  emoji: string;
  is_archived: boolean;
  frequency_type: FrequencyType;
  frequency_days: number[];
  habit_type: HabitType;
  unit?: string;
  target_value?: number | null;
  today_value: number;
  today_progress: number;
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
  habit_type?: HabitType;
  unit?: string;
  target_value?: number | null;
}

export interface CheckInOptions {
  date?: string;
  value?: number;
  mode?: 'add' | 'set';
}

export interface UncheckOptions {
  date?: string;
  value?: number;
}

export interface CheckInResponse {
  status: string;
  habit_id: number;
  date: string;
  today_value?: number;
  today_progress?: number;
  is_completed?: boolean;
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
  value?: number;
  created_at: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface HabitStatistics {
  habit_id: number;
  completion_rate_7d: number;
  completion_rate_30d: number;
  total_check_ins: number;
  current_streak: number;
  longest_streak: number;
}

export interface BestHabitSummary {
  id: number;
  name: string;
  emoji: string;
  color: string;
  completion_rate_30d: number;
}

export interface StatisticsSummary {
  overall_completion_rate_week: number;
  overall_completion_rate_month: number;
  best_habit: BestHabitSummary | null;
  total_active_habits: number;
  total_check_ins: number;
}

