# Habit Tracker — System Architecture & Implementation Plan

This document outlines the architectural blueprint, domain models, API contracts, business logic rules, testing methodology, and roadmap for building the **Habit Tracker** application.

---

## 1. System Overview & Technology Stack

The application is a web-based Habit Tracker with a Python backend and a decoupled frontend.

### 1.1 Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Language & Framework** | Python 3.12+, Django 5.x, Django REST Framework (DRF) 3.15+ | Mature ecosystem, robust ORM, rapid API development, built-in admin, first-class security. |
| **Local Database** | SQLite 3 | Zero configuration for local development and rapid test iteration. |
| **Production Database** | PostgreSQL 16+ | ACID compliance, strong date/time functions, production reliability on Render. |
| **Environment Config** | `django-environ` | 12-factor app compliance; clean separation of configuration and secrets via `.env`. |
| **Testing** | `pytest`, `pytest-django`, `freezegun`, `factory-boy` | Expressive fixtures, fast test execution, precise date-mocking for streak testing. |
| **Authentication (Phase 2)** | `djangorestframework-simplejwt` | Stateless token authentication ideal for decoupled mobile/web clients. |
| **Frontend (Phase 5)** | React 18+, Vite, Tailwind CSS, Lucide Icons | High-performance mobile-first single-page application (SPA). |
| **Containerization (Phase 6)** | Docker & Docker Compose | Consistent local and staging environments mirroring production. |
| **Hosting & Static Assets (Phase 7)** | Render.com (Web Service + Managed Postgres), Gunicorn, WhiteNoise | Straightforward PaaS deployment with efficient static file serving. |

---

## 2. Project and App Structure

The codebase adheres to the Django "thin views, fat models / rich services" architectural pattern, with business logic decoupled into a dedicated `services` layer.

```
habit_tracker/
├── manage.py
├── pytest.ini
├── .env.example
├── .gitignore
├── requirements/
│   ├── base.txt
│   ├── local.txt
│   └── production.txt
├── docs/
│   ├── PLAN.md
│   └── PROGRESS.md
├── config/                          # Project configuration root
│   ├── __init__.py
│   ├── asgi.py
│   ├── wsgi.py
│   ├── urls.py                      # Main URL routing and API v1 include
│   └── settings/
│       ├── __init__.py
│       ├── base.py                  # Common settings (apps, middleware, DRF, auth)
│       ├── local.py                 # SQLite, DEBUG=True, console email backend
│       └── production.py            # PostgreSQL, DEBUG=False, WhiteNoise, secure cookies
└── apps/
    ├── habits/                      # Core Domain App (Habits, Check-ins, Streaks)
    │   ├── __init__.py
    │   ├── apps.py
    │   ├── admin.py                 # Django admin registration
    │   ├── models.py                # Habit and HabitCheckIn models
    │   ├── serializers.py           # DRF input/output serializers
    │   ├── urls.py                  # DefaultRouter and endpoint routes
    │   ├── views.py                 # HabitViewSet and CheckIn actions
    │   ├── services/                # Pure business logic isolated from HTTP/DRF
    │   │   ├── __init__.py
    │   │   ├── streaks.py           # Current/longest streak calculation algorithms
    │   │   └── statistics.py        # Completion rate analytics (Phase 4)
    │   └── tests/                   # Strict TDD test suite
    │       ├── __init__.py
    │       ├── conftest.py          # Fixtures, APIClient, mock dates
    │       ├── factories.py         # FactoryBoy factories for Habit & HabitCheckIn
    │       ├── test_models.py       # Model constraints and validations
    │       ├── test_services.py     # Pure algorithmic tests for streak engine
    │       └── test_views.py        # API endpoint status codes and payloads
    └── accounts/                    # Auth App (Phase 2)
        ├── __init__.py
        ├── apps.py
        ├── models.py                # Custom User model
        ├── serializers.py           # Register, Login, Profile serializers
        ├── urls.py                  # Token obtain/refresh routes
        └── tests/
```

### 2.1 Separation of Responsibilities

- **Models (`models.py`)**: Data representation, database constraints, field types, and simple queries.
- **Services (`services/`)**: Core domain calculations (e.g., streak counting, frequency schedule matching, stats aggregation). Completely decoupled from request/response objects to ensure testability.
- **Serializers (`serializers.py`)**: Input parsing, validation (e.g. rejecting future dates), and serialization formatting.
- **Views / ViewSets (`views.py`)**: Thin controllers handling HTTP authentication, permissions, filtering, and invoking services.
- **Settings (`config/settings/`)**: Loaded dynamically based on `DJANGO_SETTINGS_MODULE`. Secrets are never hardcoded and read strictly via `environ.Env`.

---

## 3. Models, Relationships, Constraints & Migrations

