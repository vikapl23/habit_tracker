# Habit Tracker — Project Progress & Implementation Checklist

This checklist tracks the ongoing development progress of the Habit Tracker project across each milestone. Update this document after completing each sub-task or feature step.

---

## Progress Overview

| Phase | Milestone | Status | Completed Steps |
|---|---|:---:|:---:|
| **Phase 0** | Project Setup & Tooling | `[x]` Completed | 4 / 4 |
| **Phase 1** | MVP: Core Domain, Streaks & REST API | `[x]` Completed | 7 / 7 |
| **Phase 2** | JWT Authentication & User Isolation | `[x]` Completed | 5 / 5 |
| **Phase 3** | Habit Scheduling & Frequency | `[x]` Completed | 4 / 4 |
| **Phase 4** | Statistics & Analytics | `[x]` Completed | 4 / 4 |
| **Phase 5** | Mobile-First React Frontend (Vite) | `[ ]` In Progress | 5 / 6 |
| **Phase 6** | Docker & PostgreSQL Environment | `[x]` Completed | 4 / 4 |
| **Phase 7** | Production Deployment (Render.com) | `[x]` Completed | 4 / 4 |
| **Phase 8** | Measurable Habits with Units | `[x]` Completed | 5 / 5 |
| **Phase 9** | Email Notifications via Mailgun | `[x]` Completed | 6 / 6 |
| **Phase 10** | AI Habit Coach Chatbot via Google Gemini | `[ ]` Not Started | 0 / 5 |
| **Phase 11** | Webhooks (Pending Mentor Clarification) | `[ ]` Pending | 0 / 4 |

---

## Detailed Task Breakdown

### Phase 0: Project Setup & Tooling
- [x] **0.1 Virtual Environment & Dependencies**
  - [x] Initialize Python virtual environment.
  - [x] Create `requirements/base.txt`, `requirements/local.txt`, `requirements/production.txt`.
  - [x] Add `Django~=5.0`, `djangorestframework`, `django-environ`, `drf-spectacular`, `pytest`, `pytest-django`, `freezegun`.
- [x] **0.2 Django Project Scaffolding**
  - [x] Initialize Django project with `config` layout.
  - [x] Split settings into `config/settings/base.py` and `local.py`.
  - [x] Configure `django-environ` with `.env.example` (ensure `SECRET_KEY` is loaded from environment).
- [x] **0.3 Pytest Configuration**
  - [x] Create `pytest.ini` with `DJANGO_SETTINGS_MODULE = config.settings.local`.
  - [x] Add basic smoke test to confirm test runner is operating.
- [x] **0.4 Documentation Verification**
  - [x] Validate `docs/PLAN.md` and initial git commit.

---

### Phase 1: MVP — Core Domain, Streaks & REST API (TDD)
- [x] **1.1 Core Models & Migrations (TDD)**
  - [x] **Test**: Write model unit tests (`test_models.py`) verifying `Habit` fields, `HabitCheckIn` fields, and `UniqueConstraint(habit, date)`.
  - [x] **Impl**: Implement `Habit` and `HabitCheckIn` models in `apps/habits/models.py`.
  - [x] Generate and apply initial database migrations.
  - [x] Verify test suite passes.
- [x] **1.2 Streak Calculation Service (TDD)**
  - [x] **Test**: Write algorithmic unit tests (`test_services.py`) covering edge cases:
    - Empty check-in history.
    - Checked today vs checked yesterday (unbroken streak).
    - Lapsed streak (missed yesterday).
    - Consecutive multi-day streaks.
    - Longest historical streak calculation with gaps.
    - Undo breaks/reverts streak.
    - Longest in past bigger than current.
  - [x] **Impl**: Implement pure calculation function in `apps/habits/services/streaks.py`.
  - [x] Verify 100% test coverage on streak logic.
- [x] **1.3 Serializers & Input Validation (TDD)**
  - [x] **Test**: Test rejection of future check-in dates.
  - [x] **Test**: Test serialization of habit data including computed `current_streak` and `longest_streak`.
  - [x] **Impl**: Implement `HabitSerializer`, `HabitCheckInSerializer`, and `CheckInActionSerializer`.
- [x] **1.4 Habits CRUD API Endpoints (TDD)**
  - [x] **Test**: API integration tests (`test_views.py`) for `GET /api/v1/habits/`, `POST`, `GET /id/`, `PUT`, `PATCH`, `DELETE`.
  - [x] **Impl**: Implement `HabitViewSet` with DRF `DefaultRouter`.
