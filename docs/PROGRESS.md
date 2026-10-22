# Habit Tracker — Project Progress & Implementation Checklist

This checklist tracks the ongoing development progress of the Habit Tracker project across each milestone. Update this document after completing each sub-task or feature step.

---

## Progress Overview

| Phase | Milestone | Status | Completed Steps |
|---|---|:---:|:---:|
| **Phase 0** | Project Setup & Tooling | `[ ]` Not Started | 0 / 4 |
| **Phase 1** | MVP: Core Domain, Streaks & REST API | `[ ]` Not Started | 0 / 7 |
| **Phase 2** | JWT Authentication & User Isolation | `[ ]` Not Started | 0 / 5 |
| **Phase 3** | Habit Scheduling & Frequency | `[ ]` Not Started | 0 / 4 |
| **Phase 4** | Statistics & Analytics | `[ ]` Not Started | 0 / 4 |
| **Phase 5** | Mobile-First React Frontend (Vite) | `[ ]` Not Started | 0 / 6 |
| **Phase 6** | Docker & PostgreSQL Environment | `[ ]` Not Started | 0 / 4 |
| **Phase 7** | Production Deployment (Render.com) | `[ ]` Not Started | 0 / 4 |

---

## Detailed Task Breakdown

### Phase 0: Project Setup & Tooling
- [ ] **0.1 Virtual Environment & Dependencies**
  - [ ] Initialize Python virtual environment.
  - [ ] Create `requirements/base.txt`, `requirements/local.txt`, `requirements/production.txt`.
  - [ ] Add `Django~=5.0`, `djangorestframework`, `django-environ`, `pytest`, `pytest-django`, `freezegun`.
- [ ] **0.2 Django Project Scaffolding**
  - [ ] Initialize Django project with `config` layout.
  - [ ] Split settings into `config/settings/base.py` and `local.py`.
  - [ ] Configure `django-environ` with `.env.example` (ensure `SECRET_KEY` is loaded from environment).
- [ ] **0.3 Pytest Configuration**
  - [ ] Create `pytest.ini` with `DJANGO_SETTINGS_MODULE = config.settings.local`.
  - [ ] Add basic smoke test to confirm test runner is operating.
- [ ] **0.4 Documentation Verification**
  - [ ] Validate `docs/PLAN.md` and initial git commit.

---

### Phase 1: MVP — Core Domain, Streaks & REST API (TDD)
- [ ] **1.1 Core Models & Migrations (TDD)**
  - [ ] **Test**: Write model unit tests (`test_models.py`) verifying `Habit` fields, `HabitCheckIn` fields, and `UniqueConstraint(habit, date)`.
  - [ ] **Impl**: Implement `Habit` and `HabitCheckIn` models in `apps/habits/models.py`.
  - [ ] Generate and apply initial database migrations.
  - [ ] Verify test suite passes.
- [ ] **1.2 Streak Calculation Service (TDD)**
  - [ ] **Test**: Write algorithmic unit tests (`test_services.py`) covering edge cases:
    - Empty check-in history.
    - Checked today vs checked yesterday (unbroken streak).
    - Lapsed streak (missed yesterday).
    - Consecutive multi-day streaks.
    - Longest historical streak calculation with gaps.
  - [ ] **Impl**: Implement pure calculation function in `apps/habits/services/streaks.py`.
  - [ ] Verify 100% test coverage on streak logic.
- [ ] **1.3 Serializers & Input Validation (TDD)**
  - [ ] **Test**: Test rejection of future check-in dates.
  - [ ] **Test**: Test serialization of habit data including computed `current_streak` and `longest_streak`.
  - [ ] **Impl**: Implement `HabitListSerializer`, `HabitDetailSerializer`, `HabitWriteSerializer`, and `CheckInSerializer`.
- [ ] **1.4 Habits CRUD API Endpoints (TDD)**
  - [ ] **Test**: API integration tests (`test_views.py`) for `GET /api/v1/habits/`, `POST`, `GET /id/`, `PUT`, `PATCH`, `DELETE`.
  - [ ] **Impl**: Implement `HabitViewSet` with DRF `DefaultRouter`.
- [ ] **1.5 Check-In & Undo Endpoints (TDD)**
  - [ ] **Test**: Test `POST /api/v1/habits/{id}/check/` (success, duplicate idempotency, future date rejection).
  - [ ] **Test**: Test `POST /api/v1/habits/{id}/uncheck/` (undo existing check-in, 404/400 for non-existent check-in).
  - [ ] **Impl**: Implement `@action(detail=True, methods=['post'])` endpoints in `HabitViewSet`.
