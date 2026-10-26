import React, { useState, useEffect, useRef } from 'react';
import { X, AlertTriangle } from 'lucide-react';
import { Habit, HabitFormData, FrequencyType, HabitType } from '../types/habit';
import { ApiError } from '../api/client';
import { getErrorMessage } from '../utils/errorUtils';

interface HabitFormBottomSheetProps {
  isOpen: boolean;
  habit?: Habit | null;
  onClose: () => void;
  onSubmit: (data: HabitFormData) => Promise<void>;
}

const COMMON_UNITS = ['glasses', 'km', 'minutes', 'pages', 'steps', 'hours'];

const PRESET_COLORS: Array<{ hex: string; name: string }> = [
  { hex: '#3B82F6', name: 'Blue' },
  { hex: '#10B981', name: 'Emerald' },
  { hex: '#F59E0B', name: 'Amber' },
  { hex: '#EF4444', name: 'Red' },
  { hex: '#8B5CF6', name: 'Purple' },
  { hex: '#EC4899', name: 'Pink' },
  { hex: '#06B6D4', name: 'Cyan' },
  { hex: '#14B8A6', name: 'Teal' },
  { hex: '#F97316', name: 'Orange' },
  { hex: '#6366F1', name: 'Indigo' },
];

const PRESET_EMOJIS = [
  '🎯', '💧', '🏃', '📚', '🧘', '💪', '🍎', '💤',
  '☕', '✍️', '🌱', '🚶', '🚴', '🎨', '🧠', '🥗',
  '☀️', '🚭', '🧹', '💊',
];

const WEEKDAYS = [
  { day: 0, label: 'Mon' },
  { day: 1, label: 'Tue' },
  { day: 2, label: 'Wed' },
  { day: 3, label: 'Thu' },
  { day: 4, label: 'Fri' },
  { day: 5, label: 'Sat' },
  { day: 6, label: 'Sun' },
];