- [x] **1.5 Check-In & Undo Endpoints (TDD)**
  - [x] **Test**: Test `POST /api/v1/habits/{id}/check/` (success, duplicate idempotency, future date rejection, 404 on missing habit).
  - [x] **Test**: Test `POST /api/v1/habits/{id}/uncheck/` (undo existing check-in, default today, 404 for non-existent check-in / habit).
  - [x] **Test**: Test `GET /api/v1/habits/{id}/check-ins/` (list check-ins, date range filtering `?from=&to=`, 404 on missing habit).
  - [x] **Impl**: Implement `@action(detail=True)` endpoints (`check`, `uncheck`, `check_ins`) in `HabitViewSet`.
- [x] **1.6 Archive / Unarchive Actions (TDD)**
  - [x] **Test**: Test soft-archiving habits and filtering active habits by default.
  - [x] **Impl**: Add `archive` and `unarchive` actions to `HabitViewSet`.
- [x] **1.7 Django Admin Registration**
  - [x] Register `Habit` and `HabitCheckIn` in `apps/habits/admin.py` with custom list displays, filters, and search fields.

---

### Phase 2: JWT Authentication & User Isolation
- [x] **2.1 Custom User Model (TDD)**
  - [x] Create `apps/accounts` with email-based `User` model.
  - [x] Configure `AUTH_USER_MODEL = 'accounts.User'`.
- [x] **2.2 SimpleJWT Integration**
  - [x] Configure `rest_framework_simplejwt` in settings.
  - [x] Setup token endpoints: `/api/v1/auth/token/` and `/api/v1/auth/token/refresh/`.
  - [x] Add user registration endpoint: `/api/v1/auth/register/`.
- [x] **2.3 User-Habit Association & Safe Migration**
  - [x] Migrate `Habit.user` ForeignKey to link to `accounts.User` (enforcing `null=False`).
- [x] **2.4 Queryset Scoping & Permissions (TDD)**
  - [x] **Test**: Ensure User A cannot view, edit, check, or delete User B's habits (`404` or `403`).
  - [x] **Impl**: Restrict `get_queryset()` in `HabitViewSet` to `user=self.request.user`.
  - [x] Automatically assign `user` from request context in serializer `create()`.
- [x] **2.5 Update Test Suite with Authenticated APIClient**
  - [x] Provide pytest fixtures for registered/authenticated user and client.

---

### Phase 3: Habit Scheduling & Custom Frequency
- [x] **3.1 Frequency Fields on Habit Model (TDD)**
  - [x] **Test & Impl**: Add `frequency_type` (`daily`, `custom`) and `frequency_days` (list of weekday ints 0-6).
- [x] **3.2 Frequency-Aware Streak Calculation (TDD)**
  - [x] **Test**: Verify that off-schedule days (e.g. weekend for weekday-only habit) do not reset the streak.
  - [x] **Impl**: Update `apps.habits.services.streaks` algorithm to evaluate only scheduled dates.
- [x] **3.3 Validation & Serializer Support (TDD)**
  - [x] Validate valid weekday combinations.
- [x] **3.4 API Integration Verification**
  - [x] Confirm habit list and detail endpoints return frequency data correctly.
  - [x] Support filtering habit list with `?scheduled_today=true` and `?scheduled_today=false`.
  - [x] Add weekday-only habit request to Postman collection.

---

### Phase 4: Statistics & Analytics
- [x] **4.1 Analytics Aggregation Service (TDD)**
  - [x] **Test & Impl**: Compute weekly completion percentage (`checked / scheduled`, respecting habit frequency and user timezone; days before creation excluded).
  - [x] Compute monthly completion percentage.
  - [x] Compute total lifetime check-ins count, current and longest streak.
  - [x] Extensible `is_day_completed` helper for future measurable habits.
- [x] **4.2 Analytics Endpoints (TDD)**
  - [x] Add `GET /api/v1/habits/{id}/statistics/` with OpenAPI `@extend_schema`.
  - [x] Add `GET /api/v1/statistics/summary/` for user-wide dashboard overview.
  - [x] Enforce user isolation (`404` on foreign habit, `401` on unauthenticated).
- [x] **4.3 Frontend Statistics & UI Integration**
  - [x] Habit detail screen statistics cards (7-day and 30-day completion %, total check-ins, current and longest streak).
  - [x] "Stats" tab in bottom navigation with summary (week & month completion %, best habit highlight, active habits count, total check-ins).
  - [x] Mobile-first loading skeletons, error/retry states, and responsive cards.
