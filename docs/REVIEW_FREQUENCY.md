# Code Review: Phase 3 — Habit Frequency & Frequency-Aware Streaks

**Review Date**: 2026-10-23  
**Scope**: Habit frequency scheduling, frequency-aware streak calculation algorithms, data migration safety, input validation, query performance, and test coverage.  
**Review Target**: Phase 3 implementation (`apps/habits/models.py`, `apps/habits/services/streaks.py`, `apps/habits/services/checkin.py`, `apps/habits/serializers.py`, `apps/habits/views.py`, `apps/habits/migrations/0003_...`, and test suites).

---

## Executive Summary

Phase 3 introduces flexible habit scheduling (`daily` vs `custom` weekday selection) and updates the streak engine to account for rest days without resetting streaks. The algorithmic design cleanly decouples scheduled check-ins from bonus/off-schedule check-ins.

However, several critical and important issues require attention prior to moving forward into Phase 4 (Analytics):
1. **Critical infinite loop vulnerability** in backwards date traversal when encountering unrecognized frequency types or unvalidated custom schedules.
2. **Dead data migration logic** where existing rows are never touched by `set_existing_habits_daily` due to column defaults taking precedence.
3. **Silent data loss on `PATCH`** where updating `frequency_days` on an existing daily habit silently discards the user's payload without error.
4. **Double streak recalculation** on every check-in/uncheck due to overlapping post-save/post-delete signals and service-layer calls.
5. **In-memory table scan and N+1 query patterns** in the habit list endpoint when filtering by `scheduled_today` or evaluating historical dates.

---

## 1. Critical Priority

Issues that cause crashes, infinite loops, data loss, dead migration logic, or significant degradation in production.

