# Habit Tracker — Backend REST API

A high-performance, robust RESTful API for habit tracking and daily streak monitoring, built with Python, Django, and Django REST Framework (DRF).

---

## 🚀 Features

- **Habit Lifecycle Management**: Create, view, update, delete, soft-archive, and restore habits.
- **Visual Attributes & Validation**: Custom color themes (strict `#RRGGBB` / `#RGB` hexadecimal codes) and emoji icons (Unicode symbol validation).
- **Daily Check-Ins & Undo**: Idempotent check-ins for today or past dates; instant check-in undo capabilities.
- **Streak Calculation Engine**: Real-time evaluation of `current_streak` (unbroken if completed yesterday or today) and lifetime `longest_streak`.
- **Today Status Detection**: Dynamic `is_checked_today` field on habits, configurable with an optional `?date=YYYY-MM-DD` reference query parameter.
- **Check-In History & Filtering**: Filter check-ins with `?from=YYYY-MM-DD` and `?to=YYYY-MM-DD` query parameters with full date validation.
- **Pagination & Query Performance**: Standard DRF `PageNumberPagination` on list endpoints, with check-in prefetching to eliminate $N+1$ queries.
- **Interactive OpenAPI / Swagger Docs**: Live interactive API documentation via Swagger UI (`/docs/`) and OpenAPI 3.0 schema generation (`/api/schema/`).
- **Comprehensive Test Suite**: Built with strict Test-Driven Development (TDD) using `pytest-django`, `freezegun`, and query count assertions.

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| **Language & Framework** | Python 3.12+, Django 5.x |
| **API Framework** | Django REST Framework (DRF) 3.15+ |
| **API Documentation** | `drf-spectacular` (OpenAPI 3.0 & Swagger UI) |
| **Configuration** | `django-environ` (12-factor configuration via `.env`) |
| **Testing** | `pytest`, `pytest-django`, `freezegun` |
| **Database** | SQLite 3 (local development), PostgreSQL 16+ (production-ready) |

---

## 💻 Local Setup & Installation (Windows)

Follow these steps in **PowerShell** or **Command Prompt** to run the project locally on Windows:

### 1. Create and Activate Virtual Environment

```powershell
# Create a virtual environment named .venv
python -m venv .venv

# Activate the virtual environment in PowerShell
.\.venv\Scripts\Activate.ps1

# (Or in Command Prompt: .venv\Scripts\activate.bat)
```

### 2. Install Dependencies

```powershell
pip install -r requirements/local.txt
```

### 3. Environment Configuration

Copy the example environment file to `.env`:

```powershell
copy .env.example .env
```

### 4. Run Database Migrations

```powershell
python manage.py migrate
```

### 5. Create an Admin User (Superuser)

```powershell
python manage.py createsuperuser
```

### 6. Start the Development Server

```powershell
python manage.py runserver
```

The API will be accessible at:
- **API Base:** [http://127.0.0.1:8000/api/v1/](http://127.0.0.1:8000/api/v1/)
- **Interactive Swagger UI:** [http://127.0.0.1:8000/docs/](http://127.0.0.1:8000/docs/)
- **Django Admin:** [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## 🧪 Running Tests

The test suite uses `pytest` with `pytest-django`:

```powershell
# Run the complete test suite
.\.venv\Scripts\pytest

# Run tests with detailed verbose output
.\.venv\Scripts\pytest -v

# Run only view/API integration tests
.\.venv\Scripts\pytest apps/habits/tests/test_views.py
```

---

## 📡 Main API Endpoints & Examples

Base URL: `/api/v1`

### 1. List Habits (`GET /api/v1/habits/`)

Query Parameters:
- `include_archived` (optional, boolean, default: `false`)
- `date` (optional, `YYYY-MM-DD`, default: today) — determines `is_checked_today`

**Response (`200 OK`):**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
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
      "updated_at": "2026-10-23T08:15:00Z"
    }
  ]
}
```

### 2. Create a Habit (`POST /api/v1/habits/`)

**Request Body:**
```json
{
  "name": "Morning Meditation",
  "description": "10 minutes of mindfulness",
  "color": "#10B981",
  "emoji": "🧘"
}
```

**Response (`201 Created`):**
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
  "created_at": "2026-10-23T08:30:00Z",
  "updated_at": "2026-10-23T08:30:00Z"
}
```

### 3. Record Check-In (`POST /api/v1/habits/{id}/check/`)

**Request Body (optional date, defaults to today):**
```json
{
  "date": "2026-10-23"
}
```

**Response (`201 Created` or `200 OK` if already checked):**
```json
{
  "status": "checked",
  "habit_id": 2,
  "date": "2026-10-23",
  "current_streak": 1,
  "longest_streak": 1
}
```

### 4. Undo Check-In (`POST /api/v1/habits/{id}/uncheck/`)

**Request Body (optional date, defaults to today):**
```json
{
  "date": "2026-10-23"
}
```

**Response (`200 OK`):**
```json
{
  "status": "unchecked",
  "habit_id": 2,
  "date": "2026-10-23",
  "current_streak": 0,
  "longest_streak": 1
}
```

### 5. Check-In History (`GET /api/v1/habits/{id}/check-ins/`)

Query Parameters:
- `from` (optional, `YYYY-MM-DD`)
- `to` (optional, `YYYY-MM-DD`)

**Response (`200 OK`):**
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 15,
      "date": "2026-10-23",
      "created_at": "2026-10-23T08:35:00Z"
    },
    {
      "id": 14,
      "date": "2026-10-22",
      "created_at": "2026-10-22T09:10:00Z"
    }
  ]
}
```

### 6. Archive / Unarchive Habit (`POST /api/v1/habits/{id}/archive/` & `/unarchive/`)

**Response (`200 OK`):**
```json
{
  "id": 2,
  "is_archived": true
}
```

---

## 📚 Project Documentation

- [System Architecture & Implementation Plan](docs/PLAN.md) — Architectural overview, database schema, streak algorithms, and roadmap across all project milestones.
- [Project Progress & Implementation Checklist](docs/PROGRESS.md) — Status tracking and checklist covering completed and upcoming phases.
- [MVP Code Review & Audit Report](docs/REVIEW_MVP.md) — Comprehensive audit report identifying findings, query optimizations, edge cases, and verification steps.