- [x] **4.4 Query Optimization & Postman**
  - [x] Single-query aggregations with zero N+1 database queries verified via `django_assert_num_queries`.
  - [x] Deterministic date tests with `freezegun` and Vitest fake timers.
  - [x] Updated Postman collection with `4. Statistics` requests and assertions.

---

### Phase 5: Mobile-First React Frontend (Vite)
- [x] **5.1 Project Scaffolding & Setup**
  - [x] Initialize React + TypeScript with Vite in `frontend/`.
  - [x] Configure Tailwind CSS and mobile viewport meta tags.
- [x] **5.2 Authentication Flow**
  - [x] Login, registration, and automatic token refresh interceptor.
  - [x] Protected route wrapper for authenticated views.
- [x] **5.3 Mobile Dashboard View**
  - [x] Habit list with optimistic toggle (check/uncheck on tap).
  - [x] Visual streak badges (`🔥 7`), colored accent, and longest streak smaller.
  - [x] Daily progress bar and date header (counting only habits scheduled today).
  - [x] Summary card with best current streak among active habits.
  - [x] Collapsed "Not today" section for other active habits.
  - [x] Pagination handling to load all habit pages.
  - [x] Empty state ("Create your first habit"), loading skeletons, and error retry state.
  - [x] Touch targets min 44px, no horizontal scroll at 320px width.
- [x] **5.4 Habit Management (Modals/Drawers)**
  - [x] Create habit bottom sheet (name, description, color picker, emoji selector, frequency).
  - [x] Floating action button and empty state create trigger.
  - [x] Edit habit and soft-archive actions from card menu.
  - [x] Delete confirmation dialog with prompt.
  - [x] Dedicated "Archived" habits screen with unarchive functionality.
  - [x] Server and client-side field validation error rendering.
  - [x] Mobile drawer UX: backdrop tap, swipe down, Esc key, auto-focus, responsive layout.
- [x] **5.5 Habit Detail & History View**
  - [x] Habit detail screen (tap on habit name/emoji, not check circle).
  - [x] Month calendar view with checked days in habit color, non-scheduled days visually muted.
  - [x] Month navigation with range query `GET /habits/{id}/check-ins/?from=&to=`.
  - [x] Current and longest streak cards.
  - [x] Tapping past day toggles check-in; future days disabled.
  - [x] Profile screen with read-only email, timezone selector (`PATCH /auth/profile/`), and logout.
  - [x] Bottom navigation (Today / Archive / Profile) replacing header archive and sign-out icons.
  - [x] Floating "+" button positioned above bottom navigation without overlap.
- [ ] **5.6 Polish & PWA Readiness**
  - [ ] Haptic-feel animations, responsive touch targets, dark/light theme support.

---

### Phase 6: Docker & PostgreSQL Integration
- [x] **6.1 Multi-Stage Dockerfile & Container Setup**
  - [x] Backend Dockerfile: Python 3.12-slim base, non-root user `appuser`, installs `requirements/production.txt`, runs gunicorn.
  - [x] Frontend Dockerfile: multi-stage build (Node 20 Alpine, Nginx 1.27 Alpine), `VITE_API_URL` build arg, SPA fallback, security headers.
  - [x] `.dockerignore` for root backend and frontend.
- [x] **6.2 Docker Compose Configuration**
  - [x] Define `backend`, `frontend`, and `db` (PostgreSQL 16) services.
  - [x] Configure named volume `postgres_data` for persistent Postgres storage.
  - [x] Add database healthcheck (`pg_isready`) and configure backend `depends_on` service_healthy.
  - [x] Configure `.env.example` and `.env` with compose hosts (`ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`).
- [x] **6.3 Entrypoint & Automated Migrations**
  - [x] Backend startup runs `python manage.py migrate --noinput` and `python manage.py collectstatic --noinput` before launching Gunicorn.
- [x] **6.4 CI Pipeline & Verification**
  - [x] Add GitHub Actions `docker` job to build both backend and frontend images.
  - [x] Document Windows execution steps and URLs in README.md.

---

### Phase 7: Production Cloud Deployment (Render.com)
- [x] **7.1 Production Settings & Static Assets**
  - [x] Configure `config/settings/production.py` with strict HTTPS defaults and configurable overrides.
  - [x] Integrate `WhiteNoise` for static asset compression and caching.
  - [x] Enforce security headers, SSL redirect, and cookie protection flags.
