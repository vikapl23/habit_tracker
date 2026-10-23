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
| **Phase 4** | Statistics & Analytics | `[ ]` Postponed (after deployment) | 0 / 4 |
| **Phase 5** | Mobile-First React Frontend (Vite) | `[ ]` In Progress | 4 / 6 |
| **Phase 6** | Docker & PostgreSQL Environment | `[ ]` Not Started | 0 / 4 |
| **Phase 7** | Production Deployment (Render.com) | `[ ]` Not Started | 0 / 4 |

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

### Phase 4: Statistics & Analytics (Postponed until after deployment)
- [ ] **4.1 Analytics Aggregation Service (TDD)** (Postponed)
  - [ ] **Test & Impl**: Compute weekly completion percentage (`checked / scheduled`).
  - [ ] Compute monthly completion percentage.
  - [ ] Compute total lifetime check-ins count.
- [ ] **4.2 Analytics Endpoints (TDD)** (Postponed)
  - [ ] Add `GET /api/v1/habits/{id}/statistics/`.
  - [ ] Add `GET /api/v1/statistics/summary/` for user-wide dashboard overview.
- [ ] **4.3 Heatmap & Calendar Matrix Endpoint** (Postponed)
  - [ ] Provide optimized endpoint returning date-checkin pairs for frontend calendar grids.
- [ ] **4.4 Query Optimization** (Postponed)
  - [ ] Ensure single-query aggregations with zero N+1 database queries.

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
- [ ] **5.5 Habit Detail & History View**
  - [ ] Monthly calendar heatmap view of check-in history.
  - [ ] Statistical summary cards.
- [ ] **5.6 Polish & PWA Readiness**
  - [ ] Haptic-feel animations, responsive touch targets, dark/light theme support.

---

### Phase 6: Docker & PostgreSQL Integration
- [ ] **6.1 Multi-Stage Dockerfile**
  - [ ] Python 3.12-slim base, non-root user, optimized layer caching.
- [ ] **6.2 Docker Compose Configuration**
  - [ ] Define `web` service (Django) and `db` service (PostgreSQL 16).
  - [ ] Configure named volume for persistent Postgres storage.
  - [ ] Add database healthcheck to ensure Postgres is ready before Django starts.
- [ ] **6.3 Entrypoint & Automated Migrations**
  - [ ] Add entrypoint script executing `python manage.py migrate` and `collectstatic`.
- [ ] **6.4 Local Verification**
  - [ ] Confirm end-to-end tests and API functionality inside Docker containers.

---

### Phase 7: Production Cloud Deployment (Render.com)
- [ ] **7.1 Production Settings & Static Assets**
  - [ ] Configure `config/settings/production.py`.
  - [ ] Integrate `WhiteNoise` for static asset compression and caching.
  - [ ] Enforce security headers, SSL redirect, and cookie protection flags.
- [ ] **7.2 Render Blueprint Configuration (`render.yaml`)**
  - [ ] Define Web Service running Gunicorn (`gunicorn config.wsgi:application`).
  - [ ] Define Managed PostgreSQL instance.
  - [ ] Map environment variables (`DATABASE_URL`, `SECRET_KEY`, `ALLOWED_HOSTS`).
- [ ] **7.3 Pre-Deploy & Migration Scripts**
  - [ ] Setup zero-downtime database migration hook.
- [ ] **7.4 Live Verification & Monitoring**
  - [ ] Verify SSL, API endpoints, admin login, and database persistence in live Render environment.
