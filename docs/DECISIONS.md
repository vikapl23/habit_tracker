# Architecture and Security Decisions

## ADR 001: Generic Registration Response (Anti-User Enumeration)

### Date
2026-10-23

### Context & Problem
Previously, `/api/v1/auth/register/` used DRF's default model uniqueness validation on `User.email`. When an already-registered email was submitted, the endpoint responded with `HTTP 400 Bad Request` and `{"email": ["user with this email already exists."]}`.

This allowed unauthenticated attackers to enumerate valid email addresses registered in the system (account harvesting / user enumeration attack), violating security best practices (OWASP Authentication Cheat Sheet, Mentor Review item 8).

### Decision
1. Remove email uniqueness validation from `RegisterSerializer` while preserving email format validation and password validation.
2. In `RegisterView`, return an identical generic response (`HTTP 201 Created` with `{"detail": "User registered successfully."}`) whether the email is newly registered or already exists in the database.
3. If an existing email is submitted, do not create a duplicate user and do not overwrite or modify existing user credentials.
4. Normalize emails to lower case before querying or creating user records.

### Trade-offs & UX Implications
- **Security Advantages:**
  - Complete mitigation of user enumeration via the registration endpoint. Attackers cannot distinguish between existing and non-existing accounts.
  - Safe against race conditions and concurrent registration requests via database-level uniqueness constraints and handled exceptions.

- **User Experience (UX) Trade-offs:**
  - **No immediate feedback for duplicate registrations:** Legitimate users who forget they already registered will receive a generic confirmation rather than a reminder that their account already exists and they should log in or reset their password.
  - **Password confusion:** If an existing user attempts to register again with a new password, the new password is intentionally ignored (to prevent unauthorized account hijacking/overwrite). The user may subsequently struggle to log in with the newly attempted password.

- **Mitigation & Future Improvements:**
  - Once transactional email delivery (e.g., SendGrid, Amazon SES) is introduced, the registration flow should trigger a transactional email notification:
    - If the user is new: send an account activation or welcome email.
    - If the user already exists: send a security notice stating that a registration attempt occurred for their existing account, accompanied by a password reset link.

## ADR 002: User Timezone and Per-User Date Evaluation

### Date
2026-10-23

### Context & Problem
Previously, server `TIME_ZONE` was hardcoded to `Europe/Kyiv`. Business logic for check-in defaults, future date check-in validations, `is_checked_today`, and streak computations relied on server-local dates (`django.utils.timezone.localdate()`), assuming all users operated under Kyiv time. Users located in other time zones (e.g. UTC, America/New_York) suffered incorrect streaks, mismatched check-in dates, and premature or delayed midnight rollovers. In addition, `is_checked_today` took a `?date=` query parameter and silently ignored invalid inputs rather than returning a 400 client error (Mentor Review item 3).

### Decision
1. **Server Timezone Reset to UTC**: Set server `TIME_ZONE = "UTC"` with `USE_TZ = True` in `config/settings/base.py`.
2. **User Timezone Field**: Add a `timezone` field to `User` (`max_length=64`, default `"Europe/Kyiv"`), validated against IANA time zones using Python's standard library `zoneinfo.available_timezones()`. Provide a helper method `user.get_today()` returning the user's current date in their specific timezone.
3. **Settable at Registration and Profile Endpoints**:
   - `POST /api/v1/auth/register/` optionally accepts `timezone` (validated against IANA names, returns 400 on invalid value).
   - Add `GET` and `PATCH` `/api/v1/auth/profile/` requiring authentication to inspect and update user timezone.
4. **Per-User Date Context**:
   - Default check-in date (`POST /api/v1/habits/{id}/check/` and `uncheck`) defaults to the user's local date.
   - Future date check-in validation (`HabitCheckIn.clean`, `HabitCheckInSerializer`, and `CheckInActionSerializer`) compares against the user's current date.
   - `is_checked_today` and streak calculations (`calculate_habit_streaks`) evaluate relative to the user's local date.
5. **Strict Query Parameter Validation**:
   - If an invalid `?date=` query parameter is supplied to habit endpoints (list, retrieve), the API returns `HTTP 400 Bad Request` with `{"date": [...]}` instead of silently ignoring invalid values.

### Trade-offs & UX Implications
- **Advantages:**
  - Preserves standard UTC timestamp consistency across all server logs, database tables, and Django models.
  - Accurate streak tracking and habit check-in boundaries across all international time zones and daylight saving time (DST) shifts.
  - Strict input validation prevents subtle client bugs and silent parameter corruption.
- **Trade-offs:**
  - Habit queries and streak calculations now depend on user timezone context. To avoid N+1 queries when evaluating streaks across habit lists, queries select the related user (`select_related("user")`).

