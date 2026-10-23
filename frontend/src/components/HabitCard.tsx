import React, { useState, useRef, useEffect } from 'react';
import { Habit } from '../types/habit';
import { Check, MoreHorizontal, Edit, Archive, Trash2 } from 'lucide-react';

interface HabitCardProps {
  habit: Habit;
  onToggle: (habit: Habit) => void;
  onEdit?: (habit: Habit) => void;
  onArchive?: (habit: Habit) => void;
  onDelete?: (habit: Habit) => void;
  disabled?: boolean;
}

export const HabitCard: React.FC<HabitCardProps> = ({
  habit,
  onToggle,
  onEdit,
  onArchive,
  onDelete,
  disabled = false,
}) => {
  const isChecked = habit.is_checked_today;
  const accentColor = habit.color || '#3B82F6';
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsMenuOpen(false);
      }
    };
    if (isMenuOpen) {
      document.addEventListener('mousedown', handleOutsideClick);
    }
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
    };
  }, [isMenuOpen]);

  const handleCardClick = () => {
    onToggle(habit);
  };

  const handleMenuToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsMenuOpen((prev) => !prev);
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={handleCardClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleCardClick();
        }
      }}
      aria-label={`Toggle ${habit.name}, currently ${isChecked ? 'completed' : 'incomplete'}`}
      aria-pressed={isChecked}
      className={`relative w-full min-h-[56px] text-left p-3.5 rounded-2xl border transition-all duration-200 flex items-center justify-between gap-3 select-none cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
        disabled ? 'opacity-60 pointer-events-none' : 'active:scale-[0.99]'
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

      {/* Right side: Checkbox Circle Indicator & Menu Button */}
      <div className="shrink-0 flex items-center gap-2 pl-1">
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

        {(onEdit || onArchive || onDelete) && (
          <div className="relative" ref={menuRef}>
            <button
              type="button"
              onClick={handleMenuToggle}
              aria-label={`More options for ${habit.name}`}
              aria-haspopup="menu"
              aria-expanded={isMenuOpen}
              className="min-h-[44px] min-w-[36px] flex items-center justify-center text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition"
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
