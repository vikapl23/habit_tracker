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