## ADR 003: Persisted Habit Streaks and Scoped User Compound Index

### Date
2026-10-23

### Context & Problem
Previously, the habits list view (`GET /api/v1/habits/`) executed `prefetch_related("check_ins")` to load every historical check-in for every habit just to calculate `current_streak`, `longest_streak`, and `is_checked_today` in memory via `HabitSerializer`. As users accumulate check-ins over months and years, memory usage and database payload grow without bound (Mentor Review item 6).
Additionally, the compound database index on `Habit` was `(is_archived, -created_at)`, omitting `user` which is the mandatory scoping filter for authenticated multi-tenant queries.

### Decision
1. **Model Fields**: Add `current_streak` (`PositiveIntegerField`, default 0), `longest_streak` (`PositiveIntegerField`, default 0), and `last_check_in_date` (`DateField`, nullable) to `Habit`.
2. **Compound Index**: Replace `(is_archived, -created_at)` with `(user, is_archived, -created_at)`.
3. **Streak Recalculation Service**: Provide `recalculate_habit_streaks(habit, reference_date)` in `apps/habits/services/streaks.py`. On check-in (`check_in_habit`) and check-in removal (`uncheck_habit`), persist the updated streaks and latest check-in date.
4. **Management Command**: Provide `python manage.py recalculate_streaks` to recalculate streaks for all habits (with optional `--habit-id` and `--user-id` filters).
5. **Read-Time Streak Decay**: If days pass without check-ins, `current_streak` becomes 0 dynamically at read time (`Habit.get_current_streak(reference_date)`) by comparing `last_check_in_date` with the user's `today` (elapsed days > 1), without mutating the database and without loading check-ins.
6. **Query Optimization**: Remove `prefetch_related("check_ins")` from `HabitViewSet.get_queryset()`. In `HabitSerializer`, evaluate `is_checked_today` and `current_streak` without querying check-ins during normal list views.

## ADR 004: In-Memory Access Token with Storage Refresh Token and Strict CSP (Option C)

### Date
2026-10-24

### Context & Problem
Previously, access and refresh tokens were both stored in `localStorage`, without a Content-Security-Policy (CSP). Any malicious or compromised dependency executing in the page could exfiltrate the 7-day refresh token. Because refresh token rotation blacklists previous tokens, stolen tokens could be continuously rotated by an attacker while simultaneously locking out legitimate users.

Two alternative architectures were evaluated:
1. **Option B (HttpOnly Refresh Cookie + In-Memory Access Token)**: The backend sets an `HttpOnly` cookie for the refresh token. However, because the production frontend and backend will be hosted on separate Render subdomains (`*.onrender.com`), and `onrender.com` is listed in the Public Suffix List (PSL), cookies cannot be shared across different subdomains as first-party cookies. In browsers with strict privacy protections (e.g. Safari / iOS WebKit ITP), cross-site cookies are blocked by default. Without configuring a custom domain or an API reverse proxy, Option B would break authentication for mobile Safari users.
2. **Option C (In-Memory Access Token + localStorage Refresh Token + Strict CSP)**: Keep the short-lived access token strictly in JavaScript memory (never written to `localStorage` or `sessionStorage`), store the refresh token in `localStorage`, silently refresh on application mount/reload, coordinate cross-tab refresh via Web Locks API and BroadcastChannel, and enforce a strict CSP on production builds.

### Decision
1. Adopt **Option C**:
   - Store access tokens strictly in module-scoped memory (`client.ts`).
   - Store the refresh token in `localStorage`.
   - On initial app boot, silently call `refreshTokens()` if a refresh token is present to retrieve a valid in-memory access token.
2. **Cross-Tab Concurrency (C2)**:
   - Coordinate token refresh using the `navigator.locks` Web Locks API (with fallback) and broadcast rotation updates via `BroadcastChannel`.
   - If a tab acquires the lock or encounters a refresh response, it checks whether another tab has already rotated the refresh token in storage before clearing session state.
