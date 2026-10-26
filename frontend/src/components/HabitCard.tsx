import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Habit } from '../types/habit';
import { Check, MoreHorizontal, Edit, Archive, Trash2, Plus, Minus } from 'lucide-react';

interface HabitCardProps {
  habit: Habit;
  onToggle: (habit: Habit, options?: { value?: number; mode?: 'add' | 'set'; action?: 'check' | 'uncheck' }) => void;
  onSelect?: (habit: Habit) => void;
  onEdit?: (habit: Habit) => void;
  onArchive?: (habit: Habit) => void;
  onDelete?: (habit: Habit) => void;
  disabled?: boolean;
}

export const HabitCard: React.FC<HabitCardProps> = ({
  habit,
  onToggle,
  onSelect,
  onEdit,
  onArchive,
  onDelete,
  disabled = false,
}) => {
  const navigate = useNavigate();
  const isChecked = habit.is_checked_today;
  const accentColor = habit.color || '#3B82F6';
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!isMenuOpen) return;
    const handleOutsideClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsMenuOpen(false);
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsMenuOpen(false);
        menuButtonRef.current?.focus();
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isMenuOpen]);

  const isMeasurable = habit.habit_type === 'measurable';
  const target = habit.target_value ?? 1;
  const todayValue = habit.today_value ?? 0;
  const progressPct = Math.min(100, Math.max(0, habit.today_progress ?? (isChecked ? 100 : 0)));

  const [isEditingExact, setIsEditingExact] = useState(false);
  const [exactInput, setExactInput] = useState('');
  const exactInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isEditingExact) {
      setExactInput(String(todayValue));
      setTimeout(() => exactInputRef.current?.select(), 50);
    }
  }, [isEditingExact, todayValue]);

  const handleExactSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const parsed = parseFloat(exactInput);
    if (!isNaN(parsed) && parsed >= 0) {
      onToggle(habit, { value: parsed, mode: 'set' });
    }
    setIsEditingExact(false);
  };

  const handleInfoClick = (e: React.MouseEvent | React.KeyboardEvent) => {
    e.stopPropagation();
    if (onSelect) {
      onSelect(habit);
    } else {
      navigate(`/habits/${habit.id}`);
    }
  };

  const handleMenuToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsMenuOpen((prev) => !prev);
  };

  return (
    <div
      className={`relative w-full min-h-[56px] text-left p-3.5 rounded-2xl border transition-all duration-200 flex items-center justify-between gap-3 select-none ${
        disabled ? 'opacity-60 pointer-events-none' : ''
      } ${
        isChecked
          ? 'bg-slate-50/80 border-slate-200 shadow-none'
          : 'bg-white border-slate-200/90 shadow-sm hover:border-slate-300 hover:shadow'
      }`}
      style={{
        borderLeftWidth: '5px',
        borderLeftColor: accentColor,
      }}
    >
      {/* Left side: Emoji & Habit Information (Tap to view habit details) */}
      <div
        role="button"
        tabIndex={0}
        onClick={handleInfoClick}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleInfoClick(e);
          }
        }}
        aria-label={`View details for ${habit.name}`}
        className="flex items-center gap-3 min-w-0 flex-1 cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded-lg p-1 -m-1"
      >
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
                isChecked ? 'line-through text-slate-500' : 'text-slate-900'
              }`}
            >
              {habit.name}
            </h3>
          </div>

          {/* Measurable Progress display & Streaks */}
          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
            {isMeasurable ? (
              isEditingExact ? (
                <form
                  onSubmit={handleExactSubmit}
                  onClick={(e) => e.stopPropagation()}
                  className="flex items-center gap-1.5"
                >
                  <input
                    ref={exactInputRef}
                    type="number"
                    step="any"
                    min="0"
                    max="100000"
                    aria-label={`Enter exact amount for ${habit.name}`}
                    value={exactInput}
                    onChange={(e) => setExactInput(e.target.value)}
                    onBlur={() => setIsEditingExact(false)}
                    className="w-16 h-6 px-1.5 text-xs font-bold rounded border border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white"
                  />
                  <span className="text-[11px] text-slate-500">/ {target} {habit.unit}</span>
                </form>
              ) : (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setIsEditingExact(true);
                  }}
                  aria-label={`Current amount ${todayValue} of ${target} ${habit.unit}. Tap to enter exact amount`}
                  className="text-xs font-bold text-blue-600 hover:text-blue-800 transition py-0.5 px-1 -mx-1 rounded hover:bg-blue-50"
                >
                  {todayValue} / {target} {habit.unit}
                </button>
              )
            ) : null}

            {/* Streaks Badges */}
            <div className="flex items-center gap-1.5">
              <span
                className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-md text-[11px] font-bold bg-amber-50 text-amber-800 border border-amber-200/60"
                aria-label={`Current streak ${habit.current_streak} days`}
              >
                🔥 {habit.current_streak}
              </span>
              <span
                className="text-[11px] font-medium text-slate-500"
                aria-label={`Longest streak ${habit.longest_streak} days`}
              >
                best {habit.longest_streak}d
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Right side: Action buttons & Menu */}
      <div className="shrink-0 flex items-center gap-1.5 pl-1">
        {isMeasurable ? (
          <div className="flex items-center gap-1">
            {/* Quick Decrement (-) */}
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                if (!disabled) {
                  onToggle(habit, { value: 1, action: 'uncheck' });
                }
              }}
              aria-label={`Decrease ${habit.name}`}
              disabled={disabled || todayValue <= 0}
              className="w-7 h-7 rounded-full flex items-center justify-center text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 active:scale-95 transition disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Minus className="w-3.5 h-3.5" />
            </button>

            {/* Progress Ring with (+) button or tap to check */}
            <div className="relative w-8 h-8 flex items-center justify-center">
              <svg className="w-8 h-8 -rotate-90 pointer-events-none" viewBox="0 0 36 36">
                <circle
                  cx="18"
                  cy="18"
                  r="14"
                  fill="none"
                  stroke="#E2E8F0"
                  strokeWidth="3.5"
                />
                <circle
                  cx="18"
                  cy="18"
                  r="14"
                  fill="none"
                  stroke={isChecked ? '#10B981' : accentColor}
                  strokeWidth="3.5"
                  strokeDasharray="88"
                  strokeDashoffset={88 - (88 * progressPct) / 100}
                  strokeLinecap="round"
                  className="transition-all duration-300 ease-out"
                />
              </svg>

              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  if (!disabled) {
                    onToggle(habit, { value: 1, action: 'check' });
                  }
                }}
                disabled={disabled}
                aria-label={`Add 1 ${habit.unit || ''} to ${habit.name}`}
                className="absolute inset-0 m-auto w-6 h-6 rounded-full flex items-center justify-center text-slate-700 hover:text-blue-600 active:scale-95 transition"
              >
                {isChecked ? (
                  <Check className="w-3.5 h-3.5 text-emerald-600 stroke-[3]" />
                ) : (
                  <Plus className="w-3.5 h-3.5" />
                )}
              </button>
            </div>
          </div>
        ) : (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              if (!disabled) {
                onToggle(habit);
              }
            }}
            aria-disabled={disabled}
            aria-label={`Toggle ${habit.name}, currently ${isChecked ? 'completed' : 'incomplete'}`}
            aria-pressed={isChecked}
            className={`min-w-[44px] min-h-[44px] -m-2 flex items-center justify-center rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 ${
              disabled ? 'opacity-60 cursor-not-allowed' : ''
            }`}
          >
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center transition-all duration-200 pointer-events-none ${
                isChecked
                  ? 'bg-emerald-500 text-white shadow-sm ring-2 ring-emerald-500/20'
                  : 'border-2 border-slate-300 hover:border-slate-400 bg-white'
              }`}
            >
              {isChecked && <Check className="w-4 h-4 stroke-[2.5]" />}
            </div>
          </button>
        )}

        {(onEdit || onArchive || onDelete) && (
          <div className="relative" ref={menuRef}>
            <button
              ref={menuButtonRef}
              type="button"
              onClick={handleMenuToggle}
              aria-label={`More options for ${habit.name}`}
              aria-haspopup="menu"
              aria-expanded={isMenuOpen}
              className="min-h-[44px] min-w-[44px] flex items-center justify-center text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition"
            >
              <MoreHorizontal className="w-5 h-5" />
            </button>

            {isMenuOpen && (
              <div
                role="menu"
                className="absolute right-0 top-full mt-1 w-36 rounded-xl bg-white shadow-xl border border-slate-100 py-1 z-30 animate-in fade-in zoom-in-95 duration-100"
                onClick={(e) => e.stopPropagation()}
              >
                {onEdit && (
                  <button
                    type="button"
                    role="menuitem"
                    onClick={(e) => {
                      e.stopPropagation();
                      setIsMenuOpen(false);
                      onEdit(habit);
                    }}
                    className="w-full min-h-[40px] px-3 flex items-center gap-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition text-left"
                  >
                    <Edit className="w-3.5 h-3.5 text-slate-500" />
                    <span>Edit</span>
                  </button>
                )}

                {onArchive && (
                  <button
                    type="button"
                    role="menuitem"
                    onClick={(e) => {
                      e.stopPropagation();
                      setIsMenuOpen(false);
                      onArchive(habit);
                    }}
                    className="w-full min-h-[40px] px-3 flex items-center gap-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition text-left"
                  >
                    <Archive className="w-3.5 h-3.5 text-slate-500" />
                    <span>Archive</span>
                  </button>
                )}

                {onDelete && (
                  <button
                    type="button"
                    role="menuitem"
                    onClick={(e) => {
                      e.stopPropagation();
                      setIsMenuOpen(false);
                      onDelete(habit);
                    }}
                    className="w-full min-h-[40px] px-3 flex items-center gap-2 text-xs font-semibold text-red-600 hover:bg-red-50 transition text-left border-t border-slate-100"
                  >
                    <Trash2 className="w-3.5 h-3.5 text-red-500" />
                    <span>Delete</span>
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
