import React from 'react';

export const DashboardSkeleton: React.FC = () => {
  return (
    <div className="space-y-5 animate-pulse" role="status" aria-label="Loading dashboard">
      {/* Date & Progress Card Skeleton */}
      <div className="rounded-2xl bg-slate-200/70 p-5 space-y-3">
        <div className="flex items-center justify-between">
          <div className="h-4 w-28 bg-slate-300 rounded-md" />
          <div className="h-4 w-16 bg-slate-300 rounded-full" />
        </div>
        <div className="h-6 w-44 bg-slate-300 rounded-md" />
        <div className="h-2.5 w-full bg-slate-300 rounded-full" />
      </div>

      {/* Stats Cards Skeleton */}
      <div className="grid grid-cols-2 gap-3">
        <div className="p-4 rounded-xl bg-slate-100 border border-slate-200/60 space-y-2">
          <div className="h-3.5 w-20 bg-slate-200 rounded" />
          <div className="h-7 w-16 bg-slate-300 rounded" />
        </div>
        <div className="p-4 rounded-xl bg-slate-100 border border-slate-200/60 space-y-2">
          <div className="h-3.5 w-24 bg-slate-200 rounded" />
          <div className="h-7 w-16 bg-slate-300 rounded" />
        </div>
      </div>

      {/* Habit List Section Skeleton */}
      <div className="space-y-3 pt-2">
        <div className="h-4 w-24 bg-slate-200 rounded" />
        <div className="space-y-2.5">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-16 w-full rounded-2xl bg-slate-100 border border-slate-200/60 p-3.5 flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-slate-200" />
                <div className="space-y-1.5">
                  <div className="h-4 w-32 bg-slate-200 rounded" />
                  <div className="h-3 w-20 bg-slate-200 rounded" />
                </div>
              </div>
              <div className="w-7 h-7 rounded-full bg-slate-200" />
            </div>
          ))}
        </div>
      </div>
      <span className="sr-only">Loading habits...</span>
    </div>
  );
};
