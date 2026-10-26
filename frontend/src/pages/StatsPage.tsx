import React, { useState, useEffect, useCallback } from 'react';
import { BarChart3, TrendingUp, Calendar, Trophy, Layers, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';
import { StatisticsSummary } from '../types/habit';
import { habitsApi } from '../api/habits';
import { getErrorMessage } from '../utils/errorUtils';
import { BottomNavigation } from '../components/BottomNavigation';
import { Link } from 'react-router-dom';

export const StatsPage: React.FC = () => {
  const [summary, setSummary] = useState<StatisticsSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadSummary = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await habitsApi.getStatisticsSummary();
      setSummary(data);
    } catch (err: unknown) {
      setError(getErrorMessage(err, 'Failed to load statistics summary.'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  const weekPercent = summary ? Math.round(summary.overall_completion_rate_week * 100) : 0;
  const monthPercent = summary ? Math.round(summary.overall_completion_rate_month * 100) : 0;

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center">
      <div className="w-full max-w-[420px] min-h-screen flex flex-col bg-white shadow-sm border-x border-slate-100 overflow-x-hidden relative">
        {/* Header */}
        <header className="px-5 py-4 pt-[calc(1rem+env(safe-area-inset-top,0px))] border-b border-slate-100 flex items-center justify-between sticky top-0 bg-white/95 backdrop-blur z-10">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
              <BarChart3 className="w-5 h-5" />
            </div>
            <h1 className="text-lg font-bold text-slate-900 tracking-tight">Statistics</h1>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 p-4 sm:p-5 pb-24 space-y-4">
          {isLoading ? (
            <div className="space-y-4 animate-pulse" data-testid="stats-loading-skeleton">
              <div className="grid grid-cols-2 gap-3">
                <div className="h-28 bg-slate-100 rounded-2xl" />
                <div className="h-28 bg-slate-100 rounded-2xl" />
              </div>
              <div className="h-28 bg-slate-100 rounded-2xl" />
              <div className="grid grid-cols-2 gap-3">
                <div className="h-24 bg-slate-100 rounded-2xl" />
                <div className="h-24 bg-slate-100 rounded-2xl" />
              </div>
            </div>
          ) : error ? (
            <div
              className="rounded-2xl border border-red-200 bg-red-50/70 p-6 text-center space-y-3"
              role="alert"
            >
              <div className="w-12 h-12 rounded-full bg-red-100 text-red-600 flex items-center justify-center mx-auto">
                <AlertCircle className="w-6 h-6" />
              </div>
              <h2 className="text-base font-bold text-slate-900">Failed to load statistics</h2>
              <p className="text-xs text-slate-600">{error}</p>
              <button
                type="button"
                onClick={loadSummary}
                className="min-h-[44px] inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 active:bg-blue-800 transition"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Retry</span>
              </button>
            </div>
          ) : summary ? (
            <>
              {/* Rate Cards: Week & Month */}
              <div className="grid grid-cols-2 gap-3">
                {/* Week Completion */}
                <div
                  aria-label={`This week completion ${weekPercent}%`}
                  className="p-4 rounded-2xl bg-gradient-to-br from-blue-50 to-indigo-50/40 border border-blue-100 shadow-sm"
                >
                  <div className="flex items-center gap-1.5 text-xs font-bold text-blue-800">
                    <TrendingUp className="w-4 h-4 text-blue-600" />
                    <span>This Week</span>
                  </div>
                  <p className="mt-2 text-2xl font-extrabold text-blue-950">
                    {weekPercent}<span className="text-sm font-semibold text-blue-700">%</span>
                  </p>
                  <p className="text-[10px] text-blue-600/80 mt-0.5">Scheduled completion</p>
                </div>

                {/* Month Completion */}
                <div
                  aria-label={`This month completion ${monthPercent}%`}
                  className="p-4 rounded-2xl bg-gradient-to-br from-emerald-50 to-teal-50/40 border border-emerald-100 shadow-sm"
                >
                  <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-800">
                    <Calendar className="w-4 h-4 text-emerald-600" />
                    <span>This Month</span>
                  </div>
                  <p className="mt-2 text-2xl font-extrabold text-emerald-950">
                    {monthPercent}<span className="text-sm font-semibold text-emerald-700">%</span>
                  </p>
                  <p className="text-[10px] text-emerald-600/80 mt-0.5">Scheduled completion</p>
                </div>
              </div>

              {/* Best Habit Card */}
              {summary.best_habit ? (
                <Link
                  to={`/habits/${summary.best_habit.id}`}
                  className="block rounded-2xl p-4 sm:p-5 border border-amber-200/70 bg-gradient-to-r from-amber-50/80 to-amber-100/30 shadow-sm transition hover:shadow-md active:scale-[0.99]"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs font-bold text-amber-900">
                      <Trophy className="w-4 h-4 text-amber-600" />
                      <span>Best Habit (Last 30 Days)</span>
                    </div>
                    <span className="text-xs font-extrabold text-amber-800 bg-amber-200/60 px-2 py-0.5 rounded-full">
                      {Math.round(summary.best_habit.completion_rate_30d * 100)}%
                    </span>
                  </div>
                  <div className="mt-3 flex items-center gap-3">
                    <span className="text-3xl shrink-0" aria-hidden="true">
                      {summary.best_habit.emoji}
                    </span>
                    <div className="min-w-0">
                      <h3 className="text-base font-bold text-slate-900 truncate">
                        {summary.best_habit.name}
                      </h3>
                      <p className="text-xs text-slate-500">Highest 30-day consistency</p>
                    </div>
                  </div>
                </Link>
              ) : (
                <div className="rounded-2xl p-4 sm:p-5 border border-dashed border-slate-200 text-center space-y-1">
                  <p className="text-xs font-semibold text-slate-700">No best habit yet</p>
                  <p className="text-[11px] text-slate-400">Complete scheduled habits to see highlights here.</p>
                </div>
              )}

              {/* Overview Counters */}
              <div className="grid grid-cols-2 gap-3">
                <div
                  aria-label={`Total active habits ${summary.total_active_habits}`}
                  className="p-4 rounded-2xl bg-white border border-slate-200/80 shadow-sm"
                >
                  <div className="flex items-center gap-1.5 text-xs font-bold text-slate-700">
                    <Layers className="w-4 h-4 text-slate-500" />
                    <span>Active Habits</span>
                  </div>
                  <p className="mt-2 text-2xl font-extrabold text-slate-900">
                    {summary.total_active_habits}
                  </p>
                  <p className="text-[10px] text-slate-500 mt-0.5">Currently tracking</p>
                </div>

                <div
                  aria-label={`Total check-ins ${summary.total_check_ins}`}
                  className="p-4 rounded-2xl bg-white border border-slate-200/80 shadow-sm"
                >
                  <div className="flex items-center gap-1.5 text-xs font-bold text-slate-700">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    <span>Total Check-ins</span>
                  </div>
                  <p className="mt-2 text-2xl font-extrabold text-slate-900">
                    {summary.total_check_ins}
                  </p>
                  <p className="text-[10px] text-slate-500 mt-0.5">All-time lifetime</p>
                </div>
              </div>
            </>
          ) : null}
        </main>

        {/* Bottom Navigation */}
        <BottomNavigation />
      </div>
    </div>
  );
};