- [x] **7.2 Render Blueprint Configuration (`render.yaml`)**
  - [x] Define Managed PostgreSQL Database (`habit-tracker-db`, free tier).
  - [x] Define Web Service running Gunicorn (`gunicorn config.wsgi:application`) on `0.0.0.0:$PORT` with `WEB_CONCURRENCY` workers.
  - [x] Define Frontend Static Site (`habit-tracker-frontend`) with `npm ci && npm run build`, `dist` publish path, rewrite `/* -> /index.html`, and strict security headers.
  - [x] Map environment variables (`DATABASE_URL` via `fromDatabase`, `SECRET_KEY` generated, `DJANGO_SETTINGS_MODULE`, `AUTH_THROTTLE_RATE`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `VITE_API_URL`).
- [x] **7.3 Pre-Deploy & Automated Migration Scripts**
  - [x] Configure container entrypoint (`scripts/entrypoint.sh`) running migrations and static collection prior to launching Gunicorn.
- [x] **7.4 Documentation & Deployment Workflow**
  - [x] Document step-by-step Render dashboard setup, environment variable wiring, redeployment order, free tier limitations (30-day DB lifespan, sleep on inactivity), and superuser creation in README.md.

---

### Phase 8: Measurable Habits with Units
- [x] **8.1 Data Model Extensions & Migrations (TDD)**
  - [x] Add `habit_type` (`boolean`, `measurable`), `target_value` (`DecimalField` max 100,000, 2 decimals), and `unit` (`CharField`) to `Habit`.
  - [x] Update `HabitCheckIn` to record check-in `value` (`DecimalField` default 1.00).
  - [x] Apply migration with backward compatibility for existing boolean habits.
- [x] **8.2 Shared Completion Helper & Atomic Check-In Accumulation (TDD)**
  - [x] Centralize `is_day_completed` in `apps/habits/services/completion.py`.
  - [x] Atomic check-in accumulation (`mode="add"`, `mode="set"`) protected against race conditions with tests.
  - [x] Decrement on `uncheck` when `value` provided, reset day when omitted.
  - [x] Validation: limits <= 100,000, 2 decimals, reject `value` on boolean habits.
- [x] **8.3 Streak Engine & Analytics Adaptation (TDD)**
  - [x] Adapt streak calculation and statistics using `is_day_completed`.
  - [x] Recalculate streaks in service layer when `habit_type` or `target_value` is updated.
- [x] **8.4 API Serialization & Query Optimization (TDD)**
  - [x] Return numeric JSON values for `target_value`, `today_value`, `today_progress`, and check-in `value`.
  - [x] Assert zero N+1 queries on habits list and statistics (`django_assert_num_queries`).
- [x] **8.5 Frontend Measurable Habit UI & Postman Collection**
  - [x] Form type toggle, unit suggestions, target input, warning on target change.
  - [x] Dashboard card with `"5 / 8 glasses"`, progress ring, quick `+`/`−`, tap for exact amount.
  - [x] Calendar distinct display for partial vs completed days, tap for amount.
  - [x] Update Postman collection with measurable habit example.

---

### Phase 9: Email Notifications via Mailgun
- [x] **9.1 User Notification Preferences & Tokens (TDD)**
  - [x] Add notification settings to user model (`daily_reminder_enabled`, `daily_reminder_time`, `weekly_summary_enabled`).
  - [x] Expose settings in `GET/PATCH /api/v1/auth/profile/` with validation.
  - [x] Cryptographically signed one-click unsubscribe links with `/api/v1/notifications/unsubscribe/<token>/`.
- [x] **9.2 Mailgun Integration & Templates**
  - [x] Configure `django-anymail[mailgun]` with fallback to console backend in local development and `locmem` in tests.
  - [x] Environment configuration via `.env.example` (`MAILGUN_API_KEY`, `MAILGUN_DOMAIN`, `MAILGUN_API_URL`, `DEFAULT_FROM_EMAIL`, `CRON_TOKEN`).
  - [x] Text and HTML templates for daily reminders and Monday weekly summaries.
- [x] **9.3 Daily Reminder & Weekly Summary Dispatch Service (TDD)**
  - [x] `send_due_notifications` service evaluating user timezone and matching current 15-minute window.
  - [x] Daily reminders for incomplete scheduled habits (using shared `is_day_completed` helper; no email if all done).
  - [x] Weekly summary on Mondays calculating last week's completion %, best habit, and current streaks.
  - [x] Idempotent deduplication via `NotificationLog` model to prevent duplicate sends on the same date/week.
- [x] **9.4 Protected Internal Endpoint & Management Command (TDD)**
  - [x] Protected endpoint `POST /api/v1/internal/send-notifications/` authorized with `X-Cron-Token` constant-time comparison.
  - [x] Management command `send_notifications` with `--force` flag for manual execution and testing.
