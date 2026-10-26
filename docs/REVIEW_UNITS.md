# Code Review: Phase 8 (Measurable Habits with Units)

A prioritized code review of the Phase 8 backend and frontend implementation covering bugs, the shared `is_day_completed` helper, race conditions, decimal handling, migration safety, mobile UX, and missing tests.

---

## 1. Critical

### 1. [FIXED] Incomplete `checkins_map` breaks boolean habit completion in lists
- **File & Line**: `apps/habits/views.py:131-140` and `apps/habits/serializers.py:270-271, 284-286, 310-314`
- **Issue**: In `HabitViewSet.list()`, when `habits_list` contains at least one measurable habit, `context["checkins_map"]` is populated *only* with `measurable_ids` to avoid queries for boolean habits. However, `HabitSerializer.get_is_checked_today()`, `get_today_value()`, and `get_today_progress()` unconditionally assume that if `"checkins_map" in self.context`, any habit missing from the map has no check-in (`if not checkin: return False`). Consequently, whenever any measurable habit exists, all checked boolean habits on the user's dashboard incorrectly return `is_checked_today: false`, `today_value: 0.0`, and `today_progress: 0.0`.
- **Fix**: Either populate `checkins_map` for all habits in the list, or in `HabitSerializer` restrict the `checkins_map` check to `obj.habit_type == HabitType.MEASURABLE`.

### 2. [FIXED] Race condition on initial check-in creation (`IntegrityError`)
- **File & Line**: `apps/habits/services/checkin.py:98-103, 142-145`
- **Issue**: `HabitCheckIn.objects.select_for_update().filter(habit=habit, date=target_date).first()` returns `None` when no check-in row exists yet for that date. In PostgreSQL/SQLite, `select_for_update` on non-existent rows acquires no lock. Two rapid concurrent check-ins (e.g. quick "+" double-tap or concurrent API calls) will both see `checkin == None` and attempt `HabitCheckIn.objects.create(...)`, triggering an unhandled `django.db.IntegrityError` on `unique_habit_checkin_per_date` (HTTP 500) instead of atomic accumulation.
- **Fix**: Lock the parent `Habit` row (`Habit.objects.select_for_update().get(id=habit.id)`), or handle `IntegrityError` on creation by falling back to fetching and updating the existing row.

---

## 2. Important

### 3. [FIXED] Missing backfill migration for `last_check_in_value`
- **File & Line**: `apps/habits/migrations/0006_habit_last_check_in_value.py:16-18`
- **Issue**: Migration 0006 adds `last_check_in_value` with default `0.00` without backfilling existing habits. Existing habits that had check-ins on `user_today` retain `last_check_in_value = Decimal('0.00')`. When `get_today_value()` executes, it reads `0.0` instead of `1.0`.
- **Fix**: Add a data migration (`RunPython`) to backfill `last_check_in_value = Decimal('1.00')` for existing habits where `last_check_in_date is not None`.

### 4. [FIXED] Streak recalculation executed outside atomic transaction
- **File & Line**: `apps/habits/services/checkin.py:151, 224` and `apps/habits/services/streaks.py:236-244`
- **Issue**: `recalculate_habit_streaks(habit, ...)` runs after the check-in transaction commits, without locking the `Habit` instance. Under concurrent check-ins, two recalculations can interleave and save stale `current_streak` / `last_check_in_date` values to the database.
- **Fix**: Run `recalculate_habit_streaks` inside the transaction with `select_for_update` on `Habit`.

### 5. [FIXED] PATCH conversion from measurable to boolean fails validation
- **File & Line**: `apps/habits/serializers.py:121-160`
- **Issue**: `validate()` uses `attrs.get("target_value", self.instance.target_value)`. If a client sends `PATCH /habits/{id}/` with `{"habit_type": "boolean"}`, `target_value` retains its old numeric value (e.g. `5.00`), triggering validation error `"Target value cannot be set for boolean habits."` unless `target_value: null` and `unit: ""` are explicitly passed.
- **Fix**: If `habit_type` is updated to `"boolean"`, automatically clear `target_value` and `unit` or ignore previous instance values.

