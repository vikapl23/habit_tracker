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

## ADR 006: Client-Side Browser Timezone Detection over IP Geolocation

### Date
2026-10-26

### Context & Problem
Accurate timezone resolution is critical for the habit tracker: daily check-in resets, future date validation, scheduling, and streak calculations depend directly on the user's local calendar day. Users travel across time zones, change systems, or switch devices. Two primary architectural options were evaluated for automatic timezone synchronization:
1. **Server-Side IP Geolocation**: Querying MaxMind GeoIP database or external IP geolocation web APIs (e.g. ipinfo.io, ipapi.co) based on client IP headers (`X-Forwarded-For`).
2. **Client-Side Browser Timezone Detection (`Intl.DateTimeFormat`)**: Querying the client environment via ECMAScript's native `Intl.DateTimeFormat().resolvedOptions().timeZone` on application mount and login, then silently updating the user's profile (`PATCH /api/v1/auth/profile/`) when `timezone_auto` is enabled.

### Decision
Adopt **Client-Side Browser Timezone Detection (`Intl.DateTimeFormat`)**:
1. When `timezone_auto` is enabled (default `True`), the frontend resolves the client IANA timezone via `Intl.DateTimeFormat().resolvedOptions().timeZone` on application boot and post-login.
2. If the resolved timezone differs from the persisted timezone, normalize legacy names (e.g. `Europe/Kiev` to `Europe/Kyiv`) and issue a silent `PATCH /api/v1/auth/profile/` with the new timezone. If identical, no network request is sent.
3. If `timezone_auto` is `False` (manual mode), the frontend never overwrites the chosen timezone.

### Rationale & Trade-offs
- **Accuracy with VPN and Mobile Networks**:
  - IP geolocation frequently pinpoints users to data centers, corporate VPN exit nodes, or mobile carrier proxy hubs hundreds or thousands of miles away from their actual physical clock time. Browser timezone detection reflects the user's actual device clock and local wall time regardless of VPN or proxy tunnels.
- **No Third-Party Database or External Service Dependency**:
  - Eliminates external API call latency, third-party network failure points, and monthly subscription limits.
  - Avoids bundling or routinely downloading/maintaining heavy local MaxMind GeoIP binary databases on ephemeral containers.
- **Privacy First**:
  - No IP address or location metadata is logged, queried, or leaked to third-party tracking services.
- **Works Seamlessly Behind Cloud Reverse Proxies (Render.com)**:
  - Behind Render's multi-tier load balancers and reverse proxies, extracting accurate client IPs requires trusting specific proxy headers (`X-Forwarded-For`), which can be spoofed or masked. Native browser detection operates end-to-end within the user agent.

## ADR 007: Architecture for Measurable Habits (Type, Unit, Target, Atomic Increment & Service Streaks)

### Date
2026-10-26

### Context & Problem
Until Phase 8, habits in Habit Tracker were binary (done or not done). Users need to track quantitative habits (e.g. "Drink 2.5 L water", "Read 20 pages", "Walk 5 km").
Specific requirements dictate:
1. Habit type is either `"boolean"` (default) or `"measurable"`. Measurable habits require a `unit` (free text with suggestions) and `target_value` (positive number, decimals allowed, max 100,000, 2 decimal places).
2. Multiple check-ins on the same day must add up (+2 glasses, then +3 glasses = 5). Users can decrease or reset the day's total. Rapid "+" taps must be protected against race conditions and lost updates.
3. Fast exact amount input: setting exact amount (or 0 to reset) via `mode: "set"`.
4. Consistent field naming across model and API: `habit_type`, `unit`, `target_value`, `today_value`, `today_progress`.
5. Return numeric quantities as JSON numbers (not DRF string decimals).
6. A day is completed only when the day's total >= target_value.
7. ONE shared helper for completion must be used everywhere (streaks, is_checked_today, today_progress, statistics completion rates, calendar).
8. Existing habits become boolean via safe data migration. Changing habit type or target must recalculate stored streaks. Streaks recalculation must be orchestrated from the service layer (`services/`), NOT inside `Habit.save()`.
9. Changing the target will recalculate existing streaks under the new threshold; user must see a warning in the edit form.
10. "uncheck" for measurable habits: "-" button always sends a decrement value; uncheck without value removes the whole day only on explicit "Reset day".
11. Limits: value and target max 100,000, 2 decimal places. Check without value for measurable habit adds 1.

### Decision
1. **Model Architecture**:
   - `Habit`: Add `habit_type` (`CharField` with choices `boolean`, `measurable`, default `boolean`). Add `target_value` (`DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)`), and `unit` (`CharField(max_length=30, blank=True, default='')`).
   - `HabitCheckIn`: Add `value` (`DecimalField(max_digits=8, decimal_places=2, default=1.0)`). Maintain the existing unique constraint `(habit, date)` where each record represents the daily accumulated total for that date.