### 3.1 Entity Relationship Diagram (ERD)

```mermaid
erDiagram
    USER ||--o{ HABIT : "owns (Phase 2)"
    HABIT ||--o{ HABIT_CHECKIN : "has many"

    USER {
        bigint id PK
        string email UK
        string password
        datetime date_joined
    }

    HABIT {
        bigint id PK
        bigint user_id FK "nullable in MVP, required in Phase 2"
        string name
        text description
        string color
        string emoji
        boolean is_archived
        datetime created_at
        datetime updated_at
    }

    HABIT_CHECKIN {
        bigint id PK
        bigint habit_id FK
        date date
        datetime created_at
    }
```

### 3.2 Model Specifications

#### `Habit`
Represents an ongoing habit tracked by the user.

- `id`: `BigAutoField`, Primary Key.
- `user`: `ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='habits', null=True, blank=True)`
  - *Migration Note*: Nullable during MVP (Phase 1); made non-nullable with a data migration in Phase 2 when JWT auth is added.
- `name`: `CharField(max_length=200)` — Short, descriptive title (e.g. "Drink 2L Water").
- `description`: `TextField(blank=True, default='')` — Optional context or motivation.
- `color`: `CharField(max_length=7, default='#3B82F6')` — Hex color code for mobile/web UI cards.
- `emoji`: `CharField(max_length=16, default='🎯')` — Icon representation.
- `is_archived`: `BooleanField(default=False)` — Soft-archive state. Archived habits do not appear in the daily dashboard but retain streak history.
- `created_at`: `DateTimeField(auto_now_add=True)`
- `updated_at`: `DateTimeField(auto_now=True)`

**Indexes & Ordering:**
- Meta ordering: `['-created_at']`
- Indexes: `models.Index(fields=['is_archived', 'created_at'])`

---

#### `HabitCheckIn`
Represents the completion record of a habit on a specific calendar day.

- `id`: `BigAutoField`, Primary Key.
- `habit`: `ForeignKey('habits.Habit', on_delete=models.CASCADE, related_name='check_ins')`
- `date`: `DateField` — The date the habit was satisfied.
- `created_at`: `DateTimeField(auto_now_add=True)` — Timestamp when the check-in was registered.

**Constraints & Validation:**
- **Unique Constraint**: A habit can only be checked in once per day:
  ```python
  constraints = [
      models.UniqueConstraint(
          fields=['habit', 'date'],
          name='unique_habit_checkin_per_date'
      )
  ]
  ```
- **Future Date Constraint**: Check-ins cannot be created for dates ahead of current local time:
  - Enforced at model `clean()` level, serializer validation, and database `CheckConstraint` (e.g. `check=models.Q(date__lte=datetime.date.today)`).
- **Index**:
  - `models.Index(fields=['habit', 'date'])`
  - Meta ordering: `['-date']`

### 3.3 Database Migrations Strategy

1. **Deterministic Auto-Generated Migrations**:
   - Every schema change must have a test verifying it can apply and unapply (`migrate` and `migrate <app> zero`).
2. **Phase 2 Auth Migration Strategy**:
   - In MVP (Phase 1), `user` is defined with `null=True, blank=True` to allow CRUD without auth.
   - In Phase 2:
     - Step 2a: Introduce the custom User model.
     - Step 2b: Data migration creates a default user or maps legacy unassigned habits.
     - Step 2c: Alter `user` field to `null=False`.
3. **No Raw SQL Workarounds**:
   - All constraints (uniqueness, date constraints) are managed via Django's declarative `Meta.constraints` framework for cross-database compatibility (SQLite in dev, PostgreSQL in prod).

---

## 4. REST API Endpoints Specification

Base Path: `/api/v1`

### 4.1 Summary of Endpoints

| Method | Endpoint | Description | Status Codes |
|---|---|---|---|
| `GET` | `/api/v1/habits/` | List all active habits (includes streak summary) | `200 OK` |
| `POST` | `/api/v1/habits/` | Create a new habit | `201 Created`, `400 Bad Request` |
| `GET` | `/api/v1/habits/{id}/` | Retrieve habit details, streak stats, recent check-ins | `200 OK`, `404 Not Found` |
| `PUT` | `/api/v1/habits/{id}/` | Full update of habit details | `200 OK`, `400 Bad Request`, `404 Not Found` |
| `PATCH` | `/api/v1/habits/{id}/` | Partial update of habit details | `200 OK`, `400 Bad Request`, `404 Not Found` |
| `DELETE` | `/api/v1/habits/{id}/` | Permanently delete habit and its check-ins | `204 No Content`, `404 Not Found` |
| `POST` | `/api/v1/habits/{id}/archive/` | Soft-archive habit | `200 OK`, `404 Not Found` |
| `POST` | `/api/v1/habits/{id}/unarchive/` | Restore habit from archive | `200 OK`, `404 Not Found` |
| `POST` | `/api/v1/habits/{id}/check/` | Check in habit for a specific date (defaults to today) | `201 Created`, `200 OK` (idempotent), `400 Bad Request` |
| `POST` | `/api/v1/habits/{id}/uncheck/` | Undo check-in for a specific date | `200 OK` / `204 No Content`, `404 Not Found` |
| `GET` | `/api/v1/habits/{id}/check-ins/` | List check-in history with optional `?from=&to=` query params | `200 OK`, `404 Not Found` |

