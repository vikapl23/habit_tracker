# Habit Tracker — Backend REST API

[![CI](https://github.com/vikapl23/habit_tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/vikapl23/habit_tracker/actions/workflows/ci.yml)

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
| **Testing & Quality** | `pytest`, `pytest-django`, `freezegun`, `ruff` |
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

## 🌐 Running Backend & Frontend Together

The application consists of a Django REST Framework backend and a mobile-first React (Vite + Tailwind CSS) frontend in `frontend/`.

### 1. Terminal 1 — Start the Backend API

```powershell
# Activate Python environment
.\.venv\Scripts\Activate.ps1

# Apply migrations
python manage.py migrate

# Start Django development server (default port 8000)
python manage.py runserver
```

> **CORS Configuration:** `django-cors-headers` is configured to allow `http://localhost:5173` by default via `CORS_ALLOWED_ORIGINS` in `.env`.

### 2. Terminal 2 — Start the React Frontend

```powershell
# Navigate to frontend directory
cd frontend

# Set up environment variables (.env with VITE_API_URL=http://localhost:8000/api/v1)
copy .env.example .env

# Install Node dependencies
npm install

# Start Vite development server (default port 5173)
npm run dev
```

Open your browser at **[http://localhost:5173](http://localhost:5173)**. You can register an account, log in, and view the mobile-first habit tracker interface (optimized for 375px mobile view and responsive on desktop).


---

## 🐳 Run with Docker

You can run the entire stack (PostgreSQL 16, Django Backend API with Gunicorn, and React Frontend served with Nginx) using Docker Compose.

### 1. Prerequisites
- [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/) installed and running.

### 2. Environment Configuration
Ensure your `.env` is configured or copy the defaults from `.env.example`:

```powershell
copy .env.example .env
```

> [!NOTE]
> `SECRET_KEY` is read directly from `.env` in `docker-compose.yml` (no insecure default fallback). Ensure `SECRET_KEY` is defined in `.env` before starting Docker Compose.

### 3. Build and Start the Containers

From the repository root on Windows (PowerShell or CMD):

```powershell
docker compose up --build
```

*(To run in detached background mode, add `-d`: `docker compose up --build -d`)*

Docker Compose will:
1. Start the **PostgreSQL 16** database (`db`) and wait until its healthcheck passes.
2. Build the **Backend** image (Python 3.12-slim, non-root user `appuser`, `requirements/production.txt`).
3. Execute the image entrypoint (`scripts/entrypoint.sh`), which automatically runs database migrations (`python manage.py migrate --noinput`), collects static assets (`python manage.py collectstatic --noinput`), and launches **Gunicorn** on port `8000`.
4. Wait for the backend healthcheck (`/health/`) to become healthy.
5. Build the multi-stage **Frontend** image (Node 20 build stage with `VITE_API_URL=http://localhost:8000/api/v1`, served via Nginx with SPA fallback and security headers).
6. Start the frontend on port `3000` once the backend is healthy.

### 4. Which URLs to Open

Once the containers are running, open your browser:
- **Frontend Web Application (React App):** [http://localhost:3000](http://localhost:3000)
- **Backend REST API Root:** [http://localhost:8000/api/v1/](http://localhost:8000/api/v1/)
- **Interactive Swagger Documentation:** [http://localhost:8000/docs/](http://localhost:8000/docs/)
- **Django Admin Interface:** [http://localhost:8000/admin/](http://localhost:8000/admin/)

### 5. Create a Superuser in Docker (Optional)

To create a superuser for accessing the Django Admin:

```powershell
docker compose exec backend python manage.py createsuperuser
```

### 6. Stopping the Containers

```powershell
docker compose down
```
*(To stop and also delete database volumes: `docker compose down -v`)*


---

## 🧪 Running Tests & Linting

### Running Tests
The test suite uses `pytest` with `pytest-django`:

```powershell
# Run the complete test suite
.\.venv\Scripts\pytest

# Run tests with detailed verbose output
.\.venv\Scripts\pytest -v

# Run only view/API integration tests
.\.venv\Scripts\pytest apps/habits/tests/test_views.py
```

### Linting & Formatting
Code style and quality are enforced with [Ruff](https://astral.sh/ruff):

```powershell
# Check linting
.\.venv\Scripts\ruff check .

# Check formatting
.\.venv\Scripts\ruff format --check .

# Auto-format codebase
.\.venv\Scripts\ruff format .
```

### Frontend Tests & Quality Checks
Frontend tests and checks run inside `frontend/`:

```powershell
cd frontend

# Run ESLint
npm run lint

# Run Vitest test suite
npm test

# Production build check
npm run build
```


---

## 🔐 Authentication & JWT Workflow

All `/api/v1/habits/` endpoints require JWT (JSON Web Token) authentication. User data is strictly isolated per account.

Rate limiting is enforced on auth endpoints (`5 requests/minute per IP`) to protect against brute-force attacks.

### 1. Register an Account (`POST /api/v1/auth/register/`)

Create a new user account. Email addresses are case-insensitive and stored lowercased (e.g. `User@Example.com` is stored as `user@example.com`).

**Request Body:**
```json
{
  "email": "anna@example.com",
  "password": "StrongPassword123!"
}
```

**Response (`201 Created`):**
```json
{
  "id": 1,
  "email": "anna@example.com"
}
```

### 2. Obtain JWT Token Pair (`POST /api/v1/auth/token/`)

Log in using your email (case-insensitive) and password to obtain an access and refresh token pair:

**Request Body:**
```json
{
  "email": "Anna@example.com",
  "password": "StrongPassword123!"
}
```

**Response (`200 OK`):**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

- **Access Token Lifetime**: 60 minutes
- **Refresh Token Lifetime**: 7 days

### 3. Use "Authorize" in Swagger UI (`/docs/`)

When using the interactive documentation at [http://127.0.0.1:8000/docs/](http://127.0.0.1:8000/docs/):

1. Click the green **Authorize** 🔓 button located in the top-right corner of the Swagger page.
2. In the **jwtAuth (http, Bearer)** popup, enter your token in the **Value** field:
   ```
   Bearer <your_access_token>
   ```
   *(Or paste `<your_access_token>` directly; Swagger UI automatically prefixes with `Bearer` if needed).*
3. Click **Authorize**, then click **Close**.
4. The lock icon will change to locked 🔒 and all subsequent "Try it out" endpoint executions will automatically send the header.

### 4. Call Endpoints with `Authorization: Bearer <token>`

Pass the access token in the `Authorization` HTTP header with the `Bearer ` prefix:

**cURL Example:**
```bash
curl -X GET http://127.0.0.1:8000/api/v1/habits/ \
  -H "Authorization: Bearer <your_access_token>"
```

**PowerShell Example:**
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/habits/" `
  -Headers @{ Authorization = "Bearer <your_access_token>" }
```

**HTTP Header Example:**
```http
GET /api/v1/habits/ HTTP/1.1
Host: 127.0.0.1:8000
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 5. Refresh an Expired Access Token (`POST /api/v1/auth/token/refresh/`)

When an access token expires (after 60 minutes, returning `401 Unauthorized` with `code: "token_not_valid"`), use the `refresh` token to obtain a fresh access token without re-entering credentials:

**Request Body:**
```json
{
  "refresh": "<your_refresh_token>"
}
```

**Response (`200 OK`):**
```json
{
  "access": "<new_access_token>"
}
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