2. **Atomic Concurrency Protection & Check-In Modes**:
   - For measurable habits, `POST /habits/{id}/check/` accepts `mode` (`"add"` by default, or `"set"`) and `value` (positive decimal, max 100,000, 2 decimal places):
     - `mode="add"`: if no `value` is provided, default `value=1.00`. Uses `select_for_update()` inside a database transaction on `HabitCheckIn` (or creates a new record) and adds `value` atomically.
     - `mode="set"`: sets exact value for that day. If `value <= 0`, removes the check-in record.
   - For boolean habits, `value` or `mode="set"` is disallowed (`400 Bad Request`).
3. **Decrement & Explicit Reset**:
   - `POST /habits/{id}/uncheck/`:
     - If `value` is provided (e.g. from "-" button): decrements the day's total atomically. If new total <= 0, the check-in is removed.
     - If `value` is omitted (explicit reset): removes the check-in entirely.
     - For boolean habits: removes the check-in.
4. **Single Shared Completion Helper**:
   - Centralize completion logic in `apps/habits/services/completion.py`: `is_day_completed(habit, value_or_checkin) -> bool`.
   - Used uniformly across:
     - `Habit.get_current_streak` and `apps/habits/services/streaks.py` (`calculate_streaks`, `calculate_habit_streaks`).
     - `HabitSerializer.get_is_checked_today` and `HabitSerializer.get_today_progress`.
     - `apps/habits/services/statistics.py` (`calculate_habit_statistics`, `calculate_user_summary_statistics`).
     - Frontend calendar and cards.
5. **Streak Recalculation in Services Layer (Not in Habit.save)**:
   - In accordance with thin models / rich services architecture, streak recalculations are NOT triggered inside `Habit.save()`.
   - When a habit is updated via `update_habit(...)` service (or `HabitViewSet.perform_update`), if `habit_type` or `target_value` has changed, the service invokes `recalculate_habit_streaks(habit)` so streaks reflect the new threshold immediately.
   - A clear warning banner is displayed in the frontend habit edit form: *"Changing the target will recalculate your streak"*.
6. **JSON Number Serialization**:
   - Return `target_value`, `today_value`, `today_progress`, and check-in `value` as JSON numbers (float/int) rather than strings by configuring `coerce_to_string = False` or float conversion in DRF serializers.
7. **Zero N+1 Query Guarantee**:
   - Use annotations and single query aggregations on list views and statistics, tested with `django_assert_num_queries`.

## ADR 008: Email Notifications via Mailgun, Timezone Window Dispatch, and Signed Unsubscribe Tokens

### Date
2026-10-26

### Context & Problem
Users need automated reminders to sustain habit consistency and weekly summaries to reflect on progress.
Key design challenges:
1. Multi-timezone user base: users are distributed globally; reminder time (e.g. 20:00) must trigger according to each user's local wall clock, not server time.
2. Deduplication & Idempotency: external schedulers / cron jobs can trigger repeatedly or overlap; reminders must never be sent twice on the same day or week.
3. No email spam: if a user has already completed all habits scheduled for today (boolean or measurable targets met), daily reminders must be skipped.
4. Privacy & Unsubscribe: users must be able to unsubscribe instantly from any email without requiring authentication, while preventing unauthorized unsubscriptions.
5. Environment separation: avoid committing API keys, support Mailgun in production via `django-anymail`, fall back to console backend in local dev, and use `locmem` in automated tests.

### Decision
1. **Email Backend Architecture (`django-anymail[mailgun]`)**:
   - Integrated `django-anymail` with Mailgun backend in `config/settings/base.py`.
   - Dynamic fallback: if `MAILGUN_API_KEY` is not present, local development uses `django.core.mail.backends.console.EmailBackend`.
   - Test suite strictly uses `django.core.mail.backends.locmem.EmailBackend`.
   - All credentials (`MAILGUN_API_KEY`, `MAILGUN_DOMAIN`, `MAILGUN_API_URL`, `DEFAULT_FROM_EMAIL`, `CRON_TOKEN`) are configured through environment variables with empty placeholders in `.env.example`.
2. **User Notification Settings**:
   - Added `daily_reminder_enabled` (default `False`), `daily_reminder_time` (default `20:00:00`), and `weekly_summary_enabled` (default `False`) to `accounts.User`.
   - Exposed via `GET /api/v1/auth/profile/` and `PATCH /api/v1/auth/profile/` in `UserProfileSerializer`.
3. **15-Minute Window & Timezone Resolution**:
   - The dispatch engine divides each hour into 4 15-minute buckets (`[0, 15)`, `[15, 30)`, `[30, 45)`, `[45, 60)`).
   - In `send_due_notifications(now, force=False)`, `now` is converted to each candidate user's IANA timezone. A user is selected when their local time bucket matches `daily_reminder_time` (or unconditionally when `force=True`).
4. **Idempotency via `NotificationLog`**:
   - Added `NotificationLog` model with database-level `UniqueConstraint(user, notification_type, scheduled_date)`:
     - Daily reminders are recorded with `scheduled_date=user_today`.
     - Weekly summaries are recorded with `scheduled_date=start_of_week` (Monday).
   - Subsequent cron executions within the same day or week detect existing log records and safely skip.
