import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { LogOut, Flame, Sparkles } from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const { user, logout } = useAuth();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
    } finally {
      setIsLoggingOut(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center">
      {/* Mobile-first Container (375px min width styled, responsive max width) */}
      <div className="w-full max-w-[420px] min-h-screen flex flex-col bg-white shadow-sm border-x border-slate-100">
        {/* Top App Header */}
        <header className="px-5 py-4 border-b border-slate-100 flex items-center justify-between sticky top-0 bg-white/95 backdrop-blur z-10">
          <div className="flex items-center gap-2">
            <span className="text-2xl select-none" role="img" aria-label="Target">🎯</span>
            <div>
              <h1 className="text-base font-bold text-slate-900 leading-tight">Habit Tracker</h1>
              <p className="text-[11px] text-slate-500 truncate max-w-[160px] sm:max-w-[200px]" title={user?.email}>
                {user?.email}
              </p>
            </div>
          </div>

          <button
            onClick={handleLogout}
            disabled={isLoggingOut}
            aria-label="Log out"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-100 active:bg-slate-200 transition duration-150 disabled:opacity-50"
          >
            {isLoggingOut ? (
              <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-400 border-t-transparent" />
            ) : (
              <LogOut className="h-3.5 w-3.5 text-slate-500" />
            )}
            <span>Sign out</span>
          </button>
        </header>

        {/* Main Content Area */}
        <main className="flex-1 p-5 space-y-5">
          {/* Welcome Card */}
          <div className="rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-600 p-5 text-white shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-blue-100 flex items-center gap-1">
                <Sparkles className="h-3.5 w-3.5" /> Welcome back
              </span>
              <span className="text-xs bg-white/20 backdrop-blur px-2 py-0.5 rounded-full font-medium">
                {user?.timezone || 'UTC'}
              </span>
            </div>
            <h2 className="text-lg font-bold">Ready to build momentum?</h2>
            <p className="mt-1 text-xs text-blue-100 leading-relaxed">
              Every check-in keeps your streak alive. Stay focused and conquer today's habits!
            </p>
          </div>

          {/* Quick Stats Placeholder */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-100">
              <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
                <Flame className="h-4 w-4 text-orange-500" /> Current Streak
              </div>
              <p className="mt-2 text-2xl font-bold text-slate-800">0 <span className="text-xs font-normal text-slate-500">days</span></p>
            </div>
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-100">
              <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
                <span className="text-sm">🎯</span> Completed Today
              </div>
              <p className="mt-2 text-2xl font-bold text-slate-800">0 <span className="text-xs font-normal text-slate-500">habits</span></p>
            </div>
          </div>

          {/* Habits Dashboard Placeholder */}
          <div className="p-6 rounded-2xl border-2 border-dashed border-slate-200 text-center space-y-2">
            <p className="text-sm font-semibold text-slate-700">Dashboard Loaded Successfully</p>
            <p className="text-xs text-slate-500">
              Authentication and token refresh are fully wired. Step 5.3 (Habit tracking cards & check-in toggle) will populate this list next!
            </p>
          </div>
        </main>
      </div>
    </div>
  );
};
