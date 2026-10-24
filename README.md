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

## ☁️ Deployment (Render.com)

The application includes a [Render Blueprint](https://render.com/docs/blueprint-spec) (`render.yaml`) to deploy the complete stack using free plans:
- **Managed PostgreSQL Database** (`habit-tracker-db`): Free PostgreSQL instance.
- **Backend Web Service** (`habit-tracker-backend`): Docker container running Django, automated migrations, static asset collection, and Gunicorn.
- **Frontend Static Site** (`habit-tracker-frontend`): Built with Vite and served globally with custom security headers and SPA routing rewrites.

> [!WARNING]
> **Free Tier Limitations on Render:**
> - **Temporary Database:** Render's free PostgreSQL instances are temporary (expire after 30 days of creation). For long-term production use, upgrade to a paid PostgreSQL instance or export periodic backups.
> - **Instance Spin-down / Cold Starts:** Free web services spin down (sleep) after 15 minutes of inactivity. The first incoming request after sleep will take 30–60 seconds to wake up the backend.

### 1. Step-by-Step Render Dashboard Deployment

1. **Push your code to GitHub:**
   Ensure all changes including `render.yaml`, `Dockerfile`, and `frontend/` are pushed to your GitHub repository.
2. **Open Render Dashboard:**
   Log in to [Render.com](https://dashboard.render.com/).
3. **Create New Blueprint Instance:**
   - In the top right, click **New +** and select **Blueprint**.
   - Connect your GitHub repository (e.g. `your-username/habit_tracker`).
   - Give the Blueprint instance a name (e.g. `habit-tracker`).
   - Select the branch (e.g. `main`).
   - Render parses `render.yaml` and lists three resources: `habit-tracker-db` (Postgres), `habit-tracker-backend` (Web Service), and `habit-tracker-frontend` (Static Site).
4. **Initial Deploy & Blueprint Creation:**
   - Click **Apply**.
   - Render immediately creates the database and generates a secure random `SECRET_KEY`.
   - The initial build of backend and frontend will start. Note that they require post-creation configuration of their respective URLs as explained below.

---

### 2. Environment Variables & Two-Step Linking Process

Because Render assigns subdomains only *after* services are created, the frontend and backend URLs must be configured in two simple steps:

```
Step 1: Backend URL  ─────────────►  Set Frontend VITE_API_URL  ─────────────►  Redeploy Frontend
                                                                                        │
Step 2: Backend CORS / ALLOWED_HOSTS  ◄───────────────────────────  Frontend URL  ──────┘
          │
          ▼
Redeploy Backend
```

#### Step A: Configure Frontend `VITE_API_URL`
1. Go to the **habit-tracker-backend** service page in the Render dashboard.
2. Copy its public URL from the top header (e.g. `https://habit-tracker-backend-xyz.onrender.com`).
3. Navigate to the **habit-tracker-frontend** Static Site in Render.
4. Go to **Environment** tab, edit `VITE_API_URL`, and set:
   ```
   https://habit-tracker-backend-xyz.onrender.com/api/v1
   ```
   *(Be sure to append `/api/v1` and ensure it uses `https://`).*
5. Save changes. Go to **Deploys** and click **Manual Deploy > Clear build cache & deploy** so Vite bakes the production API URL into the built bundle.

#### Step B: Configure Backend `ALLOWED_HOSTS` & `CORS_ALLOWED_ORIGINS`
1. Copy the public URL of **habit-tracker-frontend** (e.g. `https://habit-tracker-frontend-abc.onrender.com`).
2. Navigate to the **habit-tracker-backend** service in Render.
3. Go to **Environment** tab, find:
   - `ALLOWED_HOSTS`: set to your backend host name (comma-separated, without scheme):
     ```
     habit-tracker-backend-xyz.onrender.com
     ```
   - `CORS_ALLOWED_ORIGINS`: set to your frontend origin (comma-separated, with `https://`):
     ```
     https://habit-tracker-frontend-abc.onrender.com
     ```
4. Click **Save Changes**. Render will automatically trigger a rolling redeploy of the backend.

---

### 3. Creating a Django Superuser on Render

On Render's free plan, interactive SSH / Shell access is not available. To create an initial admin superuser:

1. In the Render Dashboard, navigate to your **habit-tracker-backend** service.
2. Go to the **Environment** tab.
3. Set the following environment variables:
   - `DJANGO_SUPERUSER_EMAIL`: your admin email address (e.g. `admin@example.com`).
   - `DJANGO_SUPERUSER_PASSWORD`: a strong, secure admin password.
4. Save changes. On deployment/startup, `scripts/entrypoint.sh` runs database migrations and then creates the superuser non-interactively via `python manage.py createsuperuser --noinput` (it will not fail or overwrite if the user already exists, and the password is never logged).
5. Open `https://<your-backend-url>/admin/` in your browser and sign in.
6. *(Recommended)* Once the superuser is created, you may remove `DJANGO_SUPERUSER_PASSWORD` from the Render environment variables if desired.

> [!NOTE]
> On paid Render plans with interactive Shell access, you can also run `python manage.py createsuperuser` directly in the web shell.

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
