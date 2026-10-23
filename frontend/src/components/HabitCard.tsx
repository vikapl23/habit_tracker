import React from 'react';
import { Habit } from '../types/habit';
import { Check } from 'lucide-react';

interface HabitCardProps {
  habit: Habit;
  onToggle: (habit: Habit) => void;
  disabled?: boolean;
}

export const HabitCard: React.FC<HabitCardProps> = ({ habit, onToggle, disabled = false }) => {
  const isChecked = habit.is_checked_today;
  const accentColor = habit.color || '#3B82F6';

  return (
    <button
      type="button"
      onClick={() => onToggle(habit)}
      disabled={disabled}
      aria-label={`Toggle ${habit.name}, currently ${isChecked ? 'completed' : 'incomplete'}`}
      aria-pressed={isChecked}
      className={`w-full min-h-[56px] text-left p-3.5 rounded-2xl border transition-all duration-200 flex items-center justify-between gap-3 select-none active:scale-[0.98] focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-60 disabled:pointer-events-none ${
        isChecked
          ? 'bg-slate-50/80 border-slate-200 shadow-none'
          : 'bg-white border-slate-200/90 shadow-sm hover:border-slate-300 hover:shadow'
      }`}
      style={{
        borderLeftWidth: '5px',
        borderLeftColor: accentColor,
      }}
    >
      {/* Left side: Emoji & Habit Information */}
      <div className="flex items-center gap-3 min-w-0 flex-1">
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center text-xl shrink-0 transition-transform"
          style={{
            backgroundColor: `${accentColor}18`,
          }}
          aria-hidden="true"
        >
          {habit.emoji || '🎯'}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3
              className={`text-sm font-semibold truncate transition-colors ${
                isChecked ? 'line-through text-slate-400' : 'text-slate-900'
              }`}
            >
              {habit.name}
            </h3>
          </div>

          {/* Streaks Badges */}
          <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
            <span
              className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-md text-[11px] font-bold bg-amber-50 text-amber-800 border border-amber-200/60"
              aria-label={`Current streak ${habit.current_streak} days`}
            >
              🔥 {habit.current_streak}
            </span>
            <span
              className="text-[11px] font-medium text-slate-400"
              aria-label={`Longest streak ${habit.longest_streak} days`}
            >
              best {habit.longest_streak}d
            </span>
          </div>
        </div>
      </div>

      {/* Right side: Checkbox Circle Indicator */}
      <div className="shrink-0 flex items-center justify-center pl-1">
        <div
          className={`w-7 h-7 rounded-full flex items-center justify-center transition-all duration-200 ${
            isChecked
              ? 'bg-emerald-500 text-white shadow-sm ring-2 ring-emerald-500/20'
              : 'border-2 border-slate-300 hover:border-slate-400 bg-white'
          }`}
          aria-hidden="true"
        >
          {isChecked && <Check className="w-4 h-4 stroke-[2.5]" />}
        </div>
      </div>
    </button>
  );
};