---

### 4.2 Endpoint Details & Request / Response Payloads

#### 1. List Habits (`GET /api/v1/habits/`)
Query Parameters:
- `include_archived` (boolean, optional, default: `false`)
- `date` (ISO date `YYYY-MM-DD`, optional, default: today) — determines `is_checked_today` field in response.

Response (`200 OK`):
```json
[
  {
    "id": 1,
    "name": "Drink Water",
    "description": "Drink at least 2 liters of water daily",
    "color": "#3B82F6",
    "emoji": "💧",
    "is_archived": false,
    "current_streak": 5,
    "longest_streak": 14,
    "is_checked_today": true,
    "created_at": "2026-10-20T10:00:00Z",
    "updated_at": "2026-10-22T08:15:00Z"
  }
]
```

#### 2. Create Habit (`POST /api/v1/habits/`)
Request Body:
```json
{
  "name": "Morning Meditation",
  "description": "10 minutes of mindfulness",
  "color": "#10B981",
  "emoji": "🧘"
}
```

Response (`201 Created`):
```json
{
  "id": 2,
  "name": "Morning Meditation",
  "description": "10 minutes of mindfulness",
  "color": "#10B981",
  "emoji": "🧘",
  "is_archived": false,
  "current_streak": 0,
  "longest_streak": 0,
  "is_checked_today": false,
  "created_at": "2026-10-22T20:30:00Z",
  "updated_at": "2026-10-22T20:30:00Z"
}
```

#### 3. Check-In (`POST /api/v1/habits/{id}/check/`)
Request Body:
```json
{
  "date": "2026-10-22"
}
```
*(If `date` is omitted, server uses current date in request timezone).*

Response (`201 Created` or `200 OK` if already checked):
```json
{
  "status": "checked",
  "habit_id": 1,
  "date": "2026-10-22",
  "current_streak": 6,
  "longest_streak": 14
}
```

Validation Error — Future Date (`400 Bad Request`):
```json
{
  "date": ["Check-ins cannot be recorded for future dates."]
}
```

#### 4. Undo Check-In (`POST /api/v1/habits/{id}/uncheck/`)
Request Body:
```json
{
  "date": "2026-10-22"
}
```

Response (`200 OK`):
```json
{
  "status": "unchecked",
  "habit_id": 1,
  "date": "2026-10-22",
  "current_streak": 5,
  "longest_streak": 14
}
```

Response if not checked (`404 Not Found` or `400 Bad Request`):
```json
{
  "detail": "No check-in found for habit 1 on 2026-10-22."
}
```

#### 5. Archive / Unarchive (`POST /api/v1/habits/{id}/archive/` & `/unarchive/`)
Response (`200 OK`):
```json
{
  "id": 1,
  "is_archived": true
}
```

---

## 5. Streak Calculation Engine & Edge Cases

The streak calculation logic is housed in `apps.habits.services.streaks` to guarantee purity, speed, and unit-testability without touching the HTTP layer.

### 5.1 Business Rules & Definitions

1. **Streak Unit**: One day (calendar date).
2. **Current Streak**:
   - The number of consecutive days with recorded check-ins leading up to either **Today** or **Yesterday**.
   - **Case A: Today is checked**: Streak includes Today and consecutive prior days.
   - **Case B: Today is not checked yet, but Yesterday is checked**: The streak is **active** (not broken), because the user still has time to check in today. Current streak is the consecutive days ending Yesterday.
   - **Case C: Neither Today nor Yesterday is checked**: The streak has lapsed. Current streak is `0`.
3. **Scheduled Frequency & Rest Days**:
   - Habits can be scheduled as "daily" or for specific weekdays (list of 0–6, Monday=0).
   - Streaks count only scheduled days: off-schedule days never break a streak.
   - A check-in on an off-schedule day is allowed (e.g. bonus check-in on Saturday for a weekday habit) but does not affect the streak count or streak continuity.
   - **Current streak with custom frequency**:
     - If today is a scheduled day:
       - If today is checked, current streak counts consecutive scheduled days through today.
       - If today is not checked yet, the streak is still alive (unbroken) based on the preceding scheduled days.
     - If today is an off-schedule day:
       - The streak is still alive based on the most recent scheduled days.
