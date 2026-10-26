import { apiClient, RequestOptions } from './client';
import {
  Habit,
  HabitFormData,
  CheckInResponse,
  CheckInRecord,
  ArchiveResponse,
  PaginatedResponse,
  HabitStatistics,
  StatisticsSummary,
} from '../types/habit';

export const getAllHabits = async (includeArchived = false): Promise<Habit[]> => {
  const allHabits: Habit[] = [];
  let page = 1;
  let hasMore = true;

  while (hasMore) {
    const query = new URLSearchParams({
      page: String(page),
      ...(includeArchived ? { include_archived: 'true' } : {}),
    });
    const res = await apiClient.get<PaginatedResponse<Habit> | Habit[]>(`/habits/?${query.toString()}`);
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

export const createHabit = async (data: HabitFormData): Promise<Habit> => {
  return apiClient.post<Habit>('/habits/', data);
};

export const updateHabit = async (id: number, data: Partial<HabitFormData>): Promise<Habit> => {
  return apiClient.patch<Habit>(`/habits/${id}/`, data);
};

export const deleteHabit = async (id: number): Promise<void> => {
  return apiClient.delete<void>(`/habits/${id}/`);
};

export const archiveHabit = async (id: number): Promise<ArchiveResponse> => {
  return apiClient.post<ArchiveResponse>(`/habits/${id}/archive/`, {});
};

export const unarchiveHabit = async (id: number): Promise<ArchiveResponse> => {
  return apiClient.post<ArchiveResponse>(`/habits/${id}/unarchive/`, {});
};

export const checkHabit = async (id: number, date?: string): Promise<CheckInResponse> => {
  return apiClient.post<CheckInResponse>(`/habits/${id}/check/`, date ? { date } : {});
};

export const uncheckHabit = async (id: number, date?: string): Promise<CheckInResponse> => {
  return apiClient.post<CheckInResponse>(`/habits/${id}/uncheck/`, date ? { date } : {});
};

export const getHabit = async (id: number): Promise<Habit> => {
  return apiClient.get<Habit>(`/habits/${id}/`);
};

export const getHabitStatistics = async (id: number): Promise<HabitStatistics> => {
  return apiClient.get<HabitStatistics>(`/habits/${id}/statistics/`);
};

export const getStatisticsSummary = async (): Promise<StatisticsSummary> => {
  return apiClient.get<StatisticsSummary>('/statistics/summary/');
};

export const getHabitCheckIns = async (
  id: number,
  from?: string,
  to?: string,
  options?: RequestOptions
): Promise<CheckInRecord[]> => {
  const allCheckIns: CheckInRecord[] = [];
  let page = 1;
  let hasMore = true;

  while (hasMore) {
    const query = new URLSearchParams({
      page: String(page),
      ...(from ? { from } : {}),
      ...(to ? { to } : {}),
    });
    const res = options
      ? await apiClient.get<PaginatedResponse<CheckInRecord> | CheckInRecord[]>(
          `/habits/${id}/check-ins/?${query.toString()}`,
          options
        )
      : await apiClient.get<PaginatedResponse<CheckInRecord> | CheckInRecord[]>(
          `/habits/${id}/check-ins/?${query.toString()}`
        );
    if (Array.isArray(res)) {
      return res;
    }
    if (res && Array.isArray(res.results)) {
      allCheckIns.push(...res.results);
      if (res.next) {
        page += 1;
      } else {
        hasMore = false;
      }
    } else {
      hasMore = false;
    }
  }

  return allCheckIns;
};

export const habitsApi = {
  getAllHabits,
  getHabit,
  getHabitStatistics,
  getStatisticsSummary,
  getHabitCheckIns,
  createHabit,
  updateHabit,
  deleteHabit,
  archiveHabit,
  unarchiveHabit,
  checkHabit,
  uncheckHabit,
};