export const HabitFormBottomSheet: React.FC<HabitFormBottomSheetProps> = ({
  isOpen,
  habit,
  onClose,
  onSubmit,
}) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [color, setColor] = useState(PRESET_COLORS[0].hex);
  const [emoji, setEmoji] = useState(PRESET_EMOJIS[0]);
  const [frequencyType, setFrequencyType] = useState<FrequencyType>('daily');
  const [frequencyDays, setFrequencyDays] = useState<number[]>([]);
  const [habitType, setHabitType] = useState<HabitType>('boolean');
  const [unit, setUnit] = useState('');
  const [targetValue, setTargetValue] = useState('');

  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const nameInputRef = useRef<HTMLInputElement>(null);
  const weekdaySectionRef = useRef<HTMLDivElement>(null);
  const touchStartY = useRef<number | null>(null);

  // Sync form state when habit changes or sheet opens
  useEffect(() => {
    if (isOpen) {
      if (habit) {
        setName(habit.name);
        setDescription(habit.description || '');
        setColor(habit.color || PRESET_COLORS[0].hex);
        setEmoji(habit.emoji || PRESET_EMOJIS[0]);
        setFrequencyType(habit.frequency_type || 'daily');
        setFrequencyDays(habit.frequency_days || []);
        setHabitType(habit.habit_type || 'boolean');
        setUnit(habit.unit || '');
        setTargetValue(habit.target_value !== undefined && habit.target_value !== null ? String(habit.target_value) : '');
      } else {
        setName('');
        setDescription('');
        setColor(PRESET_COLORS[0].hex);
        setEmoji(PRESET_EMOJIS[0]);
        setFrequencyType('daily');
        setFrequencyDays([]);
        setHabitType('boolean');
        setUnit('');
        setTargetValue('');
      }
      setFieldErrors({});
      setGeneralError(null);

      // Focus name input automatically
      const timer = setTimeout(() => {
        nameInputRef.current?.focus();
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [isOpen, habit]);

  // Handle ESC key to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Touch handlers for swipe down to dismiss
  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartY.current = e.touches[0].clientY;
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    if (touchStartY.current !== null) {
      const touchEndY = e.changedTouches[0].clientY;
      const distance = touchEndY - touchStartY.current;
      // If pulled down sufficiently (> 75px), close sheet
      if (distance > 75) {
        onClose();
      }
    }
    touchStartY.current = null;
  };

  const scrollToFirstError = () => {
    setTimeout(() => {
      const errorEl = document.querySelector('[data-form-error="true"]');
      if (errorEl && typeof errorEl.scrollIntoView === 'function') {
        errorEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }, 50);
  };

  const handleSelectSpecificDays = () => {
    setFrequencyType('custom');
    setTimeout(() => {
      if (weekdaySectionRef.current && typeof weekdaySectionRef.current.scrollIntoView === 'function') {
        weekdaySectionRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }, 50);
  };

  const toggleWeekday = (day: number) => {
    setFrequencyDays((prev) => {
      if (prev.includes(day)) {
        return prev.filter((d) => d !== day);
      }
      return [...prev, day].sort();
    });
    // Clear weekday error when user toggles
    setFieldErrors((prev) => {
      const next = { ...prev };
      delete next.frequency_days;
      delete next.frequency;
      return next;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFieldErrors({});
    setGeneralError(null);

    // Client-side quick validations
    const errors: Record<string, string> = {};
    if (!name.trim()) {
      errors.name = 'Habit name is required.';
    }
    if (frequencyType === 'custom' && frequencyDays.length === 0) {
      errors.frequency_days = 'Custom frequency requires at least one weekday.';
    }
    if (habitType === 'measurable') {
      if (!unit.trim()) {
        errors.unit = 'Unit is required for measurable habits.';
      }
      const parsedTarget = parseFloat(targetValue);
      if (isNaN(parsedTarget) || parsedTarget <= 0) {
        errors.target_value = 'Daily target must be greater than 0.';
      } else if (parsedTarget > 100000) {
        errors.target_value = 'Daily target cannot exceed 100,000.';
      }
    }

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      scrollToFirstError();
      return;
    }

    setIsSubmitting(true);
    try {
      const payload: HabitFormData = {
        name: name.trim(),
        description: description.trim(),
        color,
        emoji: emoji.trim() || '🎯',
        frequency_type: frequencyType,
        frequency_days: frequencyType === 'daily' ? [] : frequencyDays,
        habit_type: habitType,
        ...(habitType === 'measurable'
          ? {
              unit: unit.trim(),
              target_value: parseFloat(targetValue),
            }
          : {
              unit: '',
              target_value: null,
            }),
      };
      await onSubmit(payload);
      onClose();
    } catch (err: unknown) {
      if (err instanceof ApiError && err.data && typeof err.data === 'object') {
        const nextFieldErrors: Record<string, string> = {};
        const unhandledErrors: string[] = [];
        const knownFields = new Set([
          'name',
          'description',
          'color',
          'emoji',
          'frequency_type',
          'frequency_days',
          'habit_type',
          'unit',
          'target_value',
        ]);

        for (const [key, val] of Object.entries(err.data)) {
          const valStr = Array.isArray(val) ? val.join(' ') : String(val);
          if (knownFields.has(key)) {
            nextFieldErrors[key] = valStr;
          } else if (key !== 'detail' && key !== 'non_field_errors') {
            unhandledErrors.push(`${key}: ${valStr}`);
          }
        }
        setFieldErrors(nextFieldErrors);

        if (err.data.detail) {
          setGeneralError(err.data.detail);
        } else if (err.data.non_field_errors) {
          setGeneralError(
            Array.isArray(err.data.non_field_errors)
              ? err.data.non_field_errors.join(' ')
              : String(err.data.non_field_errors)
          );
        } else if (unhandledErrors.length > 0) {
          setGeneralError(unhandledErrors.join(' | '));
        } else if (Object.keys(nextFieldErrors).length === 0) {
          setGeneralError(getErrorMessage(err, 'Something went wrong. Please check your inputs.'));
        }
      } else {
        setGeneralError(getErrorMessage(err, 'Something went wrong. Please check your inputs.'));
      }
      scrollToFirstError();
    } finally {
      setIsSubmitting(false);
    }
  };

  const sheetDialogRef = useRef<HTMLDivElement>(null);
  const previousActiveElement = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    previousActiveElement.current = document.activeElement as HTMLElement | null;
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isSubmitting) {
        onClose();
        return;
      }

      if (e.key === 'Tab' && sheetDialogRef.current) {
        const focusable = sheetDialogRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];

        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      document.body.style.overflow = originalOverflow;
      window.removeEventListener('keydown', handleKeyDown);
      previousActiveElement.current?.focus?.();
    };
  }, [isOpen, isSubmitting, onClose]);

  if (!isOpen) return null;

  return (
    <div
      ref={sheetDialogRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby="habit-sheet-title"
      className="fixed inset-0 z-40 flex flex-col justify-end bg-slate-900/50 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className="w-full max-w-[420px] mx-auto bg-white rounded-t-3xl shadow-2xl flex flex-col max-h-[90dvh] max-h-[90vh] overflow-hidden animate-in slide-in-from-bottom duration-300"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drag handle header for swipe affordance */}
        <div
          className="pt-3 pb-1 flex flex-col items-center shrink-0 cursor-grab active:cursor-grabbing"
          onTouchStart={handleTouchStart}
          onTouchEnd={handleTouchEnd}
        >
          <div className="w-10 h-1.5 rounded-full bg-slate-300" aria-hidden="true" />
          <div className="w-full px-5 pt-2 pb-3 flex items-center justify-between border-b border-slate-100">
            <h2 id="habit-sheet-title" className="text-base font-bold text-slate-900">
              {habit ? 'Edit Habit' : 'New Habit'}
            </h2>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close bottom sheet"
              className="min-w-[44px] min-h-[44px] flex items-center justify-center rounded-full text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Scrollable Form Body */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
          {generalError && (
            <div
              role="alert"
              data-form-error="true"
              className="p-3 rounded-xl bg-red-50 text-red-700 text-xs font-medium border border-red-200"
            >
              {generalError}
            </div>
          )}

          {/* Habit Type Switch (Yes/No vs Amount) */}
          <fieldset className="space-y-2 border-0 p-0 m-0">
            <legend className="block text-xs font-bold text-slate-700">
              Habit Type
            </legend>
            <div className="grid grid-cols-2 gap-2 p-1 bg-slate-100 rounded-xl">
              <button
                type="button"
                onClick={() => {
                  setHabitType('boolean');
                  setFieldErrors((prev) => {
                    const next = { ...prev };
                    delete next.unit;
                    delete next.target_value;
                    return next;
                  });
                }}
                aria-pressed={habitType === 'boolean'}
                className={`min-h-[40px] text-xs font-semibold rounded-lg transition-all ${
                  habitType === 'boolean'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Yes/No (Done)
              </button>
              <button
                type="button"
                onClick={() => setHabitType('measurable')}
                aria-pressed={habitType === 'measurable'}
                className={`min-h-[40px] text-xs font-semibold rounded-lg transition-all ${
                  habitType === 'measurable'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Amount (Measurable)
              </button>
            </div>
          </fieldset>

          {/* Measurable Fields: Unit & Target Value */}
          {habitType === 'measurable' && (
            <div className="p-3.5 rounded-2xl bg-blue-50/50 border border-blue-100 space-y-3.5 animate-in fade-in">
              {/* Streak recalculation warning if editing */}
              {habit && (
                <div className="flex items-start gap-2 p-2.5 rounded-xl bg-amber-50 text-amber-800 border border-amber-200/80 text-[11px] leading-relaxed">
                  <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                  <span>Changing the target will recalculate your streak.</span>
                </div>
              )}

              {/* Unit Input & Suggestions */}
              <div className="space-y-1.5">
                <label htmlFor="habit-unit" className="block text-xs font-bold text-slate-700">
                  Unit <span className="text-red-500">*</span>
                </label>
                <input
                  id="habit-unit"
                  type="text"
                  required={habitType === 'measurable'}
                  aria-invalid={!!fieldErrors.unit}
                  aria-describedby={fieldErrors.unit ? 'habit-unit-error' : undefined}
                  value={unit}
                  onChange={(e) => {
                    setUnit(e.target.value);
                    if (fieldErrors.unit) {
                      setFieldErrors((prev) => {
                        const next = { ...prev };
                        delete next.unit;
                        return next;
                      });
                    }
                  }}
                  placeholder="e.g. glasses, km, pages"
                  className={`w-full h-10 px-3 rounded-xl border text-base sm:text-sm text-slate-900 bg-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition ${
                    fieldErrors.unit ? 'border-red-500 bg-red-50/20' : 'border-slate-200'
                  }`}
                />
                {/* Unit Suggestions */}
                <div className="flex items-center gap-1.5 flex-wrap pt-1">
                  <span className="text-[11px] text-slate-500 font-medium">Suggestions:</span>
                  {COMMON_UNITS.map((u) => (
                    <button
                      key={u}
                      type="button"
                      onClick={() => {
                        setUnit(u);
                        if (fieldErrors.unit) {
                          setFieldErrors((prev) => {
                            const next = { ...prev };
                            delete next.unit;
                            return next;
                          });
                        }
                      }}
                      className={`px-2 py-0.5 rounded-lg text-[11px] font-medium border transition ${
                        unit.toLowerCase() === u.toLowerCase()
                          ? 'bg-blue-600 text-white border-blue-600'
                          : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300 active:bg-slate-50'
                      }`}
                    >
                      {u}
                    </button>
                  ))}
                </div>
                {fieldErrors.unit && (
                  <p id="habit-unit-error" data-form-error="true" className="text-[11px] font-medium text-red-600 animate-in fade-in">
                    {fieldErrors.unit}
                  </p>
                )}
              </div>

              {/* Daily Target */}
              <div className="space-y-1.5">
                <label htmlFor="habit-target" className="block text-xs font-bold text-slate-700">
                  Daily Target <span className="text-red-500">*</span>
                </label>
                <input
                  id="habit-target"
                  type="number"
                  step="any"
                  min="0.01"
                  max="100000"
                  required={habitType === 'measurable'}
                  aria-invalid={!!fieldErrors.target_value}
                  aria-describedby={fieldErrors.target_value ? 'habit-target-error' : undefined}
                  value={targetValue}
                  onChange={(e) => {
                    setTargetValue(e.target.value);
                    if (fieldErrors.target_value) {
                      setFieldErrors((prev) => {
                        const next = { ...prev };
                        delete next.target_value;
                        return next;
                      });
                    }
                  }}
                  placeholder="e.g. 8 or 2.5"
                  className={`w-full h-10 px-3 rounded-xl border text-base sm:text-sm text-slate-900 bg-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition ${
                    fieldErrors.target_value ? 'border-red-500 bg-red-50/20' : 'border-slate-200'
                  }`}
                />
                {fieldErrors.target_value && (
                  <p id="habit-target-error" data-form-error="true" className="text-[11px] font-medium text-red-600 animate-in fade-in">
                    {fieldErrors.target_value}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Name Field */}
          <div className="space-y-1.5">
            <label htmlFor="habit-name" className="block text-xs font-bold text-slate-700">
              Habit Name <span className="text-red-500">*</span>
            </label>
            <input
              ref={nameInputRef}
              id="habit-name"
              type="text"
              required
              aria-invalid={!!fieldErrors.name}
              aria-describedby={fieldErrors.name ? 'habit-name-error' : undefined}
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                if (fieldErrors.name) {
                  setFieldErrors((prev) => {
                    const next = { ...prev };
                    delete next.name;
                    return next;
                  });
                }
              }}
              placeholder="e.g. Read 20 pages"
              className={`w-full h-11 px-3.5 rounded-xl border text-base sm:text-sm text-slate-900 bg-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition ${
                fieldErrors.name ? 'border-red-500 bg-red-50/20' : 'border-slate-200'
              }`}
            />
            {fieldErrors.name && (
              <p id="habit-name-error" data-form-error="true" className="text-[11px] font-medium text-red-600 animate-in fade-in">
                {fieldErrors.name}
              </p>
            )}
          </div>

          {/* Description Field */}
          <div className="space-y-1.5">
            <label htmlFor="habit-description" className="block text-xs font-bold text-slate-700">
              Description <span className="text-slate-500 font-normal">(optional)</span>
            </label>
            <textarea
              id="habit-description"
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Why this habit matters..."
              aria-invalid={!!fieldErrors.description}
              aria-describedby={fieldErrors.description ? 'habit-description-error' : undefined}
              className="w-full px-3.5 py-2 rounded-xl border border-slate-200 text-base sm:text-sm text-slate-900 bg-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition resize-none"
            />
            {fieldErrors.description && (
              <p id="habit-description-error" data-form-error="true" className="text-[11px] font-medium text-red-600 animate-in fade-in">
                {fieldErrors.description}
              </p>
            )}
          </div>

          {/* Color Picker */}
          <fieldset className="space-y-2 border-0 p-0 m-0">
            <legend className="block text-xs font-bold text-slate-700">
              Color Accent
            </legend>
            <div className="flex items-center gap-2.5 flex-wrap">
              {PRESET_COLORS.map(({ hex: c, name: colorName }) => {
                const isSelected = color.toUpperCase() === c.toUpperCase();
                return (
                  <button
                    key={c}
                    type="button"
                    onClick={() => {
                      setColor(c);
                      if (fieldErrors.color) {
                        setFieldErrors((prev) => {
                          const next = { ...prev };
                          delete next.color;
                          return next;
                        });
                      }
                    }}
                    aria-label={`Select color ${colorName} (${c})`}
                    aria-pressed={isSelected}
                    className="min-w-[44px] min-h-[44px] flex items-center justify-center p-1"
                  >
                    <span
                      className={`w-8 h-8 rounded-full transition-transform active:scale-90 flex items-center justify-center ${
                        isSelected ? 'ring-2 ring-offset-2 ring-slate-800 scale-110 shadow-sm' : ''
                      }`}
                      style={{ backgroundColor: c }}
                    />
                  </button>
                );
              })}
            </div>
            {fieldErrors.color && (
              <p data-form-error="true" className="text-[11px] font-medium text-red-600 animate-in fade-in">
                {fieldErrors.color}
              </p>
            )}
          </fieldset>

          {/* Emoji Picker */}
          <fieldset className="space-y-2 border-0 p-0 m-0">
            <legend className="block text-xs font-bold text-slate-700">
              Emoji Icon
            </legend>
            <div className="grid grid-cols-5 sm:grid-cols-10 gap-1.5 p-2 rounded-xl bg-slate-50 border border-slate-100">
              {PRESET_EMOJIS.map((em) => {
                const isSelected = emoji === em;
                return (
                  <button
                    key={em}
                    type="button"
                    onClick={() => {
                      setEmoji(em);
                      if (fieldErrors.emoji) {
                        setFieldErrors((prev) => {
                          const next = { ...prev };
                          delete next.emoji;
                          return next;
                        });
                      }
                    }}
                    aria-label={`Select emoji ${em}`}
                    aria-pressed={isSelected}
                    className={`min-w-[44px] min-h-[44px] text-lg rounded-xl flex items-center justify-center transition-all ${
                      isSelected
                        ? 'bg-white shadow-sm ring-2 ring-blue-500 scale-105'
                        : 'hover:bg-slate-200/60 active:scale-95'
                    }`}
                  >
                    {em}
                  </button>
                );
              })}
            </div>

            <div className="flex items-center gap-2 pt-1">
              <span className="text-xs text-slate-500">Custom emoji:</span>
              <input
                type="text"
                maxLength={4}
                value={emoji}
                onChange={(e) => {
                  setEmoji(e.target.value);
                  if (fieldErrors.emoji) {
                    setFieldErrors((prev) => {
                      const next = { ...prev };
                      delete next.emoji;
                      return next;
                    });
                  }
                }}
                aria-label="Custom emoji input"
                className="w-14 h-9 text-center text-lg rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            {fieldErrors.emoji && (
              <p data-form-error="true" className="text-[11px] font-medium text-red-600 animate-in fade-in">
                {fieldErrors.emoji}
              </p>
            )}
          </fieldset>

          {/* Frequency Selector */}
          <fieldset className="space-y-2.5 pb-6 border-0 p-0 m-0">
            <legend className="block text-xs font-bold text-slate-700">
              Frequency
            </legend>
            <div className="grid grid-cols-2 gap-2 p-1 bg-slate-100 rounded-xl">
              <button
                type="button"
                onClick={() => {
                  setFrequencyType('daily');
                  setFieldErrors((prev) => {
                    const next = { ...prev };
                    delete next.frequency_days;
                    delete next.frequency;
                    return next;
                  });
                }}
                aria-pressed={frequencyType === 'daily'}
                className={`min-h-[40px] text-xs font-semibold rounded-lg transition-all ${
                  frequencyType === 'daily'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Every day
              </button>
              <button
                type="button"
                onClick={handleSelectSpecificDays}
                aria-pressed={frequencyType === 'custom'}
                className={`min-h-[40px] text-xs font-semibold rounded-lg transition-all ${
                  frequencyType === 'custom'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Specific days
              </button>
            </div>

            {frequencyType === 'custom' && (
              <div ref={weekdaySectionRef} className="space-y-2 animate-in fade-in duration-150 pt-1">
                <p className="text-[11px] text-slate-500">Choose days of the week:</p>
                <div className="flex items-center justify-between gap-1">
                  {WEEKDAYS.map(({ day, label }) => {
                    const isSelected = frequencyDays.includes(day);
                    return (
                      <button
                        key={day}
                        type="button"
                        onClick={() => toggleWeekday(day)}
                        aria-pressed={isSelected}
                        aria-label={label}
                        className={`min-h-[44px] flex-1 rounded-xl text-xs font-bold transition-all ${
                          isSelected
                            ? 'bg-blue-600 text-white shadow-sm'
                            : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                        }`}
                      >
                        {label}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
            {(fieldErrors.frequency_days || fieldErrors.frequency) && (
              <p data-form-error="true" className="text-[11px] font-medium text-red-600 animate-in fade-in">
                {fieldErrors.frequency_days || fieldErrors.frequency}
              </p>
            )}
          </fieldset>

          {/* Bottom Actions */}
          <div className="pt-3 pb-[calc(0.5rem+env(safe-area-inset-bottom,0px))] sticky bottom-0 bg-white border-t border-slate-100 flex gap-2.5">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="flex-1 min-h-[44px] rounded-xl border border-slate-200 bg-white text-xs font-semibold text-slate-700 hover:bg-slate-50 active:bg-slate-100 transition disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 min-h-[44px] rounded-xl bg-blue-600 text-xs font-semibold text-white hover:bg-blue-700 active:bg-blue-800 transition shadow-sm flex items-center justify-center gap-1.5 disabled:opacity-50"
            >
              {isSubmitting ? (
                <div className="w-4 h-4 rounded-full border-2 border-white/60 border-t-white animate-spin" />
              ) : habit ? (
                'Save Changes'
              ) : (
                'Create Habit'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