4. **Longest Streak Ever**:
   - The maximum consecutive block of checked-in scheduled dates in the habit's entire history.
   - Always $\ge$ Current Streak.
5. **Undo Operation**:
   - Removing a check-in instantly recalculates streaks. If today's check-in is undone and yesterday was checked, streak reverts to yesterday's count. If an intermediate date is removed, it splits one streak into two.

### 5.2 Algorithmic Logic & Edge Cases

```
Check-In Dates Set: S = {d_1, d_2, ..., d_n} (unique dates)
Target Date (Today): T
Yesterday: Y = T - 1 day

Current Streak:
  if T in S:
      start_date = T
  elif Y in S:
      start_date = Y
  else:
      return 0

  streak = 0
  cursor = start_date
  while cursor in S:
      streak += 1
      cursor = cursor - 1 day
  return streak

Longest Streak:
  if S is empty:
      return 0
  sorted_dates = sorted(S)
  max_streak = 1
  curr_streak = 1
  for i in range(1, len(sorted_dates)):
      if sorted_dates[i] == sorted_dates[i - 1] + 1 day:
          curr_streak += 1
      elif sorted_dates[i] == sorted_dates[i - 1]:
          continue # duplicate protection
      else:
          curr_streak = 1
      if curr_streak > max_streak:
          max_streak = curr_streak
  return max_streak
```

### 5.3 Edge Cases Matrix

| Case | Dates Checked | Today | Current Streak | Longest Streak | Rationale |
|---|---|---|---|---|---|
| **Empty History** | None | 2026-10-22 | 0 | 0 | Brand new habit. |
| **Only Today** | `[2026-10-22]` | 2026-10-22 | 1 | 1 | Checked today. |
| **Only Yesterday** | `[2026-10-21]` | 2026-10-22 | 1 | 1 | Today still open; streak unbroken. |
| **Two Days Ago (Broken)** | `[2026-10-20]` | 2026-10-22 | 0 | 1 | Yesterday was missed; streak resets. |
| **Consecutive Past Block** | `[2026-10-18, 19, 20]` | 2026-10-22 | 0 | 3 | Lapsed, but longest preserves historical record. |
| **Active Multi-Day** | `[2026-10-20, 21, 22]` | 2026-10-22 | 3 | 3 | All consecutive through today. |
| **Unchecked Today Multi-Day** | `[2026-10-19, 20, 21]` | 2026-10-22 | 3 | 3 | Unchecked today, but contiguous through yesterday. |
| **Gap in Past** | `[2026-10-15, 16, 17, 18, 20, 21, 22]` | 2026-10-22 | 3 | 4 | Longest was 4 (15th-18th); current is 3 (20th-22nd). |
| **Undo Today** | Was `[2026-10-21, 22]`, uncheck 22 | 2026-10-22 | 1 | 2 | Current reverts to 1 (yesterday still valid). |

### 5.4 Timezone & Date Boundary Handling (`USE_TZ = True`)

- Django operates with `USE_TZ = True`.
- `HabitCheckIn.date` is a `DateField` (pure calendar date: `YYYY-MM-DD`), avoiding timestamp drift and daylight saving bugs.
- **Reference Date Resolution**:
  - The API allows the client to pass their local reference date (e.g. `POST /api/v1/habits/1/check/ {"date": "2026-10-22"}`).
  - If omitted, server computes `today` using the request's timezone (via `django.utils.timezone.localdate()` or an optional `X-Timezone` header, defaulting to `TIME_ZONE = 'UTC'`).
  - Validation ensures `date <= localdate()` to prevent future check-ins.

---

## 6. Feature Roadmap Split into Small Steps

Each step is independent, test-driven, verifiable, and yields a working, deployable state.

### Step 1: MVP Core (Habits CRUD + Check-ins + Streaks)
- **Scope**:
  - Django project setup with `config/settings/` (using `django-environ`), SQLite.
  - `habits` app with `Habit` and `HabitCheckIn` models + unique constraints.
  - `apps.habits.services.streaks` calculation module.
  - ModelAdmin registration for Django Admin.
  - DRF `HabitViewSet` with list, create, retrieve, update, delete, archive, unarchive, check, uncheck actions.
  - Full pytest-django test suite covering models, streak engine, and API client tests.
- **Deliverable**: Complete REST API running locally with SQLite and 100% passing tests.

---

### Step 2: JWT Authentication & User Scoping
- **Scope**:
  - Install and configure `djangorestframework-simplejwt`.
  - Custom User model (`accounts.User`) with email as username.
  - Auth endpoints: `/api/v1/auth/register/`, `/api/v1/auth/token/`, `/api/v1/auth/token/refresh/`.
  - Associate `Habit.user` (ForeignKey to User).
  - Scope queries in `HabitViewSet` so users only ever see, modify, or check their own habits:
    `queryset.filter(user=request.user)`.
  - Enforce `IsAuthenticated` by default in DRF settings.