- [x] **9.5 Infrastructure & Documentation**
  - [x] Updated `render.yaml` with notification environment variables (`sync: false`).
  - [x] Documented notification architecture, usage, and commands in `README.md` and `docs/DECISIONS.md`.
- [x] **9.6 Recurring Cron Workflow & Frontend Notification Settings**
  - [x] GitHub Actions workflow `.github/workflows/notifications.yml` scheduled every 15 minutes (`*/15 * * * *`) + `workflow_dispatch` triggering `POST /api/v1/internal/send-notifications/` with `X-Cron-Token: ${{ secrets.CRON_TOKEN }}` and repository variable `BACKEND_URL`.
  - [x] Resilient retry once after 60s for waking sleeping Render free-tier instances, immediate failure on HTTP 403 Forbidden, and response counts logging.
  - [x] Add `SITE_URL` to `render.yaml` backend `envVars` (`sync: false`) and document that it must be the backend URL (used for unsubscribe links).
  - [x] Frontend Profile "Notifications" section with toggles for daily reminder and weekly summary and reminder time picker (shown in user's timezone), saved via `PATCH /auth/profile/`.
  - [x] Frontend test suite covering notifications rendering, dirty state, error handling, and profile persistence.
- [x] **9.7 Per-Habit Email Reminders (TDD)**
  - [x] Backend: Add `reminder_enabled` (default False) and `reminder_time` (nullable TimeField, minutes 0/15/30/45) to `Habit` with migrations and validations.
  - [x] Backend: Replace single daily reminder on `User` with global master switch `notifications_enabled` (default True) and sunset legacy `daily_reminder_enabled`/`time` (ADR 009).
  - [x] Backend: Update `send_due_notifications` to dispatch consolidated emails for due, incomplete, scheduled habits in current 15-minute window per user timezone.
  - [x] Backend: Per-habit daily deduplication via `NotificationLog(habit, scheduled_date)` unique constraint.
  - [x] Backend: Expose `reminder_enabled` and `reminder_time` in Habit API, `notifications_enabled` in profile API.
  - [x] Backend: Unsubscribe endpoint sets `user.notifications_enabled = False`.
  - [x] Frontend: Habit form "Remind me if not done" toggle + 15-min time picker (hidden when toggle off).
  - [x] Frontend: Habit card reminder bell icon with time.
  - [x] Frontend: Profile master switch "Email notifications" + weekly summary toggle.
  - [x] Postman collection update with reminder habit and profile notifications requests.

---

### Phase 10: AI Habit Coach Chatbot via Google Gemini
- [ ] **10.1 Chat Conversation & Message Models (TDD)**
  - [ ] Create `CoachConversation` and `CoachMessage` models with cascade deletion.
  - [ ] Migration and admin registration.
- [ ] **10.2 Gemini Client Service & Prompt Builder (TDD)**
  - [ ] Secure backend-only Gemini API integration (client never receives secret key).
  - [ ] Context aggregation service: format user's habits, frequencies, streaks, and 7-day completion stats.
  - [ ] Strict prompt-injection safeguards, system instructions, and read-only coaching persona.
- [ ] **10.3 Chat API Endpoints & Quota Rate Limiting (TDD)**
  - [ ] `POST /api/v1/coach/chat/` endpoint with daily message quota enforcement (e.g. 10/day).
  - [ ] `GET /api/v1/coach/messages/` to load recent chat history and `DELETE /api/v1/coach/history/` to clear history.
- [ ] **10.4 Frontend Coach Tab & Chat UI**
  - [ ] Dedicated "Coach" view in frontend navigation.
  - [ ] Chat conversation interface: message bubbles, quick prompt suggestions, remaining message counter.
- [ ] **10.5 Testing & Fallback Handling**
  - [ ] Mocked Gemini API unit tests, rate limit tests (429), and gracefully handled network timeouts.

---

### Phase 11: Webhooks (Pending Mentor Clarification)
- [ ] **11.1 Requirement Clarification [PENDING]**
  - [ ] Confirm scope with mentor: Stripe payments vs Mailgun event callbacks vs outgoing user webhooks.
- [ ] **11.2 Webhook Ingestion & Event Model (TDD)**
  - [ ] `WebhookEvent` model for logging raw incoming payloads, status, and event IDs.
  - [ ] Cryptographic signature verification middleware/service.
- [ ] **11.3 Idempotent Event Processor (TDD)**
  - [ ] Deduplicate delivery by provider `event_id` to prevent double processing.
  - [ ] Background dispatch of domain side-effects.
- [ ] **11.4 Integration Tests & Error Handling**
  - [ ] Test forged signature rejection, duplicate payload handling, and provider health checks.
