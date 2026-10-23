import { describe, it, expect, vi, beforeEach } from 'vitest';
import { getAllHabits, checkHabit, uncheckHabit, habitsApi } from '../habits';
import { apiClient } from '../client';
import { Habit } from '../../types/habit';

const mockHabit = (id: number, name: string, isScheduledToday = true): Habit => ({
  id,
  name,
  description: 'Test Description',
  color: '#3B82F6',
  emoji: '💧',
  is_archived: false,
  frequency_type: 'daily',
  frequency_days: [],
  current_streak: 5,
  longest_streak: 10,
  is_checked_today: false,
  is_scheduled_today: isScheduledToday,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
});

describe('Habits API Service', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('getAllHabits pagination', () => {
    it('fetches all pages sequentially until next is null', async () => {
      const getSpy = vi.spyOn(apiClient, 'get')
        .mockResolvedValueOnce({
          count: 3,
          next: 'http://localhost:8000/api/v1/habits/?page=2',
          previous: null,
          results: [mockHabit(1, 'Habit 1'), mockHabit(2, 'Habit 2')],
        })
        .mockResolvedValueOnce({
          count: 3,
          next: null,
          previous: 'http://localhost:8000/api/v1/habits/?page=1',
          results: [mockHabit(3, 'Habit 3')],
        });

      const habits = await getAllHabits();

      expect(getSpy).toHaveBeenCalledTimes(2);
      expect(getSpy).toHaveBeenNthCalledWith(1, '/habits/?page=1');
      expect(getSpy).toHaveBeenNthCalledWith(2, '/habits/?page=2');
      expect(habits).toHaveLength(3);
      expect(habits.map((h) => h.id)).toEqual([1, 2, 3]);
    });

    it('handles non-paginated array response gracefully', async () => {
      const mockList = [mockHabit(1, 'Single Habit')];
      vi.spyOn(apiClient, 'get').mockResolvedValueOnce(mockList);

      const habits = await getAllHabits();

      expect(habits).toEqual(mockList);
    });
  });

  describe('checkHabit and uncheckHabit', () => {
    it('calls POST /habits/{id}/check/', async () => {
      const postSpy = vi.spyOn(apiClient, 'post').mockResolvedValueOnce({
        status: 'created',
        habit_id: 1,
        date: '2026-10-23',
        current_streak: 6,
        longest_streak: 10,
      });

      const res = await checkHabit(1);

      expect(postSpy).toHaveBeenCalledWith('/habits/1/check/', {});
      expect(res.current_streak).toBe(6);
    });

    it('calls POST /habits/{id}/uncheck/', async () => {
      const postSpy = vi.spyOn(apiClient, 'post').mockResolvedValueOnce({
        status: 'removed',
        habit_id: 1,
        date: '2026-10-23',
        current_streak: 5,
        longest_streak: 10,
      });

      const res = await uncheckHabit(1);

      expect(postSpy).toHaveBeenCalledWith('/habits/1/uncheck/', {});
      expect(res.current_streak).toBe(5);
    });
  });

  describe('createHabit, updateHabit, deleteHabit, archiveHabit, unarchiveHabit', () => {
    it('calls POST /habits/ to create habit', async () => {
      const postSpy = vi.spyOn(apiClient, 'post').mockResolvedValueOnce(mockHabit(10, 'New'));
      await habitsApi.createHabit({
        name: 'New',
        color: '#3B82F6',
        emoji: '🎯',
        frequency_type: 'daily',
        frequency_days: [],
      });
      expect(postSpy).toHaveBeenCalledWith('/habits/', {
        name: 'New',
        color: '#3B82F6',
        emoji: '🎯',
        frequency_type: 'daily',
        frequency_days: [],
      });
    });

    it('calls PATCH /habits/{id}/ to update habit', async () => {
      const patchSpy = vi.spyOn(apiClient, 'patch').mockResolvedValueOnce(mockHabit(10, 'Updated'));
      await habitsApi.updateHabit(10, { name: 'Updated' });
      expect(patchSpy).toHaveBeenCalledWith('/habits/10/', { name: 'Updated' });
    });

    it('calls DELETE /habits/{id}/ to delete habit', async () => {
      const deleteSpy = vi.spyOn(apiClient, 'delete').mockResolvedValueOnce(undefined);
      await habitsApi.deleteHabit(10);
      expect(deleteSpy).toHaveBeenCalledWith('/habits/10/');
    });

    it('calls POST /habits/{id}/archive/ and unarchive/', async () => {
      const postSpy = vi
        .spyOn(apiClient, 'post')
        .mockResolvedValueOnce({ id: 10, is_archived: true })
        .mockResolvedValueOnce({ id: 10, is_archived: false });

      await habitsApi.archiveHabit(10);
      expect(postSpy).toHaveBeenNthCalledWith(1, '/habits/10/archive/', {});

      await habitsApi.unarchiveHabit(10);
      expect(postSpy).toHaveBeenNthCalledWith(2, '/habits/10/unarchive/', {});
    });
  });
});