- **Deliverable**: Secure multi-user API with token auth and complete data isolation.

---

### Step 3: Habit Frequency (Scheduled Weekdays)
- **Scope**:
  - Extend `Habit` model with `frequency_type` (`daily`, `custom_days`) and `frequency_days` (e.g., bitmask or array of weekday integers `[0, 2, 4]` for Mon/Wed/Fri).
  - Update streak calculation engine: non-scheduled days are skipped rather than breaking the streak!
    *(Example: A Mon/Wed/Fri habit completed on Friday and Monday keeps a continuous streak across the weekend).*
  - Update serializers, validation rules, and comprehensive streak tests for scheduled habits.
- **Deliverable**: Flexible habit scheduling without penalizing rest days.

---

### Step 4: Statistics & Analytics (Weekly / Monthly Completion)
- **Scope**:
  - Add statistics endpoint: `GET /api/v1/habits/{id}/statistics/` and `GET /api/v1/statistics/summary/`.
  - Metrics:
    - Current week completion rate (e.g., $4/7 = 57\%$).
    - Current month completion rate.
    - Total check-ins all time.
    - Heatmap data representation for UI calendar grids.
  - Optimized database aggregation queries (`Count`, `TruncDate`) to avoid N+1 query overhead.
- **Deliverable**: Analytical insights endpoint ready for frontend charts and calendar views.

---

### Step 5: Mobile-First React UI (Vite)
- **Scope**:
  - Initialize Vite + React + TypeScript + Tailwind CSS in `frontend/`.
  - Mobile-first responsive layout (bottom navigation, swipeable cards, dark/light mode).
  - State management & API client (Axios / TanStack Query) handling JWT persistence in `localStorage` / memory.
  - Habit Card component:
    - Tap-to-check / undo toggle with immediate optimistic UI updates.
    - Visual streak flame indicator (`🔥 5 days`).
    - Color and emoji badges.
  - Habits creation/edit modal and archive drawer.
- **Deliverable**: Sleek, responsive mobile PWA/web app consuming the Django API.

---

### Step 6: Docker & Docker Compose with PostgreSQL
- **Scope**:
  - Multi-stage `Dockerfile` for Django backend (Python 3.12-slim, non-root user).
  - `docker-compose.yml` orchestrating:
    - `web`: Django API with Gunicorn / dev reload.
    - `db`: PostgreSQL 16 with persistent volume.
  - Database connection string wired through `DATABASE_URL` via `django-environ`.
  - Container healthchecks and entrypoint script running automatic migrations.
- **Deliverable**: One-command reproducible local & staging development environment (`docker compose up --build`).

---

### Step 7: Cloud Deployment on Render.com
- **Scope**:
  - Configure `WhiteNoise` for efficient static asset serving in Django.
  - Add `render.yaml` (Infrastructure-as-Code blueprint) defining:
    - Web Service (Python environment, `gunicorn config.wsgi:application`).
    - Managed PostgreSQL Database instance.
    - Automatic migration command (`python manage.py migrate`) in pre-deploy / build command.
  - Secure production settings: HTTPS redirects, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `ALLOWED_HOSTS`.
- **Deliverable**: Live, production-ready Habit Tracker web app on Render.com.

---

### Step 8: Measurable Habits with Units
- **Scope**:
  - Distinguish between **boolean** habits (completed / not completed) and **measurable** habits (target quantity + unit).
  - Habit model configuration: `habit_type` (`boolean` vs `measurable`), `unit` (e.g. `ml`, `pages`, `minutes`, `steps`), and `target_value` (e.g. `2000`, `30`).
  - Incremental check-ins: users can check in multiple times per day with incremental amounts; daily check-in values are summed.
  - Day completion criteria: a measurable habit is satisfied on a given date if and only if `sum(values) >= target_value`.
  - Streak engine & statistics integration: streaks and completion rates adapt seamlessly using the `is_day_completed` abstraction.
  - Frontend UI: progress bars for measurable cards (e.g. `1200 / 2000 ml`), quick-add increment buttons (+250ml, custom input), and visual state transitions upon reaching target.
- **Data Model Changes**:
  - `Habit`:
    - `habit_type`: `CharField(max_length=20, choices=[('boolean', 'Boolean'), ('measurable', 'Measurable')], default='boolean')`
    - `target_value`: `DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)`
    - `unit`: `CharField(max_length=30, blank=True, default='')`
    - Model validation: `target_value > 0` and non-empty `unit` required if `habit_type == 'measurable'`.
  - `HabitCheckIn`:
    - `value`: `DecimalField(max_digits=10, decimal_places=2, default=1.0)`
    - Relax unique constraint from `(habit, date)` to allow multiple check-in logs per day, OR maintain a daily aggregated check-in with check-in log records. (Preferred: Keep `HabitCheckIn` per date with `value` representing the daily accumulated total, or add `HabitCheckInLog` for multi-log entries summed into `HabitCheckIn.value`).
