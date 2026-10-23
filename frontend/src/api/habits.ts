import { apiClient } from './client';
import { Habit, CheckInResponse, PaginatedResponse } from '../types/habit';

export const getAllHabits = async (): Promise<Habit[]> => {
  const allHabits: Habit[] = [];
  let page = 1;
  let hasMore = true;

  while (hasMore) {
    const res = await apiClient.get<PaginatedResponse<Habit> | Habit[]>(`/habits/?page=${page}`);
    if (Array.isArray(res)) {
      return res;
    }
    if (res && Array.isArray(res.results)) {
      allHabits.push(...res.results);
      if (res.next) {
        page += 1;
      } else {
        hasMore = false;
      }
    } else {
      hasMore = false;
    }
  }

  return allHabits;
};

export const checkHabit = async (id: number, date?: string): Promise<CheckInResponse> => {
  return apiClient.post<CheckInResponse>(`/habits/${id}/check/`, date ? { date } : {});
};

export const uncheckHabit = async (id: number, date?: string): Promise<CheckInResponse> => {
  return apiClient.post<CheckInResponse>(`/habits/${id}/uncheck/`, date ? { date } : {});
};

export const habitsApi = {
  getAllHabits,
  checkHabit,
  uncheckHabit,
};