### 6. [FIXED] Mobile UX: Sub-standard touch targets on habit card actions
- **File & Line**: `frontend/src/components/HabitCard.tsx:230, 270`
- **Issue**: The "-" quick-decrement button is only 28x28px (`w-7 h-7`) and the "+" button is only 24x24px (`w-6 h-6`) separated by 4px (`gap-1`). This violates Apple HIG and Android Material guidelines (min 44x44px / 48x48px), causing frequent mis-taps on mobile touchscreens.
- **Fix**: Add padding or min-touch-target hitboxes (`min-w-[44px] min-h-[44px]`) to the action buttons.

### 7. [FIXED] Mobile UX / Accessibility: Invalid nested interactive controls
- **File & Line**: `frontend/src/components/HabitCard.tsx:111-123, 182-192`
- **Issue**: The exact amount `<button>` (and active `<input>`) is nested inside an outer card `<div role="button">` (which navigates to the detail page). In HTML and WAI-ARIA, interactive controls must not be nested. This confuses screen readers and risks triggering unintended card navigation when tapping the amount input.
- **Fix**: Separate the card navigation hit area from the progress/amount editing area so they are adjacent siblings, not nested.

### 8. [FIXED] Missing tests: Concurrency test is synchronous; mixed list unchecked
- **File & Line**: `apps/habits/tests/test_measurable_checkin.py:120-139` and `apps/habits/tests/test_measurable_api.py:214-240`
- **Issue**:
  - `test_atomic_concurrent_checkin_increments` runs 10 sequential calls in a single thread rather than true multi-threaded concurrent requests, masking the initial check-in `IntegrityError` race condition.
  - `test_habits_list_no_n_plus_one_queries` creates a mixed list of boolean and measurable habits but only asserts `len(results) == 5`, failing to verify `is_checked_today` or `today_progress` on the boolean habits (which masked Critical Bug #1).
- **Fix**: Add a multi-threaded test (using `ThreadPoolExecutor`) verifying concurrent check-in creation, and assert completion state on boolean habits in mixed lists.

---

## 3. Nice-to-Have

### 9. Shared helper `is_day_completed` returns True for `False` on boolean habits
- **File & Line**: `apps/habits/services/completion.py:27-32`
- **Issue**: For boolean habits, `if habit_type == "boolean": return True`. Because `False is not None` and `bool` subclasses `int` in Python, calling `is_day_completed(habit, False)` returns `True`.
- **Fix**: Explicitly check `if checkin_or_value is False or checkin_or_value is None: return False`.

### 10. Frontend missing client-side decimal places validation
- **File & Line**: `frontend/src/components/HabitFormBottomSheet.tsx:183-188` and `frontend/src/components/HabitCard.tsx:68-74`
- **Issue**: The form and card exact inputs do not validate that amounts have at most 2 decimal places before submitting, deferring rejection to an unhandled HTTP 400 backend error.
- **Fix**: Add a regex check (e.g. `/^\d+(\.\d{1,2})?$/`) in form and card validation.

### 11. Modal in HabitDetailPage missing Escape key listener & focus trapping
- **File & Line**: `frontend/src/pages/HabitDetailPage.tsx:695-755`
- **Issue**: The amount modal has no `onKeyDown` handler for `Escape` and does not trap focus, requiring keyboard users to tab all the way to "Cancel".
- **Fix**: Add an `Escape` key event listener and focus-trap logic.

### 12. Uncheck with `value=0` semantics
- **File & Line**: `apps/habits/services/checkin.py:202-205`
- **Issue**: Calling `POST /uncheck/` with `value: 0` is accepted as valid, resulting in `checkin.value - 0` (a no-op that returns HTTP 200).
- **Fix**: Reject `value=0` with HTTP 400 or treat it as an explicit day reset.