- **Endpoints**:
  - `POST /api/v1/habits/`: Accept `habit_type`, `target_value`, `unit`.
  - `POST /api/v1/habits/{id}/check/`: Accept optional `value` payload (e.g. `{"date": "2026-10-26", "value": 500}`). For measurable habits, increments the day's accumulated value. Returns current accumulated value, target, and completion status.
  - `POST /api/v1/habits/{id}/uncheck/`: Reset or decrement today's check-in value.
  - `GET /api/v1/habits/` & `GET /api/v1/habits/{id}/`: Expose `habit_type`, `target_value`, `unit`, `today_value`, and `is_checked_today` (`today_value >= target_value`).
- **Testing Strategy**:
  - Unit tests for validation: negative or zero target values rejected; measurable habit requires unit and target.
  - Streak service unit tests: partial completion does not count towards streak; reaching/exceeding target counts as satisfied day; decrementing below target lapses streak if today/yesterday.
  - Integration tests for `check` action: verifying sequential check-ins sum properly (e.g. 500 + 700 = 1200 / 1000 => completed).
  - Statistics tests: verify weekly/monthly rates compute based on threshold satisfaction.
- **Risks & Mitigations**:
  - *Risk*: Migration of existing boolean check-ins breaking streak calculations.
    *Mitigation*: Default existing check-in `value` to `1.0` and default existing habits to `habit_type='boolean'` with `target_value=1.0`.
  - *Risk*: Floating point rounding issues with fractional units (e.g. kilometers, liters).
    *Mitigation*: Use `DecimalField` instead of `FloatField` for exact decimal arithmetic.
  - *Risk*: Race conditions during simultaneous concurrent check-ins summing amounts.
    *Mitigation*: Use Django ORM `F()` expressions or database-level row locking (`select_for_update()`).

---

### Step 9: Email Notifications via Mailgun
- **Scope**:
  - Transactional and reminder email dispatch using the Mailgun API.
  - User-configurable daily reminders delivered at user's chosen local time (e.g. 20:00).
  - Weekly summary email (completion percentages, streaks preserved, habits needing attention) delivered every Monday.
  - Per-user notification preferences and one-click direct unsubscribe links with signed tokens.
  - Scheduled dispatch engine driven by a custom Django management command (`python manage.py send_habit_reminders`) invoked periodically by a cron scheduler (e.g. Render Cron Job / Celery Beat).
  - Strict security: Mailgun API keys, domain, and webhooks secrets stored exclusively in environment variables (`.env`).