### 1.1 Unbounded Infinite While Loop in Backwards Date Traversal [FIXED]
- **File**: [`apps/habits/services/streaks.py`](file:///c:/Users/monos.com.ua/.gemini/antigravity/scratch/habit_tracker/apps/habits/services/streaks.py#L94-L114)
- **Lines**: 94–96, 101–103, 112–113
- **Description**:
  When calculating streaks, `calculate_streaks()` traverses days backwards using `while not _is_scheduled_day(...)`:
  ```python
  last_scheduled = today - timedelta(days=1)
  while not _is_scheduled_day(last_scheduled, frequency_type, frequency_days):
      last_scheduled -= timedelta(days=1)
  ```
  `_is_scheduled_day` returns `False` if `frequency_type != "daily"` and `frequency_days` is empty or `None`.
  While line 82 checks `if frequency_type == "custom" and not frequency_days:`, any unrecognized `frequency_type` (e.g. `"weekly"`, `"monthly"`, or any invalid string), or `frequency_days=None`, will cause `_is_scheduled_day` to return `False` permanently. The while loop runs backwards unbounded until Python raises `OverflowError: date value out of range`, locking the worker thread and hanging the request indefinitely.
- **Recommendation**:
  1. Add a hard boundary check before the loop: if `frequency_type != "daily"` and not `frequency_days`, return `StreakResult(0, 0)`.
  2. Guard the while loops with a maximum lookback limit (e.g. `limit = 7` days, since any valid weekly cycle repeats within 7 days). If no scheduled day is found within 7 days, break.

---

### 1.2 Ineffective / Dead Data Migration Query [FIXED]
- **File**: [`apps/habits/migrations/0003_habit_frequency_days_habit_frequency_type.py`](file:///c:/Users/monos.com.ua/.gemini/antigravity/scratch/habit_tracker/apps/habits/migrations/0003_habit_frequency_days_habit_frequency_type.py#L6-L13)
- **Lines**: 6–13, 28–33
- **Description**:
  Operation 2 adds the `frequency_type` column with `default='daily'`:
  ```python
  migrations.AddField(
      model_name='habit',
      name='frequency_type',
      field=models.CharField(choices=[('daily', 'Daily'), ('custom', 'Custom')], default='daily', max_length=10),
  )
  ```
  In PostgreSQL and SQLite, Django immediately assigns `'daily'` to all existing rows upon column creation.
  Operation 3 then executes `RunPython(set_existing_habits_daily)`:
  ```python
  Habit.objects.filter(
      models.Q(frequency_type__isnull=True) | models.Q(frequency_type="")
  ).update(
      frequency_type="daily",
      frequency_days=[],
  )
  ```
  Because all rows already have `frequency_type='daily'`, the filter matches **zero rows**. Consequently, `frequency_days=[]` is never explicitly updated for existing rows, leaving `frequency_days` reliant entirely on database column default behavior rather than the data migration.
- **Recommendation**:
  Update `set_existing_habits_daily` to execute unconditionally across all rows (`Habit.objects.all().update(...)`), or filter `Habit.objects.filter(frequency_days__isnull=True)`.

---

### 1.3 Silent Erasure of Client Input on Partial Update (`PATCH`) [FIXED]
- **File**: [`apps/habits/serializers.py`](file:///c:/Users/monos.com.ua/.gemini/antigravity/scratch/habit_tracker/apps/habits/serializers.py#L135-L136)
- **Lines**: 135–136
- **Description**:
  In `HabitSerializer.validate()`, if a user submits a `PATCH` request with `{"frequency_days": [0, 2, 4]}` to an existing habit whose current `frequency_type` is `"daily"`:
  ```python
  elif freq_type == FrequencyType.DAILY:
      attrs["frequency_days"] = []
  ```
  Because `freq_type` falls back to `self.instance.frequency_type` (`"daily"`), the serializer silently overwrites `attrs["frequency_days"]` with `[]` without raising any validation error.
  The API responds with `200 OK`, but silently ignores the user's intended schedule modification.
- **Recommendation**:
  If `frequency_days` is provided in `attrs` while `freq_type == FrequencyType.DAILY`:
  - Either reject the request with a clear `ValidationError`: `{"frequency_days": "Cannot set frequency_days for a daily habit. Change frequency_type to 'custom'."}`.
  - Or automatically promote `frequency_type` to `custom` if `frequency_days` is non-empty.

---

### 1.4 Double Recalculation & Redundant DB Writes on Every Check-In/Uncheck [FIXED]
- **File**: [`apps/habits/models.py`](file:///c:/Users/monos.com.ua/.gemini/antigravity/scratch/habit_tracker/apps/habits/models.py#L179-L187), [`apps/habits/services/checkin.py`](file:///c:/Users/monos.com.ua/.gemini/antigravity/scratch/habit_tracker/apps/habits/services/checkin.py#L73)
- **Lines**: `models.py:179-187`, `checkin.py:73, 108`
- **Description**:
  When `check_in_habit()` creates a `HabitCheckIn` record:
  1. Django's `post_save` signal triggers `on_checkin_saved_or_deleted()`, which fetches `instance.habit`, reads all check-in dates from DB, calculates streaks, and calls `habit.save(update_fields=[...])`.
  2. Control returns to `check_in_habit()`, which immediately executes `recalculate_habit_streaks(habit, reference_date=today)`. This re-queries all check-in dates from the database and issues a second `habit.save(update_fields=[...])`.
  The exact same double execution occurs during `uncheck_habit()` via `post_delete`. Every check-in/uncheck action triggers two full streak recalculations and two DB writes.
- **Recommendation**:
  Consolidate streak recalculation responsibility:
  - If service functions (`check_in_habit`, `uncheck_habit`) manage streak recalculation explicitly, the signal should be disconnected or conditioned to avoid firing during service-driven updates.
  - Alternatively, keep recalculation strictly in the signal handler and remove duplicate calls from the services.

---

## 2. Important Priority

Issues affecting maintainability, query performance, edge-case consistency, and database indexing.

### 2.1 Full Table Scan and In-Memory Filtering for `?scheduled_today=` [FIXED]
- **File**: [`apps/habits/views.py`](file:///c:/Users/monos.com.ua/.gemini/antigravity/scratch/habit_tracker/apps/habits/views.py#L112-L124)
- **Lines**: 112–124
- **Description**:
  To filter habits scheduled today, `HabitViewSet.get_queryset()` runs an auxiliary query pulling all user habit IDs, `frequency_type`, and `frequency_days` into Python memory:
  ```python
  candidates = Habit.objects.filter(user=user)
  ...
  matching_ids = []
  for item in candidates.values("id", "frequency_type", "frequency_days"):
      ...
      if is_scheduled == want_scheduled:
          matching_ids.append(item["id"])
  qs = qs.filter(id__in=matching_ids)
  ```
  This creates an N-row memory load and generates an unnecessary `WHERE id IN (...)` subquery on every request.
- **Recommendation**:
  Filter directly in the ORM. In PostgreSQL (Phase 6 target), `frequency_days` is a `JSONField`/`JSONB` array:
  ```python
  if want_scheduled:
      qs = qs.filter(Q(frequency_type="daily") | Q(frequency_days__contains=target_weekday))
  else:
      qs = qs.filter(frequency_type="custom").exclude(frequency_days__contains=target_weekday)
  ```

---

### 2.2 Hidden Database Query on Every `Habit.save()` Call [FIXED]
- **File**: [`apps/habits/models.py`](file:///c:/Users/monos.com.ua/.gemini/antigravity/scratch/habit_tracker/apps/habits/models.py#L113-L122)
- **Lines**: 113–122
- **Description**:
  In `Habit.save()`, to detect frequency changes:
  ```python
  if update_fields is None or "frequency_type" in update_fields or "frequency_days" in update_fields:
      orig = Habit.objects.filter(pk=self.pk).values("frequency_type", "frequency_days").first()
  ```
  Whenever `habit.save()` is called without `update_fields` (standard throughout views, admin, and shell for updating `name`, `color`, `emoji`, etc.), an extra `SELECT` query is dispatched to fetch the original values from the DB.
- **Recommendation**:
  Store original values in model initialization (`__init__` / `from_db`) or track a `_loaded_values` dictionary to perform in-memory change detection without a database roundtrip.

---

### 2.3 Unhandled `TypeError` in `Habit.is_scheduled_on` if `frequency_days` is `None` [FIXED]
- **File**: [`apps/habits/models.py`](file:///c:/Users/monos.com.ua/.gemini/antigravity/scratch/habit_tracker/apps/habits/models.py#L86-L87)
- **Lines**: 86–87
- **Description**:
  `is_scheduled_on` executes:
  ```python
  weekday = target.weekday() if hasattr(target, "weekday") else target
  return weekday in self.frequency_days
  ```
  If `frequency_days` is `None` (possible when creating habits via ORM `Habit.objects.create(..., frequency_days=None)` or if raw data enters the DB), this raises `TypeError: argument of type 'NoneType' is not iterable`.
- **Recommendation**:
  Use defensive evaluation: `return weekday in (self.frequency_days or [])`.

---

### 2.4 Model `clean()` Not Executed on Direct Model `save()` [FIXED]
- **File**: [`apps/habits/models.py`](file:///c:/Users/monos.com.ua/.gemini/antigravity/scratch/habit_tracker/apps/habits/models.py#L53-L81), [`apps/habits/models.py#L99-L130`](file:///c:/Users/monos.com.ua/.gemini/antigravity/scratch/habit_tracker/apps/habits/models.py#L99-L130)
- **Lines**: 53–81, 99–130
- **Description**:
  Django models do not invoke `clean()` on `.save()`. Validation rules (such as custom frequency requiring at least one weekday, unique weekdays 0–6) are bypassed if habits are created or modified outside serializers (e.g. in fixtures, seed scripts, shell, or celery tasks).
- **Recommendation**:
  Call `self.full_clean()` inside `Habit.save()` before saving, or add database constraints (such as `CheckConstraint(check=Q(frequency_type__in=['daily', 'custom']))`).

---

### 2.5 Silent Fallback on Invalid `?scheduled_today=` Query Parameter [FIXED]
- **File**: [`apps/habits/views.py`](file:///c:/Users/monos.com.ua/.gemini/antigravity/scratch/habit_tracker/apps/habits/views.py#L105-L107)
- **Lines**: 105–107
- **Description**:
  `HabitViewSet.initial()` validates `?date=`, raising HTTP 400 if malformed. However, `?scheduled_today=` is not validated. If a client sends `?scheduled_today=invalid` or `?scheduled_today=yes`, it fails the check `if param in ["true", "1", "false", "0"]:` and is silently ignored, returning unfiltered results instead of `400 Bad Request`.
- **Recommendation**:
  Validate `scheduled_today` in `initial()` or via a query parameter serializer, raising a 400 error for unsupported boolean strings.

---

### 2.6 N+1 Query Risk on Past-Date Habit Serialization [FIXED]
- **File**: [`apps/habits/serializers.py`](file:///c:/Users/monos.com.ua/.gemini/antigravity/scratch/habit_tracker/apps/habits/serializers.py#L178), [`apps/habits/models.py#L150-L152`](file:///c:/Users/monos.com.ua/.gemini/antigravity/scratch/habit_tracker/apps/habits/models.py#L150-L152)
- **Lines**: `serializers.py:178, 183`, `models.py:150-152`
- **Description**:
  When a user requests `GET /habits/?date=YYYY-MM-DD` for a past date:
  1. `get_is_checked_today` executes `obj.check_ins.filter(date=target_date).exists()`.
  2. `get_current_streak` detects `last_check_in_date > reference_date` and calls `calculate_habit_streaks()`, executing `list(habit.check_ins.values_list("date", flat=True))`.
  Because `HabitViewSet.get_queryset()` does not prefetch check-ins, evaluating historical habit states fires $2N$ queries for $N$ habits.
- **Recommendation**:
  Add `Prefetch("check_ins")` when a historical `date` query parameter is present, or prefetch recent check-ins within the evaluated window.

---

### 2.7 Mixing DDL and DML in Migration 0003 [FIXED]
- **File**: [`apps/habits/migrations/0003_habit_frequency_days_habit_frequency_type.py`](file:///c:/Users/monos.com.ua/.gemini/antigravity/scratch/habit_tracker/apps/habits/migrations/0003_habit_frequency_days_habit_frequency_type.py#L22-L33)
- **Lines**: 22–33
- **Description**:
  Combining `AddField` (DDL) and `RunPython` (DML) in one migration file prolongs table-level exclusive locks in PostgreSQL. If the table grows large, this blocks concurrent reads and writes during migrations.
- **Recommendation**:
  Separate schema addition and data backfill into two migration steps (`0003_add_frequency_fields.py` and `0004_populate_daily_frequency.py`).

---

## 3. Nice-to-Have Priority

Minor cleanups, defensive improvements, and documentation polish.

### 3.1 Redundant Timezone Conversions per Serialized Item
- **File**: [`apps/habits/serializers.py`](file:///c:/Users/monos.com.ua/.gemini/antigravity/scratch/habit_tracker/apps/habits/serializers.py#L140-L152)
- **Lines**: 140–152
- **Description**:
  `_get_user_today()` is called independently for `get_is_checked_today`, `get_current_streak`, and `get_is_scheduled_today` on every habit. For a page of 50 habits, `user.get_today()` is invoked 150 times per request.
- **Recommendation**:
  Cache `user_today` in `self.context["user_today"]` on the first call.

---

### 3.2 Missing Database Index on `frequency_type`
- **File**: [`apps/habits/models.py`](file:///c:/Users/monos.com.ua/.gemini/antigravity/scratch/habit_tracker/apps/habits/models.py#L46-L48)
- **Lines**: 46–48
- **Description**:
  `Habit.Meta.indexes` indexes `["user", "is_archived", "-created_at"]`. Filtering active habits by frequency in Phase 4 analytics will trigger unindexed queries.
- **Recommendation**:
  Add a composite index on `["user", "frequency_type"]` or `["user", "is_archived", "frequency_type"]`.

---

### 3.3 OpenAPI Documentation for Shorthand `frequency` Field
- **File**: [`apps/habits/serializers.py`](file:///c:/Users/monos.com.ua/.gemini/antigravity/scratch/habit_tracker/apps/habits/serializers.py#L33)
- **Lines**: 33
- **Description**:
  `frequency = serializers.JSONField(required=False, write_only=True)` renders in Swagger/OpenAPI documentation as an untyped JSON object, giving API consumers no guidance on the shorthand format.
- **Recommendation**:
  Annotate with `@extend_schema_field` or provide `help_text="Frequency shorthand: 'daily' or list of weekday integers [0-6] (0=Monday)."`

---

## 4. Missing Edge-Case Tests

The following edge cases are currently omitted from the test suite:

| # | Test Scenario | Target File | Risk / Rationale |
|---|---|---|---|
| 1 | **Unrecognized `frequency_type` in `calculate_streaks`** | `tests/test_services.py` | Verify that unexpected strings do not cause an infinite while loop. |
| 2 | **Off-schedule check-in after missed scheduled day** | `tests/test_services.py` | Verify that checking in on Saturday when Friday was missed yields `current_streak = 0`. |
| 3 | **Single-day custom frequency (1 day/week) across 3 weeks** | `tests/test_services.py` | Verify streak continuity over 6-day rest gaps and breakage upon missed week. |
| 4 | **`PATCH` updating `frequency_days` without `frequency_type` on a daily habit** | `tests/test_frequency_serializers.py` | Guard against silent erasure of `frequency_days`. |
| 5 | **Invalid query param `?scheduled_today=notabool`** | `tests/test_views.py` | Verify API responds with 400 rather than silently returning all habits. |
| 6 | **User in non-UTC timezone filtering `?scheduled_today=true` near midnight** | `tests/test_views.py` | Verify habit list scheduling adheres to the requesting user's local day boundary. |
| 7 | **Custom habit with all 7 weekdays (`[0, 1, 2, 3, 4, 5, 6]`)** | `tests/test_services.py` | Verify identical streak behavior to daily habits. |
| 8 | **Direct ORM creation with `frequency_days=None`** | `tests/test_models.py` | Verify `is_scheduled_on` does not raise `TypeError`. |
| 9 | **Double signal execution check (query count assertion)** | `tests/test_services.py` | Ensure `check_in_habit` triggers streak recalculation only once. |
