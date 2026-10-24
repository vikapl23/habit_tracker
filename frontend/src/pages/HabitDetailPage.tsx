import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, ChevronLeft, ChevronRight, Flame, Trophy, Check, Calendar, AlertCircle, RefreshCw } from 'lucide-react';
import { Habit } from '../types/habit';
import { habitsApi } from '../api/habits';
import { ApiError } from '../api/client';
import { getErrorMessage } from '../utils/errorUtils';
import { BottomNavigation } from '../components/BottomNavigation';
import { Toast, ToastMessage } from '../components/Toast';
import { useAuth } from '../context/AuthContext';

const pad = (n: number) => String(n).padStart(2, '0');

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export const HabitDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const habitId = Number(id);

  const [habit, setHabit] = useState<Habit | null>(null);
  const [isLoadingHabit, setIsLoadingHabit] = useState(true);
  const [habitError, setHabitError] = useState<string | null>(null);

  const [currentMonth, setCurrentMonth] = useState<Date>(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
  });
  const [checkInDates, setCheckInDates] = useState<Set<string>>(new Set());
  const [isLoadingCheckIns, setIsLoadingCheckIns] = useState(false);
  const [togglingDate, setTogglingDate] = useState<string | null>(null);
  const [toast, setToast] = useState<ToastMessage | null>(null);

  const [todayStr, setTodayStr] = useState<string>(() => {
    const tz = user?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
    try {
      return new Intl.DateTimeFormat('en-CA', { timeZone: tz }).format(new Date());
    } catch {
      const now = new Date();
      return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
    }
  });

  // I7: Refresh today string on visibilitychange / midnight
  useEffect(() => {
    const updateToday = () => {
      const tz = user?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
      try {
        setTodayStr(new Intl.DateTimeFormat('en-CA', { timeZone: tz }).format(new Date()));
      } catch {
        const now = new Date();
        setTodayStr(`${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`);
      }
    };

    document.addEventListener('visibilitychange', updateToday);
    return () => document.removeEventListener('visibilitychange', updateToday);
  }, [user?.timezone]);

  // I13: Validate habit ID
  const loadHabit = useCallback(async () => {
    if (isNaN(habitId) || habitId <= 0) {
      setIsLoadingHabit(false);
      setHabitError('Habit not found.');
      return;
    }
    setIsLoadingHabit(true);
    setHabitError(null);
    try {
      const data = await habitsApi.getHabit(habitId);
      setHabit(data);
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 404) {
        setHabitError('Habit not found.');
      } else {
        setHabitError(getErrorMessage(err, 'Failed to load habit details.'));
      }
    } finally {
      setIsLoadingHabit(false);
    }
  }, [habitId]);

  useEffect(() => {
    loadHabit();
  }, [loadHabit]);

  const [checkInsError, setCheckInsError] = useState<string | null>(null);

  // I6: Cancel overlapping requests with request counter
  const checkInsRequestSeq = useRef(0);

  const loadCheckIns = useCallback(async () => {
    if (isNaN(habitId) || habitId <= 0) return;
    const reqId = ++checkInsRequestSeq.current;
    const year = currentMonth.getFullYear();
    const month = currentMonth.getMonth();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const from = `${year}-${pad(month + 1)}-01`;
    const to = `${year}-${pad(month + 1)}-${pad(daysInMonth)}`;

    setIsLoadingCheckIns(true);
    setCheckInsError(null);
    try {
      const records = await habitsApi.getHabitCheckIns(habitId, from, to);
      // Ignore stale responses if a newer request was dispatched
      if (reqId !== checkInsRequestSeq.current) return;
      const set = new Set<string>();
      records.forEach((r) => {
        if (r.date) set.add(r.date);
      });
      setCheckInDates(set);
    } catch {
      if (reqId === checkInsRequestSeq.current) {
        // I12: Show inline error for check-ins with retry
        setCheckInsError('Unable to load check-ins for this month.');
      }
    } finally {
      if (reqId === checkInsRequestSeq.current) {
        setIsLoadingCheckIns(false);
      }
    }
  }, [habitId, currentMonth]);

  useEffect(() => {
    loadCheckIns();
  }, [loadCheckIns]);

  const handlePrevMonth = () => {
    setCurrentMonth((prev) => new Date(prev.getFullYear(), prev.getMonth() - 1, 1));
  };

  const handleNextMonth = () => {
    setCurrentMonth((prev) => new Date(prev.getFullYear(), prev.getMonth() + 1, 1));
  };

  const handleToggleDay = async (dateStr: string) => {
    if (!habit || togglingDate || dateStr > todayStr) return;

    const isCurrentlyChecked = checkInDates.has(dateStr);
    setTogglingDate(dateStr);

    // Optimistically update calendar
    setCheckInDates((prev) => {
      const next = new Set(prev);
      if (isCurrentlyChecked) {
        next.delete(dateStr);
      } else {
        next.add(dateStr);
      }
      return next;
    });

    try {
      let res;
      if (isCurrentlyChecked) {
        res = await habitsApi.uncheckHabit(habit.id, dateStr);
      } else {
        res = await habitsApi.checkHabit(habit.id, dateStr);
      }

      setHabit((prev) =>
        prev
          ? {
              ...prev,
              current_streak: res.current_streak,
              longest_streak: res.longest_streak,
              is_checked_today:
                dateStr === todayStr ? !isCurrentlyChecked : prev.is_checked_today,
            }
          : null
      );
    } catch (err: any) {
      // Revert optimistic update
      setCheckInDates((prev) => {
        const next = new Set(prev);
        if (isCurrentlyChecked) {
          next.add(dateStr);
        } else {
          next.delete(dateStr);
        }
        return next;
      });
      setToast({
        id: String(Date.now()),
        type: 'error',
        message: err?.data?.detail || err?.message || 'Failed to update check-in.',
      });
    } finally {
      setTogglingDate(null);
    }
  };

  // Calendar calculations
  const year = currentMonth.getFullYear();
  const month = currentMonth.getMonth();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const firstDayWeekday = (new Date(year, month, 1).getDay() + 6) % 7; // 0=Mon, 6=Sun

  const monthTitle = currentMonth.toLocaleDateString('en-US', {
    month: 'long',
    year: 'numeric',
  });

  const habitColor = habit?.color || '#3B82F6';

  const daysArray = useMemo(() => {
    return Array.from({ length: daysInMonth }, (_, i) => i + 1);
  }, [daysInMonth]);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center">
      <Toast toast={toast} onDismiss={() => setToast(null)} />

      <div className="w-full max-w-[420px] min-h-screen flex flex-col bg-white shadow-sm border-x border-slate-100 overflow-x-hidden relative">
        {/* Header */}
        <header className="px-5 py-4 pt-[calc(1rem+env(safe-area-inset-top,0px))] border-b border-slate-100 flex items-center justify-between sticky top-0 bg-white/95 backdrop-blur z-10">
          <div className="flex items-center gap-3 min-w-0">
            <button
              type="button"
              onClick={() => navigate('/')}
              aria-label="Back to dashboard"
              className="min-w-[44px] min-h-[44px] -ml-2 rounded-xl text-slate-600 hover:text-slate-900 hover:bg-slate-100 active:bg-slate-200 transition flex items-center justify-center"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-xl shrink-0" aria-hidden="true">
                {habit?.emoji || '🎯'}
              </span>
              <h1 className="text-base font-bold text-slate-900 leading-tight truncate">
                {habit ? habit.name : 'Habit Details'}
              </h1>
            </div>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 p-4 sm:p-5 pb-28 space-y-5">
          {isLoadingHabit ? (
            <div className="space-y-4 animate-pulse">
              <div className="h-24 bg-slate-100 rounded-2xl" />
              <div className="grid grid-cols-2 gap-3">
                <div className="h-20 bg-slate-100 rounded-xl" />
                <div className="h-20 bg-slate-100 rounded-xl" />
              </div>
              <div className="h-64 bg-slate-100 rounded-2xl" />
            </div>
          ) : habitError ? (
            <div className="rounded-2xl border border-red-200 bg-red-50/70 p-6 text-center space-y-3" role="alert">
              <div className="w-12 h-12 rounded-full bg-red-100 text-red-600 flex items-center justify-center mx-auto">
                <AlertCircle className="w-6 h-6" />
              </div>
              <h2 className="text-base font-bold text-slate-900">Habit not found</h2>
              <p className="text-xs text-slate-600">{habitError}</p>
              <button
                type="button"
                onClick={loadHabit}
                className="min-h-[44px] inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 active:bg-blue-800 transition"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Retry</span>
              </button>
            </div>
          ) : habit ? (
            <>
              {/* Habit Summary Card */}
              <div
                className="rounded-2xl p-4 sm:p-5 border border-slate-200/80 shadow-sm space-y-2"
                style={{
                  borderLeftWidth: '5px',
                  borderLeftColor: habitColor,
                }}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span className="text-2xl">{habit.emoji || '🎯'}</span>
                    <h2 className="text-base font-bold text-slate-900 truncate">{habit.name}</h2>
                  </div>
                  <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 shrink-0">
                    {habit.frequency_type === 'daily'
                      ? 'Every day'
                      : `${habit.frequency_days.length} days/week`}
                  </span>
                </div>
                {habit.description && (
                  <p className="text-xs text-slate-500 leading-relaxed">{habit.description}</p>
                )}
              </div>

              {/* Streak Cards */}
              <div className="grid grid-cols-2 gap-3">
                <div
                  aria-label={`Current streak ${habit.current_streak} days`}
                  className="p-4 rounded-2xl bg-amber-50/80 border border-amber-200/60 shadow-sm"
                >
                  <div className="flex items-center gap-1.5 text-xs font-bold text-amber-800">
                    <Flame className="w-4 h-4 text-orange-500" />
                    <span>Current Streak</span>
                  </div>
                  <p className="mt-2 text-2xl font-extrabold text-amber-950">
                    {habit.current_streak} <span className="text-xs font-medium text-amber-700">days</span>
                  </p>
                  <p className="text-[10px] text-amber-700/80 mt-0.5">Consecutive completions</p>
                </div>

                <div
                  aria-label={`Longest streak ${habit.longest_streak} days`}
                  className="p-4 rounded-2xl bg-indigo-50/80 border border-indigo-200/60 shadow-sm"
                >
                  <div className="flex items-center gap-1.5 text-xs font-bold text-indigo-800">
                    <Trophy className="w-4 h-4 text-indigo-500" />
                    <span>Longest Streak</span>
                  </div>
                  <p className="mt-2 text-2xl font-extrabold text-indigo-950">
                    {habit.longest_streak} <span className="text-xs font-medium text-indigo-700">days</span>
                  </p>
                  <p className="text-[10px] text-indigo-700/80 mt-0.5">All-time record</p>
                </div>
              </div>

              {/* Month Calendar Section */}
              <section aria-labelledby="calendar-heading" className="rounded-2xl border border-slate-200/80 bg-white p-4 sm:p-5 shadow-sm space-y-4">
                {/* Calendar Header with Navigation */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-blue-600" />
                    <h2 id="calendar-heading" className="text-sm font-bold text-slate-900" aria-live="polite">
                      {monthTitle}
                    </h2>
                    {isLoadingCheckIns && (
                      <div
                        role="status"
                        aria-label="Loading check-ins"
                        className="w-3.5 h-3.5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"
                      />
                    )}
                  </div>

                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={handlePrevMonth}
                      aria-label="Previous month"
                      className="min-w-[44px] min-h-[44px] rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 active:bg-slate-200 transition flex items-center justify-center"
                    >
                      <ChevronLeft className="w-5 h-5" />
                    </button>
                    <button
                      type="button"
                      onClick={handleNextMonth}
                      aria-label="Next month"
                      className="min-w-[44px] min-h-[44px] rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 active:bg-slate-200 transition flex items-center justify-center"
                    >
                      <ChevronRight className="w-5 h-5" />
                    </button>
                  </div>
                </div>

                {checkInsError && (
                  <div
                    role="alert"
                    className="p-3 rounded-xl bg-red-50 text-red-700 text-xs flex items-center justify-between gap-2 border border-red-200"
                  >
                    <span>{checkInsError}</span>
                    <button
                      type="button"
                      onClick={() => loadCheckIns()}
                      className="px-2.5 py-1 rounded-lg bg-red-600 text-white text-[11px] font-semibold hover:bg-red-700 active:bg-red-800 transition"
                    >
                      Retry
                    </button>
                  </div>
                )}

                {/* Weekday Labels (Mon - Sun) */}
                <div className="grid grid-cols-7 gap-1 text-center">
                  {WEEKDAYS.map((wd) => (
                    <div key={wd} className="text-[11px] font-semibold text-slate-400 py-1">
                      {wd}
                    </div>
                  ))}
                </div>

                {/* Days Grid */}
                <div className="grid grid-cols-7 gap-1">
                  {/* Empty Offset Cells */}
                  {Array.from({ length: firstDayWeekday }).map((_, idx) => (
                    <div key={`offset-${idx}`} className="aspect-square" aria-hidden="true" />
                  ))}

                  {/* Days in Month */}
                  {daysArray.map((day) => {
                    const dateStr = `${year}-${pad(month + 1)}-${pad(day)}`;
                    const dayWeekday = (firstDayWeekday + day - 1) % 7;
                    const isScheduled =
                      habit.frequency_type === 'daily' ||
                      (Array.isArray(habit.frequency_days) &&
                        habit.frequency_days.includes(dayWeekday));
                    const isChecked = checkInDates.has(dateStr);
                    const isFuture = dateStr > todayStr;
                    const isToday = dateStr === todayStr;
                    const isToggling = togglingDate === dateStr;

                    let cellStyle: React.CSSProperties = {};
                    if (isChecked) {
                      cellStyle = {
                        backgroundColor: habitColor,
                        color: '#ffffff',
                      };
                    }

                    return (
                      <button
                        key={dateStr}
                        type="button"
                        onClick={() => handleToggleDay(dateStr)}
                        disabled={isFuture || isToggling}
                        aria-label={`${dateStr}, ${
                          isChecked ? 'completed' : 'incomplete'
                        }${!isScheduled ? ', not scheduled' : ''}${
                          isFuture ? ', disabled' : ''
                        }`}
                        aria-pressed={isChecked}
                        style={cellStyle}
                        className={`aspect-square min-h-[44px] flex flex-col items-center justify-center rounded-xl text-xs font-semibold transition-all select-none relative focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
                          isFuture
                            ? 'cursor-not-allowed opacity-30 text-slate-300 bg-slate-50/50'
                            : isChecked
                            ? 'shadow-sm active:scale-95 text-white'
                            : !isScheduled
                            ? 'opacity-40 text-slate-400 bg-slate-50/50 border border-dashed border-slate-200/60 hover:opacity-80 active:scale-95'
                            : 'bg-slate-50 border border-slate-200/90 text-slate-700 hover:bg-slate-100 hover:border-slate-300 active:scale-95'
                        } ${isToday ? 'ring-2 ring-blue-500 ring-offset-1' : ''}`}
                      >
                        <span className="leading-none">{day}</span>
                        {isChecked && (
                          <Check className="w-3 h-3 stroke-[3] mt-0.5 text-white shrink-0" />
                        )}
                      </button>
                    );
                  })}
                </div>

                {/* Calendar Legend */}
                <div className="flex items-center justify-between text-[11px] text-slate-500 pt-3 border-t border-slate-100 flex-wrap gap-2">
                  <div className="flex items-center gap-1.5">
                    <span
                      className="w-3 h-3 rounded-full inline-block"
                      style={{ backgroundColor: habitColor }}
                    />
                    <span>Completed</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="w-3 h-3 rounded-full inline-block border border-dashed border-slate-300 bg-slate-50/50 opacity-50" />
                    <span>Non-scheduled</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="w-3 h-3 rounded-full inline-block ring-2 ring-blue-500 ring-offset-1 bg-slate-100" />
                    <span>Today</span>
                  </div>
                </div>
              </section>
            </>
          ) : null}
        </main>

        {/* Bottom Navigation */}
        <BottomNavigation />
      </div>
    </div>
  );
};