- **Data Model Changes**:
  - `accounts.User` (or dedicated `UserNotificationSettings` one-to-one model):
    - `email_notifications_enabled`: `BooleanField(default=True)`
    - `daily_reminder_enabled`: `BooleanField(default=True)`
    - `daily_reminder_time`: `TimeField(default='20:00:00')` (in user's local timezone)
    - `weekly_summary_enabled`: `BooleanField(default=True)`
    - `unsubscribe_token`: `UUIDField(default=uuid.uuid4, unique=True)`
  - Optional `EmailLog` model to track sent emails and prevent duplicate deliveries within the same dispatch window.
- **Endpoints**:
  - `GET /api/v1/notifications/settings/`: Retrieve user notification preferences.
  - `PATCH /api/v1/notifications/settings/`: Update notification preferences (toggle daily reminder, change reminder time, toggle weekly summary).
  - `GET /api/v1/notifications/unsubscribe/{token}/`: Public one-click unsubscribe endpoint disabling email notifications for the corresponding user.
- **Testing Strategy**:
  - Mock Mailgun HTTP client / `Anymail` backend during testing; verify outgoing payload, headers, and recipient.
  - Timezone dispatch unit tests: freeze time across multiple UTC hours and assert that only users whose local clock matches `daily_reminder_time` receive emails.
  - Unsubscribe integration test: token lookup updates user preferences and disables future sends.
  - Edge cases: user with 0 active habits, user with all habits already completed today (skip daily reminder or send congratulations).
- **Risks & Mitigations**:
  - *Risk*: Spamming users due to scheduler retries or overlapping cron executions.
    *Mitigation*: Implement idempotency locks (cache or `EmailLog` records tagged by date and user) to guarantee at most one reminder per user per day.
  - *Risk*: Timezone shift / daylight saving misalignments.
    *Mitigation*: Always evaluate current time in the user's saved `timezone` attribute (e.g. `zoneinfo.ZoneInfo(user.timezone)`).
  - *Risk*: Leaking Mailgun API keys.
    *Mitigation*: Strictly validate `.env` configuration; enforce rejection of hardcoded secrets via pre-commit and settings validation.

---

### Step 10: AI Habit Coach Chatbot via Google Gemini
- **Scope**:
  - Dedicated "Coach" / "AI Assistant" chat interface in the frontend app.
  - Backend proxy endpoint orchestrating conversations with the Google Gemini API (Gemini Flash).
  - Backend-only API key security (client never has access to the Gemini secret key).
  - Enriched context injection: prompt includes the user's active habits, current/longest streaks, frequency, and recent 7-day completion rates.
  - Read-only coaching advice: the AI provides motivation, streak repair strategies, habit-stacking advice, and reflection prompts; it cannot directly alter user data.
  - Daily rate limits: strictly enforced daily message quota per user (e.g. 10 messages/day) to prevent API credit exhaustion.
  - Conversation history: persistent chat message history stored in DB.
  - Security & prompt injection defenses: sanitize user inputs, system prompt system instructions enforcing boundary constraints, and refusal to process non-habit instructions.
- **Data Model Changes**:
  - `CoachConversation`:
    - `id`: `BigAutoField`, PK
    - `user`: `ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='coach_conversations')`
    - `created_at`: `DateTimeField(auto_now_add=True)`
  - `CoachMessage`:
    - `id`: `BigAutoField`, PK
    - `conversation`: `ForeignKey(CoachConversation, on_delete=models.CASCADE, related_name='messages')`
    - `sender`: `CharField(max_length=10, choices=[('user', 'User'), ('assistant', 'Assistant')])`
    - `content`: `TextField()`
    - `created_at`: `DateTimeField(auto_now_add=True)`
  - User daily quota tracker: track message counts per date via Redis or relational `CoachMessage` count for `created_at__date=today`.
- **Endpoints**:
  - `GET /api/v1/coach/messages/`: Retrieve user's recent chat history.
  - `POST /api/v1/coach/chat/`: Send a message to the AI coach. Payload: `{"message": "How can I improve my reading habit?"}`. Returns assistant reply and remaining daily message quota.
  - `DELETE /api/v1/coach/history/`: Clear conversation history.
- **Testing Strategy**:
  - Mock Gemini API client/responses in backend test suite to test response handling without network calls.
  - Test daily message rate limiting: 11th message returns `429 Too Many Requests`.
  - Context assembly unit tests: verify prompt serializer correctly aggregates habits, streaks, and completion percentages.
  - Prompt injection safeguard tests: verify that prompt formatting keeps user input distinct from system instructions.
- **Risks & Mitigations**:
  - *Risk*: Excessive API billing or abuse.
    *Mitigation*: Hard limits on daily message count per user, strict max token output limit, and backend timeout configuration.
  - *Risk*: AI hallucinating nonexistent user habits or check-in stats.
    *Mitigation*: Feed clean, structured JSON summaries of current habits and stats directly into the system prompt context.
  - *Risk*: Prompt injection jailbreaks attempting to bypass habit coach persona.
    *Mitigation*: Use Gemini system instructions and role separation; strip control characters; enforce clear persona boundaries in the system prompt.

---

### Step 11: Webhooks (Pending Mentor Clarification)
- **Scope**:
  - Architectural hooks for handling asynchronous event notifications and integrations.
  - *Candidate Integration A*: **Stripe Payments** (e.g. webhook handling for subscription lifecycle: `checkout.session.completed`, `customer.subscription.deleted`, updating user premium tier).
  - *Candidate Integration B*: **Mailgun Event Tracking** (e.g. delivery receipts, bounces, spam complaints, unsubscribe events: `opened`, `clicked`, `failed`).
  - *Candidate Integration C*: **Outgoing User Webhooks** (e.g. dispatching webhook payloads to user endpoints on habit completed, streak milestone reached, or streak lost).
  - *Status*: **Pending mentor clarification** to finalize requirements and direction.
- **Data Model Changes**:
  - `WebhookEvent` (incoming log):
    - `id`: `BigAutoField`, PK
    - `provider`: `CharField(max_length=50)` (e.g. `mailgun`, `stripe`)
    - `event_id`: `CharField(max_length=255, unique=True)`
    - `event_type`: `CharField(max_length=100)`
    - `payload`: `JSONField()`
    - `status`: `CharField(choices=[('pending', 'Pending'), ('processed', 'Processed'), ('failed', 'Failed')])`
    - `received_at`: `DateTimeField(auto_now_add=True)`
  - *If Outgoing*: `WebhookSubscription` (user, target_url, secret, events list, is_active).
- **Endpoints**:
  - `POST /api/v1/webhooks/mailgun/`: Mailgun event receiver with cryptographic signature verification.
  - `POST /api/v1/webhooks/stripe/`: Stripe webhook receiver with signature header verification.
  - *If Outgoing*: CRUD on `/api/v1/webhooks/subscriptions/`.
- **Testing Strategy**:
  - Signature verification test cases (valid secret vs forged signatures returning 400/403).
  - Idempotency test: duplicate `event_id` deliveries do not re-execute business logic and return `200 OK`.
  - Malformed payload rejection tests.
- **Risks & Mitigations**:
  - *Risk*: Replay attacks and unauthorized calls to webhook endpoints.
    *Mitigation*: Strict signature verification using provider HMAC secret keys; reject requests older than timestamp tolerance (e.g. 5 minutes).
  - *Risk*: Webhook handler blocking HTTP worker during heavy processing.
    *Mitigation*: Return `200 OK` immediately after recording event to DB and delegate business execution to an asynchronous background worker.

---

## 7. Testing Strategy & Strict TDD Workflow

We adhere to **Strict Test-Driven Development (TDD)** across all features:

```mermaid
flowchart LR
    A["1. Red: Write failing test"] --> B["2. Green: Implement minimal code"]
    B --> C["3. Refactor: Clean up & optimize"]
    C --> A
```

### 7.1 Testing Pyramid

1. **Unit Tests (`test_services.py`)**:
   - Focus: Pure algorithmic logic (e.g. `calculate_streaks(checkin_dates, today_date)`).
   - Speed: Microsecond execution; no database or network required.
   - Tools: Standard Python `datetime`, edge case parametrization.

2. **Model Constraint Tests (`test_models.py`)**:
   - Focus: Database schema rules, `UniqueConstraint` enforcement, `clean()` validation, delete cascading.
   - Tools: `pytest-django`, `pytest.raises(IntegrityError)`.

3. **API Integration Tests (`test_views.py`)**:
   - Focus: HTTP request/response lifecycles, serializer validation, permission boundaries, status codes (`200`, `201`, `400`, `404`).
   - Tools: DRF `APIClient`, `pytest.mark.django_db`, `freezegun` for mocking today's date.

### 7.2 Sample TDD Test Pattern

```python
import pytest
from datetime import date, timedelta
from freezegun import freeze_time
from rest_framework import status
from apps.habits.models import Habit, HabitCheckIn
from apps.habits.services.streaks import calculate_streaks

@pytest.mark.parametrize("checked_offsets,expected_current,expected_longest", [
    ([], 0, 0),                           # No check-ins
    ([0], 1, 1),                          # Checked today
    ([-1], 1, 1),                         # Checked yesterday (unbroken)
    ([-2], 0, 1),                         # Checked 2 days ago (broken)
    ([0, -1, -2], 3, 3),                  # 3-day active streak
    ([-1, -2, -3], 3, 3),                 # 3-day streak ending yesterday
    ([-10, -9, -8, -1, 0], 2, 3),         # Past 3-day streak, current 2-day streak
])
def test_streak_calculation_scenarios(checked_offsets, expected_current, expected_longest):
    today = date(2026, 10, 22)
    checkin_dates = {today + timedelta(days=offset) for offset in checked_offsets}
    current_streak, longest_streak = calculate_streaks(checkin_dates, reference_date=today)
    assert current_streak == expected_current
    assert longest_streak == expected_longest

@pytest.mark.django_db
def test_cannot_checkin_future_date(api_client, habit):
    future_date = date.today() + timedelta(days=1)
    response = api_client.post(f"/api/v1/habits/{habit.id}/check/", {"date": str(future_date)})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "date" in response.data
```

---

## 8. Git Commit & Branching Conventions

We follow the **Conventional Commits** standard:

```
<type>(<scope>): <short description in imperative mood>

[optional body explaining why and context]

[optional footer(s)]
```

### 8.1 Types
- `feat`: A new user-facing feature or API endpoint.
- `fix`: A bug fix.
- `test`: Adding or refactoring tests (TDD cycle).
- `refactor`: Code change that neither fixes a bug nor adds a feature.
- `docs`: Documentation changes only (`PLAN.md`, `PROGRESS.md`, README).
- `chore`: Build tasks, package upgrades, configuration changes.

### 8.2 Scope Examples
- `habits`, `streaks`, `auth`, `frequency`, `stats`, `docker`, `deploy`, `api`

### 8.3 Example Commit History for Steps
- `test(habits): add failing tests for Habit model and uniqueness constraint`
- `feat(habits): implement Habit and HabitCheckIn models with migrations`
- `test(streaks): add unit tests for streak calculation edge cases`
- `feat(streaks): implement streak calculation service`
- `test(api): add tests for habit check-in and undo endpoints`
- `feat(api): implement check and uncheck actions in HabitViewSet`
- `docs(progress): update checklist for Step 1 completion`