5. **Shared Completion Logic**:
   - Daily reminders check habits scheduled for `user_today` using the shared `is_day_completed` helper.
   - If all scheduled habits are completed, or the user has no active scheduled habits today, no email is dispatched.
6. **Stateless Signed Unsubscribe Tokens**:
   - One-click unsubscribe tokens are generated with Django's cryptographic `signing.dumps(user.id, salt=...)`.
   - Public endpoint `GET /api/v1/notifications/unsubscribe/<token>/` decodes and verifies signature, disabling `daily_reminder_enabled` and `weekly_summary_enabled` without requiring login.
7. **Protected Internal Endpoint & Management Command**:
   - `POST /api/v1/internal/send-notifications/` is guarded by `X-Cron-Token` constant-time verification (`secrets.compare_digest`).
   - Management command `python manage.py send_notifications [--force]` enables CLI and manual execution.
8. **GitHub Actions Cron Dispatch & Sleeping Render Instance Resilience**:
   - Automated cron dispatch runs every 15 minutes via `.github/workflows/notifications.yml` (`cron: "*/15 * * * *"` + `workflow_dispatch`), triggering `POST $BACKEND_URL/api/v1/internal/send-notifications/` with `X-Cron-Token: ${{ secrets.CRON_TOKEN }}`.
   - Render free tier instances spin down after inactivity; the workflow catches non-2xx status codes (such as cold boot delays or gateway timeouts) and retries once after 60 seconds, allowing the free tier instance to wake up and finish execution cleanly.
   - If `403 Forbidden` is returned, the workflow aborts immediately without retry to avoid hammering with bad credentials.
   - `SITE_URL` is configured in `render.yaml` (`sync: false`) and must point to the backend URL to generate correct, valid one-click unsubscribe links in notification emails.

### Trade-offs & Implications
- **Advantages**:
  - Zero external task broker dependency (e.g. Celery/Redis) required for scheduled execution; can run on Render Cron Jobs or external webhooks.
  - Constant-time token verification prevents timing attack vulnerabilities on the internal trigger endpoint.
  - Zero duplicate email deliveries even under aggressive retry loops.

## ADR 009: Per-Habit Email Reminders, User Master Switch, and Sunset of Global Daily Reminder

### Date
2026-10-27

### Context & Problem
Previously, notifications featured a single global daily reminder setting on the user model (`daily_reminder_enabled`, `daily_reminder_time`), delivering one evening email for all incomplete habits. In practice, users build routines throughout different parts of the day (e.g., morning meditation at 08:00, workout at 17:30, reading at 21:00). A single daily reminder cannot provide contextual, actionable nudges.

Two architectures were considered to transition away from the single global reminder:
1. **Option A (Simpler)**: Migrate `daily_reminder_enabled` and `daily_reminder_time` into a single global master switch `notifications_enabled` on the user, moving all reminder scheduling directly onto individual habits (`reminder_enabled`, `reminder_time`).
2. **Option B**: Maintain `daily_reminder_enabled` as an optional secondary "evening summary" alongside per-habit reminders.

### Decision
Adopt **Option A**:
1. **Per-Habit Reminder Configuration**:
   - Added `reminder_enabled` (boolean, default `False`) and `reminder_time` (TimeField, nullable) to `Habit`.
   - Strictly validate `reminder_time` in model `clean()` and `HabitSerializer`: `reminder_time` is required when `reminder_enabled` is `True`, and minutes must be one of `[0, 15, 30, 45]`.
2. **Global Master Switch & Sunset of Legacy Daily Reminder**:
   - Replaced `daily_reminder_enabled` and `daily_reminder_time` on `User` with a single global master switch `notifications_enabled` (default `True`).
   - If `notifications_enabled` is `False`, all emails (both habit reminders and weekly summaries) are completely suppressed.
   - Kept `weekly_summary_enabled` (default `False`), delivered on Mondays.
3. **15-Minute Window & User-Level Email Grouping**:
   - `send_due_notifications(now)` evaluates habits for each user with `notifications_enabled=True` in their respective timezone.
   - For all habits with `reminder_enabled=True` whose `reminder_time` matches the current 15-minute window, that are scheduled today according to frequency and NOT completed (using shared `is_day_completed` helper; measurable habits checked for `today_value < target_value`), all due habits are batched into **ONE** consolidated email per user per window.
   - If no habits are due or incomplete, no email is sent.
4. **Per-Habit Daily Deduplication**:
   - `NotificationLog` includes `habit` ForeignKey and partial unique constraint `(habit, scheduled_date)` where `habit IS NOT NULL`, guaranteeing each habit is reminded at most once per calendar day.
5. **One-Click Unsubscribe**:
   - Unsubscribe links contained in notification emails turn off the user's master switch (`notifications_enabled = False`), halting all future emails immediately.

### Trade-offs & Implications
- **Advantages**:
  - Eliminates conflicting notifications and redundant emails: habits prompt users at their intended schedule.
  - Consolidated emails: multiple habits scheduled at the same time slot (e.g., 09:00) produce exactly one email rather than multiple separate emails.
  - Clean, unbloated user profile: one simple master switch in user settings, with granular control situated directly on each habit.




