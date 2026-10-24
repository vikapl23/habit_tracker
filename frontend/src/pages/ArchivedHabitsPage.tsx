import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, ArchiveRestore, Sparkles, AlertCircle, RefreshCw } from 'lucide-react';
import { Habit } from '../types/habit';
import { habitsApi } from '../api/habits';
import { Toast, ToastMessage } from '../components/Toast';
import { BottomNavigation } from '../components/BottomNavigation';
import { getErrorMessage } from '../utils/errorUtils';

export const ArchivedHabitsPage: React.FC = () => {
  const navigate = useNavigate();
  const [habits, setHabits] = useState<Habit[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [unarchivingId, setUnarchivingId] = useState<number | null>(null);
  const [toast, setToast] = useState<ToastMessage | null>(null);

  const loadArchivedHabits = useCallback(async () => {
    setIsLoading(true);
    setFetchError(null);
    try {
      const all = await habitsApi.getAllHabits(true);
      const archivedOnly = all.filter((h) => h.is_archived);
      setHabits(archivedOnly);
    } catch (err: any) {
      setFetchError(getErrorMessage(err, 'Failed to load archived habits.'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadArchivedHabits();
  }, [loadArchivedHabits]);

  const handleUnarchive = async (habit: Habit) => {
    setUnarchivingId(habit.id);
    try {
      await habitsApi.unarchiveHabit(habit.id);
      setHabits((prev) => prev.filter((h) => h.id !== habit.id));
      setToast({
        id: String(Date.now()),
        type: 'success',
        message: `Habit "${habit.name}" restored to dashboard.`,
      });
    } catch (err: any) {
      setToast({
        id: String(Date.now()),
        type: 'error',
        message: err?.data?.detail || err?.message || 'Failed to unarchive habit.',
      });
    } finally {
      setUnarchivingId(null);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center">
      <Toast toast={toast} onDismiss={() => setToast(null)} />

      <div className="w-full max-w-[420px] min-h-screen flex flex-col bg-white shadow-sm border-x border-slate-100 overflow-x-hidden">
        {/* Header */}
        <header className="px-5 py-4 pt-[calc(1rem+env(safe-area-inset-top,0px))] border-b border-slate-100 flex items-center justify-between sticky top-0 bg-white/95 backdrop-blur z-10">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => navigate('/')}
              aria-label="Back to dashboard"
              className="min-w-[44px] min-h-[44px] -ml-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 active:bg-slate-200 transition flex items-center justify-center"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <h1 className="text-base font-bold text-slate-900 leading-tight">Archived Habits</h1>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 p-4 sm:p-5 pb-28 space-y-4">
          {isLoading ? (
            <div className="space-y-3 animate-pulse">
              <div className="h-16 bg-slate-100 rounded-2xl" />
              <div className="h-16 bg-slate-100 rounded-2xl" />
            </div>
          ) : fetchError ? (
            <div className="rounded-2xl border border-red-200 bg-red-50/70 p-6 text-center space-y-3">
              <div className="w-12 h-12 rounded-full bg-red-100 text-red-600 flex items-center justify-center mx-auto">
                <AlertCircle className="w-6 h-6" />
              </div>
              <h2 className="text-base font-bold text-slate-900">Unable to load archived habits</h2>
              <p className="text-xs text-slate-600">{fetchError}</p>
              <button
                type="button"
                onClick={loadArchivedHabits}
                className="min-h-[44px] inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 active:bg-blue-800 transition"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Retry</span>
              </button>
            </div>
          ) : habits.length === 0 ? (
            <div className="rounded-2xl border-2 border-dashed border-slate-200 p-8 text-center space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
                <Sparkles className="w-6 h-6" />
              </div>
              <h2 className="text-sm font-bold text-slate-800">No archived habits</h2>
              <p className="text-xs text-slate-500 max-w-[240px] mx-auto leading-relaxed">
                Habits that you archive will appear here. You can unarchive them anytime.
              </p>
            </div>
          ) : (
            <div className="space-y-2.5">
              {habits.map((habit) => {
                const accentColor = habit.color || '#3B82F6';
                const isBusy = unarchivingId === habit.id;

                return (
                  <div
                    key={habit.id}
                    className="p-3.5 rounded-2xl border border-slate-200 bg-white flex items-center justify-between gap-3 shadow-sm"
                    style={{
                      borderLeftWidth: '5px',
                      borderLeftColor: accentColor,
                    }}
                  >
                    <div className="flex items-center gap-3 min-w-0 flex-1">
                      <div
                        className="w-10 h-10 rounded-xl flex items-center justify-center text-xl shrink-0"
                        style={{ backgroundColor: `${accentColor}18` }}
                        aria-hidden="true"
                      >
                        {habit.emoji || '🎯'}
                      </div>
                      <div className="min-w-0 flex-1">
                        <h3 className="text-sm font-semibold text-slate-800 truncate">
                          {habit.name}
                        </h3>
                        <p className="text-[11px] text-slate-400 mt-0.5">
                          Streak: {habit.current_streak}d (best {habit.longest_streak}d)
                        </p>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => handleUnarchive(habit)}
                      disabled={isBusy}
                      aria-label={`Unarchive ${habit.name}`}
                      className="min-h-[44px] px-3 rounded-xl bg-slate-100 hover:bg-slate-200 active:bg-slate-300 text-slate-700 text-xs font-semibold flex items-center gap-1.5 transition disabled:opacity-50 shrink-0"
                    >
                      {isBusy ? (
                        <div className="w-3.5 h-3.5 rounded-full border-2 border-slate-500 border-t-transparent animate-spin" />
                      ) : (
                        <>
                          <ArchiveRestore className="w-4 h-4 text-slate-600" />
                          <span>Unarchive</span>
                        </>
                      )}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </main>

        {/* Bottom Navigation */}
        <BottomNavigation />
      </div>
    </div>
  );
};