- [ ] **1.6 Archive / Unarchive Actions (TDD)**
  - [ ] **Test**: Test soft-archiving habits and filtering active habits by default.
  - [ ] **Impl**: Add `archive` and `unarchive` actions to `HabitViewSet`.
- [ ] **1.7 Django Admin Registration**
  - [ ] Register `Habit` and `HabitCheckIn` in `apps/habits/admin.py` with custom list displays, filters, and search fields.

---

### Phase 2: JWT Authentication & User Isolation
- [ ] **2.1 Custom User Model (TDD)**
  - [ ] Create `apps/accounts` with email-based `User` model.
  - [ ] Configure `AUTH_USER_MODEL = 'accounts.User'`.
- [ ] **2.2 SimpleJWT Integration**
  - [ ] Configure `rest_framework_simplejwt` in settings.
  - [ ] Setup token endpoints: `/api/v1/auth/token/` and `/api/v1/auth/token/refresh/`.
  - [ ] Add user registration endpoint: `/api/v1/auth/register/`.
- [ ] **2.3 User-Habit Association & Safe Migration**
  - [ ] Migrate `Habit.user` ForeignKey to link to `accounts.User` (enforcing `null=False`).
- [ ] **2.4 Queryset Scoping & Permissions (TDD)**
  - [ ] **Test**: Ensure User A cannot view, edit, check, or delete User B's habits (`404` or `403`).
  - [ ] **Impl**: Restrict `get_queryset()` in `HabitViewSet` to `user=self.request.user`.
  - [ ] Automatically assign `user` from request context in serializer `create()`.
- [ ] **2.5 Update Test Suite with Authenticated APIClient**
  - [ ] Provide pytest fixtures for registered/authenticated user and client.

---

### Phase 3: Habit Scheduling & Custom Frequency
- [ ] **3.1 Frequency Fields on Habit Model (TDD)**
  - [ ] **Test & Impl**: Add `frequency_type` (`daily`, `custom`) and `frequency_days` (list of weekday ints 0-6).
- [ ] **3.2 Frequency-Aware Streak Calculation (TDD)**
  - [ ] **Test**: Verify that off-schedule days (e.g. weekend for weekday-only habit) do not reset the streak.
  - [ ] **Impl**: Update `apps.habits.services.streaks` algorithm to evaluate only scheduled dates.
- [ ] **3.3 Validation & Serializer Support (TDD)**
  - [ ] Validate valid weekday combinations.
- [ ] **3.4 API Integration Verification**
  - [ ] Confirm habit list and detail endpoints return frequency data correctly.

---

### Phase 4: Statistics & Analytics
- [ ] **4.1 Analytics Aggregation Service (TDD)**
  - [ ] **Test & Impl**: Compute weekly completion percentage (`checked / scheduled`).
  - [ ] Compute monthly completion percentage.
  - [ ] Compute total lifetime check-ins count.
- [ ] **4.2 Analytics Endpoints (TDD)**
  - [ ] Add `GET /api/v1/habits/{id}/statistics/`.
  - [ ] Add `GET /api/v1/statistics/summary/` for user-wide dashboard overview.
- [ ] **4.3 Heatmap & Calendar Matrix Endpoint**
  - [ ] Provide optimized endpoint returning date-checkin pairs for frontend calendar grids.
- [ ] **4.4 Query Optimization**
  - [ ] Ensure single-query aggregations with zero N+1 database queries.

---

### Phase 5: Mobile-First React Frontend (Vite)
- [ ] **5.1 Project Scaffolding & Setup**
  - [ ] Initialize React + TypeScript with Vite in `frontend/`.
  - [ ] Configure Tailwind CSS and mobile viewport meta tags.
- [ ] **5.2 Authentication Flow**
  - [ ] Login, registration, and automatic token refresh interceptor.
  - [ ] Protected route wrapper for authenticated views.
- [ ] **5.3 Mobile Dashboard View**
  - [ ] Habit list with optimistic toggle (check/uncheck on tap).
  - [ ] Visual streak badges (`🔥 7`).
  - [ ] Daily progress bar (e.g. 4/6 completed today).
- [ ] **5.4 Habit Management (Modals/Drawers)**
  - [ ] Create habit modal (name, description, color picker, emoji selector, frequency).
  - [ ] Edit and archive drawers.
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