3. **Strict Content Security Policy (CSP)**:
   - Inject CSP meta tags in production builds only (`apply: 'build'`) via Vite HTML plugin:
     `default-src 'self'; connect-src 'self' <VITE_API_URL origin>; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; object-src 'none'; base-uri 'none'`.
   - `frame-ancestors` is omitted from the `<meta>` tag because browsers strictly ignore `frame-ancestors` inside HTML meta elements (W3C CSP Level 2/3 specification).
   - In production environments, `frame-ancestors 'none'`, along with `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, and `Strict-Transport-Security`, are delivered as standard HTTP response headers from the reverse proxy / web server (nginx in Docker and Render edge).

### Trade-offs & Implications
- **Advantages**:
  - Functions reliably across arbitrary third-party subdomains without requiring custom domains or cross-site cookie workarounds.
  - Prevents persistent access token extraction from disk/storage.
  - Prevents cross-tab race conditions and inadvertent global blacklisting logouts.
  - Strict CSP mitigates script injection vectors.
- **Trade-offs**:
  - The refresh token remains in `localStorage`. If an attacker bypasses the CSP and executes arbitrary script, the refresh token could still be read from `localStorage`. Defense relies on CSP and dependency auditing.

## ADR 005: Production-Parity Docker Setup, WhiteNoise, and Standalone Container Entrypoint

### Date
2026-10-24

### Context & Problem
Review of the initial Phase 6 Docker Compose setup revealed four issues:
1. `docker-compose.yml` ran with `DJANGO_SETTINGS_MODULE=config.settings.base` because `config.settings.production` enforced strict HTTPS rules (`SECURE_SSL_REDIRECT`, HTTPS cookies, HSTS, and https:// origin validation on CORS). Under `config.settings.base`, WhiteNoise was not enabled and static files (e.g. `/static/admin/css/base.css`) returned 404 in Docker (breaking Django admin styling). Furthermore, running `base` settings failed to test production-like behavior.
2. Database migration, static collection, and server boot were embedded as an inline command in `docker-compose.yml` rather than packaged inside the Docker container image. As a result, deploying the container directly to platforms like Render required duplicate configuration or external orchestration.
3. `docker-compose.yml` hardcoded a fallback value for `SECRET_KEY`, potentially masking missing secrets and risking insecure production secrets.
4. The frontend container started immediately without verifying whether backend services were initialized and responsive, leading to startup race conditions.

### Decision
1. **WhiteNoise in Base Settings**:
   - Promoted `whitenoise.middleware.WhiteNoiseMiddleware` into `config/settings/base.py` `MIDDLEWARE` directly following `SecurityMiddleware`.
   - Set `STORAGES["staticfiles"]["BACKEND"] = "whitenoise.storage.CompressedManifestStaticFilesStorage"` in base settings so all environments (local, Docker, and production) serve static files consistently.
2. **Configurable Production HTTPS Settings**:
   - In `config/settings/production.py`, made HTTPS enforcement flags configurable via environment variables while defaulting to secure values (`True` / 1 year HSTS):
     - `SECURE_SSL_REDIRECT` (default `True`)
     - `SESSION_COOKIE_SECURE` (default `True`)
     - `CSRF_COOKIE_SECURE` (default `True`)
     - `SECURE_HSTS_SECONDS` (default `31536000`)
     - `SECURE_HSTS_INCLUDE_SUBDOMAINS` (default `True`)
     - `SECURE_HSTS_PRELOAD` (default `True`)
     - `CORS_REQUIRE_HTTPS` (default `True`)
   - `docker-compose.yml` now runs `DJANGO_SETTINGS_MODULE=config.settings.production` with these flags relaxed for local HTTP testing.
3. **Container Entrypoint Script (`scripts/entrypoint.sh`)**:
   - Added `scripts/entrypoint.sh` executing `python manage.py migrate --noinput` and `python manage.py collectstatic --noinput` prior to executing the runtime command (`exec "$@"`).
   - Configured `ENTRYPOINT ["/app/scripts/entrypoint.sh"]` in `Dockerfile` and removed the inline composite command from `docker-compose.yml`.
4. **Mandatory Secret Key in Docker**:
   - Removed the hardcoded fallback `SECRET_KEY` in `docker-compose.yml`. It now reads directly from `.env` (`${SECRET_KEY}`), documented in `.env.example` and `README.md`.
5. **Backend Healthcheck & Dependency Orchestration**:
   - Implemented `/health/` endpoint in Django (`config/views.py` returning `{"status": "ok"}`).
   - Added backend Docker healthcheck querying `/health/` via `curl`.
   - Updated frontend service in `docker-compose.yml` with `depends_on: { backend: { condition: service_healthy } }`.

### Trade-offs & Implications
- **Advantages**:
  - Full production parity in Docker Compose: testing catches settings and static asset delivery discrepancies locally.
  - The backend Docker image is fully self-contained and ready for deployment to Render or cloud orchestrators without extra compose files.
  - No secret keys are hardcoded in repository files.
  - Frontend waits reliably for backend schema migrations and gunicorn startup before serving traffic.
- **Trade-offs**:
  - Relaxing HTTPS flags in `docker-compose.yml` requires environment variables; in staging or production, these variables must remain unset or set to `True`.

