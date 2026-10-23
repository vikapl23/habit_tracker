import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  Flame,
  Sparkles,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  RefreshCw,
  PlusCircle,
  Plus,
} from 'lucide-react';
import { Habit, HabitFormData } from '../types/habit';
import { habitsApi } from '../api/habits';
import { HabitCard } from '../components/HabitCard';
import { HabitFormBottomSheet } from '../components/HabitFormBottomSheet';
import { DeleteConfirmDialog } from '../components/DeleteConfirmDialog';
import { Toast, ToastMessage } from '../components/Toast';
import { DashboardSkeleton } from '../components/DashboardSkeleton';
import { BottomNavigation } from '../components/BottomNavigation';

interface DashboardPageProps {
  onCreateHabit?: () => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ onCreateHabit }) => {
  const { user } = useAuth();

  const [habits, setHabits] = useState<Habit[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [isNotTodayExpanded, setIsNotTodayExpanded] = useState(false);
  const [pendingHabitIds, setPendingHabitIds] = useState<Set<number>>(new Set());
  const [toast, setToast] = useState<ToastMessage | null>(null);

  // Bottom Sheet Form State
  const [isSheetOpen, setIsSheetOpen] = useState(false);
  const [editingHabit, setEditingHabit] = useState<Habit | null>(null);

  // Delete Confirmation Dialog State
  const [deletingHabit, setDeletingHabit] = useState<Habit | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const loadHabits = useCallback(async () => {
    setIsLoading(true);
    setFetchError(null);
    try {
      const data = await habitsApi.getAllHabits();
      setHabits(data);
    } catch (err: any) {
      setFetchError(err?.message || 'Failed to load habits. Please check your connection.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHabits();
  }, [loadHabits]);

  const handleToggleHabit = async (habit: Habit) => {
    if (pendingHabitIds.has(habit.id)) return;

    const previousHabits = habits;
    const isNowChecked = !habit.is_checked_today;
    const newCurrentStreak = isNowChecked
      ? habit.current_streak + 1
      : Math.max(0, habit.current_streak - 1);
    const newLongestStreak = Math.max(habit.longest_streak, newCurrentStreak);

    // Optimistic update
    setHabits((prev) =>
      prev.map((h) =>
        h.id === habit.id
          ? {
              ...h,
              is_checked_today: isNowChecked,
              current_streak: newCurrentStreak,
              longest_streak: newLongestStreak,
            }
          : h
      )
    );

    setPendingHabitIds((prev) => new Set(prev).add(habit.id));

    try {
      const res = isNowChecked
        ? await habitsApi.checkHabit(habit.id)
        : await habitsApi.uncheckHabit(habit.id);

      // Confirm with exact server values
      setHabits((prev) =>
        prev.map((h) =>
          h.id === habit.id
            ? {
                ...h,
                current_streak: res.current_streak,
                longest_streak: res.longest_streak,
              }
            : h
        )
      );
    } catch (err: any) {
      // Rollback to previous habits state
      setHabits(previousHabits);
      const errorMsg =
        err?.data?.detail || err?.message || 'Failed to update habit. Please try again.';
      setToast({
        id: String(Date.now()),
        type: 'error',
        message: errorMsg,
      });
    } finally {
      setPendingHabitIds((prev) => {
        const next = new Set(prev);
        next.delete(habit.id);
        return next;
      });
    }
  };

  const todayFormatted = useMemo(() => {
    try {
      return new Intl.DateTimeFormat('en-US', {
        weekday: 'long',
        month: 'short',
        day: 'numeric',
        ...(user?.timezone ? { timeZone: user.timezone } : {}),
      }).format(new Date());
    } catch {
      return new Intl.DateTimeFormat('en-US', {
        weekday: 'long',
        month: 'short',
        day: 'numeric',
      }).format(new Date());
    }
  }, [user?.timezone]);

  // Habit grouping & stats
  const scheduledTodayHabits = useMemo(
    () => habits.filter((h) => h.is_scheduled_today),
    [habits]
  );

  const notTodayHabits = useMemo(
    () => habits.filter((h) => !h.is_scheduled_today),
    [habits]
  );

  const totalScheduled = scheduledTodayHabits.length;
  const completedScheduled = useMemo(
    () => scheduledTodayHabits.filter((h) => h.is_checked_today).length,
    [scheduledTodayHabits]
  );

  const progressPercent = totalScheduled > 0 ? Math.round((completedScheduled / totalScheduled) * 100) : 0;

  // Best current streak across all active habits
  const bestCurrentStreak = useMemo(
    () => (habits.length > 0 ? Math.max(...habits.map((h) => h.current_streak), 0) : 0),
    [habits]
  );

  const handleCreateHabitClick = () => {
    if (onCreateHabit) {
      onCreateHabit();
    } else {
      setEditingHabit(null);
      setIsSheetOpen(true);
    }
  };

  const handleEditHabitClick = (habit: Habit) => {
    setEditingHabit(habit);
    setIsSheetOpen(true);
  };

  const handleFormSubmit = async (data: HabitFormData) => {
    if (editingHabit) {
      const updated = await habitsApi.updateHabit(editingHabit.id, data);
      setHabits((prev) => prev.map((h) => (h.id === updated.id ? updated : h)));
      setToast({
        id: String(Date.now()),
        type: 'success',
        message: `Habit "${updated.name}" updated successfully.`,
      });
    } else {
      const created = await habitsApi.createHabit(data);
      setHabits((prev) => [created, ...prev]);
      setToast({
        id: String(Date.now()),
        type: 'success',
        message: `Habit "${created.name}" created!`,
      });
    }
  };

  const handleArchiveHabitClick = async (habit: Habit) => {
    try {
      await habitsApi.archiveHabit(habit.id);
      setHabits((prev) => prev.filter((h) => h.id !== habit.id));
      setToast({
        id: String(Date.now()),
        type: 'info',
        message: `Habit "${habit.name}" archived.`,
      });
    } catch (err: any) {
      setToast({
        id: String(Date.now()),
        type: 'error',
        message: err?.data?.detail || err?.message || 'Failed to archive habit.',
      });
    }
  };

  const handleDeleteHabitClick = (habit: Habit) => {
    setDeletingHabit(habit);
  };

  const handleConfirmDelete = async () => {
    if (!deletingHabit) return;
    setIsDeleting(true);
    try {
      await habitsApi.deleteHabit(deletingHabit.id);
      setHabits((prev) => prev.filter((h) => h.id !== deletingHabit.id));
      setToast({
        id: String(Date.now()),
        type: 'success',
        message: `Habit "${deletingHabit.name}" deleted.`,
      });
      setDeletingHabit(null);
    } catch (err: any) {
      setToast({
        id: String(Date.now()),
        type: 'error',
        message: err?.data?.detail || err?.message || 'Failed to delete habit.',
      });
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center">
      {/* Toast Notification Container */}
      <Toast toast={toast} onDismiss={() => setToast(null)} />

      {/* Mobile-first Container (responsive max-w-[420px], no horizontal scroll at 320px) */}
      <div className="w-full max-w-[420px] min-h-screen flex flex-col bg-white shadow-sm border-x border-slate-100 overflow-x-hidden">
        {/* Top App Header */}
        <header className="px-5 py-4 border-b border-slate-100 flex items-center justify-between sticky top-0 bg-white/95 backdrop-blur z-10">
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-2xl select-none shrink-0" role="img" aria-label="Target">🎯</span>
            <div className="min-w-0">
              <h1 className="text-base font-bold text-slate-900 leading-tight truncate">Habit Tracker</h1>
              <p className="text-[11px] text-slate-500 truncate max-w-[200px]" title={user?.email}>
                {user?.email}
              </p>
            </div>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="flex-1 p-4 sm:p-5 pb-28 sm:pb-8 space-y-5">
          {isLoading ? (
            <DashboardSkeleton />
          ) : fetchError ? (
            /* Backend Unreachable / Fetch Error State */
            <div className="rounded-2xl border border-red-200 bg-red-50/70 p-6 text-center space-y-3" role="alert">
              <div className="w-12 h-12 rounded-full bg-red-100 text-red-600 flex items-center justify-center mx-auto">
                <AlertCircle className="w-6 h-6" />
              </div>
              <h2 className="text-base font-bold text-slate-900">Unable to load habits</h2>
              <p className="text-xs text-slate-600 max-w-xs mx-auto leading-relaxed">
                {fetchError}
              </p>
              <button
                type="button"
                onClick={loadHabits}
                className="min-h-[44px] inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 active:bg-blue-800 transition shadow-sm"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Retry</span>
              </button>
            </div>
          ) : habits.length === 0 ? (
            /* Empty State: No active habits exist */
            <div className="rounded-2xl border-2 border-dashed border-slate-200 p-8 text-center space-y-4">
              <div className="w-14 h-14 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto text-2xl shadow-sm">
                <Sparkles className="w-7 h-7" />
              </div>
              <div className="space-y-1">
                <h2 className="text-base font-bold text-slate-900">No habits yet</h2>
                <p className="text-xs text-slate-500 max-w-[260px] mx-auto leading-relaxed">
                  Start building momentum! Create your first habit to track daily routines and streaks.
                </p>
              </div>
              <button
                type="button"
                onClick={handleCreateHabitClick}
                className="min-h-[44px] w-full max-w-[240px] inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 active:bg-blue-800 transition shadow-sm mx-auto"
              >
                <PlusCircle className="w-4 h-4" />
                <span>Create your first habit</span>
              </button>
            </div>
          ) : (
            <>
              {/* Daily Progress Banner */}
              <div className="rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-600 p-5 text-white shadow-sm space-y-3">
                <div className="flex items-center justify-between text-xs text-blue-100 font-medium">
                  <span>{todayFormatted}</span>
                  <span className="font-semibold text-white bg-white/20 backdrop-blur px-2.5 py-0.5 rounded-full">
                    {completedScheduled} of {totalScheduled} done today
                  </span>
                </div>

                <div>
                  <h2 className="text-xl font-bold tracking-tight">
                    {totalScheduled === 0
                      ? 'No habits scheduled today'
                      : completedScheduled === totalScheduled
                      ? 'All done for today! 🎉'
                      : 'Keep up the momentum!'}
                  </h2>
                </div>

                {/* Accessible Progress Bar */}
                <div className="space-y-1.5 pt-1">
                  <div
                    className="w-full h-2.5 bg-blue-950/30 rounded-full overflow-hidden"
                    role="progressbar"
                    aria-valuenow={completedScheduled}
                    aria-valuemin={0}
                    aria-valuemax={totalScheduled}
                    aria-label="Today's habit completion progress"
                  >
                    <div
                      className="h-full bg-white rounded-full transition-all duration-300 ease-out"
                      style={{ width: `${progressPercent}%` }}
                    />
                  </div>
                  <div className="flex justify-between items-center text-[11px] text-blue-100">
                    <span>Daily Progress</span>
                    <span className="font-semibold">{progressPercent}%</span>
                  </div>
                </div>
              </div>

              {/* Summary Stats Row */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3.5 sm:p-4 rounded-xl bg-slate-50 border border-slate-100">
                  <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
                    <Flame className="h-4 w-4 text-orange-500" /> Current Streak
                  </div>
                  <p className="mt-2 text-2xl font-bold text-slate-800">
                    {bestCurrentStreak} <span className="text-xs font-normal text-slate-500">days</span>
                  </p>
                  <p className="text-[10px] text-slate-400 mt-0.5 truncate">Best active streak</p>
                </div>

                <div className="p-3.5 sm:p-4 rounded-xl bg-slate-50 border border-slate-100">
                  <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
                    <span className="text-sm">🎯</span> Completed Today
                  </div>
                  <p className="mt-2 text-2xl font-bold text-slate-800">
                    {completedScheduled} <span className="text-xs font-normal text-slate-500">/ {totalScheduled}</span>
                  </p>
                  <p className="text-[10px] text-slate-400 mt-0.5 truncate">Scheduled habits</p>
                </div>
              </div>

              {/* "Today" Section */}
              <section className="space-y-3" aria-labelledby="today-heading">
                <div className="flex items-center justify-between">
                  <h2 id="today-heading" className="text-sm font-bold text-slate-900 tracking-tight">
                    Today
                  </h2>
                  <span className="text-xs text-slate-500 font-medium">
                    {completedScheduled} of {totalScheduled} completed
                  </span>
                </div>

                {scheduledTodayHabits.length === 0 ? (
                  <div className="p-5 rounded-2xl border border-slate-100 bg-slate-50/50 text-center text-xs text-slate-500">
                    No habits scheduled for today.
                  </div>
                ) : (
                  <div className="space-y-2.5">
                    {scheduledTodayHabits.map((habit) => (
                      <HabitCard
                        key={habit.id}
                        habit={habit}
                        onToggle={handleToggleHabit}
                        onEdit={handleEditHabitClick}
                        onArchive={handleArchiveHabitClick}
                        onDelete={handleDeleteHabitClick}
                        disabled={pendingHabitIds.has(habit.id)}
                      />
                    ))}
                  </div>
                )}
              </section>

              {/* "Not today" Collapsible Section */}
              {notTodayHabits.length > 0 && (
                <section className="pt-2 border-t border-slate-100 space-y-3" aria-labelledby="not-today-heading">
                  <button
                    type="button"
                    onClick={() => setIsNotTodayExpanded(!isNotTodayExpanded)}
                    aria-expanded={isNotTodayExpanded}
                    aria-controls="not-today-list"
                    className="w-full min-h-[44px] flex items-center justify-between py-2 text-left text-slate-600 hover:text-slate-900 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded-lg px-1"
                  >
                    <div className="flex items-center gap-2">
                      <span id="not-today-heading" className="text-xs font-bold uppercase tracking-wider text-slate-500">
                        Not today
                      </span>
                      <span className="px-1.5 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-600">
                        {notTodayHabits.length}
                      </span>
                    </div>

                    <div className="flex items-center gap-1 text-xs text-slate-400">
                      <span>{isNotTodayExpanded ? 'Hide' : 'Show'}</span>
                      {isNotTodayExpanded ? (
                        <ChevronUp className="w-4 h-4" />
                      ) : (
                        <ChevronDown className="w-4 h-4" />
                      )}
                    </div>
                  </button>

                  {isNotTodayExpanded && (
                    <div id="not-today-list" className="space-y-2.5 animate-in fade-in duration-200">
                      {notTodayHabits.map((habit) => (
                        <HabitCard
                          key={habit.id}
                          habit={habit}
                          onToggle={handleToggleHabit}
                          onEdit={handleEditHabitClick}
                          onArchive={handleArchiveHabitClick}
                          onDelete={handleDeleteHabitClick}
                          disabled={pendingHabitIds.has(habit.id)}
                        />
                      ))}
                    </div>
                  )}
                </section>
              )}
            </>
          )}
        </main>

        {/* Floating Action Button (FAB) for New Habit - positioned above bottom navigation */}
        <div className="fixed bottom-20 right-6 z-20 sm:static sm:bottom-auto sm:right-auto sm:p-5 sm:pt-0">
          <button
            type="button"
            onClick={handleCreateHabitClick}
            aria-label="New habit"
            className="w-14 h-14 rounded-full bg-blue-600 hover:bg-blue-700 active:scale-95 text-white shadow-lg flex items-center justify-center transition-all focus:outline-none focus-visible:ring-4 focus-visible:ring-blue-400"
          >
            <Plus className="w-7 h-7 stroke-[2.5]" />
          </button>
        </div>

        {/* Bottom Navigation */}
        <BottomNavigation />

        {/* New / Edit Habit Bottom Sheet */}
        <HabitFormBottomSheet
          isOpen={isSheetOpen}
          habit={editingHabit}
          onClose={() => {
            setIsSheetOpen(false);
            setEditingHabit(null);
          }}
          onSubmit={handleFormSubmit}
        />

        {/* Delete Habit Confirmation Dialog */}
        <DeleteConfirmDialog
          isOpen={!!deletingHabit}
          habitName={deletingHabit?.name || ''}
          isDeleting={isDeleting}
          onConfirm={handleConfirmDelete}
          onCancel={() => setDeletingHabit(null)}
        />
      </div>
    </div>
  );
};
