# Code Review: Phase 9 (Email Notifications, Mailgun, Per-Habit Reminders, Cron & Unsubscribe)

A prioritized code review of the Phase 9 notification system covering security (cron token, unsubscribe tokens, secrets), timezone windows, duplicate prevention, scalability and query performance, Mailgun error handling, and test coverage.

---

## 1. Critical

### 1. [FIXED] State-Mutating Unsubscribe on HTTP GET (Email Security Scanners Auto-Unsubscribe Users)
- **File & Line**: `apps/notifications/views.py:68-73, 90-91`
- **Issue**: `UnsubscribeView.get()` directly calls `self._process_unsubscribe(token)`, mutating database state (`user.notifications_enabled = False; user.save(...)`). Modern enterprise email security scanners, antivirus software, and mailbox link prefetchers (e.g., Microsoft Defender Safe Links, Google Workspace, Apple Mail Privacy Protection) automatically issue HTTP `GET` requests on all links in incoming messages upon receipt to check for phishing/malware. As a result, incoming reminder emails automatically unsubscribe users before they even read them. Furthermore, mutating state on `GET` violates HTTP semantics (RFC 7231 / RFC 9110 safe methods) and RFC 8058.
- **Fix**: Make `GET` safe: render a confirmation view with a "Confirm Unsubscribe" button that submits via `POST`, or require `POST` for execution while `GET` returns a confirmation challenge.

### 2. [FIXED] Race Condition on Email Sending Leading to Duplicate Deliveries
- **File & Line**: `apps/notifications/services.py:79-84, 139-156` (reminders) and `apps/notifications/services.py:178-183, 263-275` (weekly summaries)
- **Issue**: Deduplication relies on `NotificationLog.objects.filter(...).exists()` before dispatching, but `NotificationLog.objects.create(...)` is executed strictly *after* `msg.send()`. If two cron triggers overlap (e.g., GitHub Actions scheduled workflow runs concurrently with manual `workflow_dispatch`, or an automated retry executes during a slow initial run), both processes evaluate `exists() == False`, both deliver identical emails to Mailgun, and only then does the second process raise a database `IntegrityError`. The unique constraint prevents double database logs, but fails to prevent duplicate emails reaching users.
- **Fix**: Atomically reserve/create a pending `NotificationLog` record (or acquire an atomic row lock / transaction) *before* calling `msg.send()`. If creation hits an `IntegrityError`, abort immediately before sending.

### 3. [FIXED] Strict 15-Minute Time Window Permanently Misses Notifications on GitHub Actions Queuing Delays
- **File & Line**: `apps/notifications/services.py:42-49, 71-75, 326-327` and `.github/workflows/notifications.yml:4-6`
- **Issue**: `is_reminder_time_in_window()` strictly asserts exact hour and 15-minute bucket equality (`reminder_time.hour == current_time.hour and reminder_time.minute // 15 == current_time.minute // 15`). GitHub Actions cron jobs are best-effort and routinely delayed by 5–25+ minutes under platform load (especially at the top of the hour `:00`). If a cron scheduled for `20:00` executes at `20:16`, `current_time.minute // 15` is `1` while `reminder_time.minute // 15` is `0`. The reminder is skipped, and because the next cron evaluates bucket `2`, the notification is lost for the entire day. The same vulnerability affects `send_weekly_summary`, which is hardcoded strictly to 09:00 local time.
- **Fix**: Query habits where `reminder_time <= user_time` that have not yet been logged in `NotificationLog` for `user_today`, rather than checking only the current 15-minute slice.

### 4. Synchronous O(N) Processing in Web Request Causes Gunicorn / HTTP Timeouts at Scale
- **File & Line**: `apps/notifications/services.py:300-333` and `apps/notifications/views.py:50-57`
- **Issue**: `send_due_notifications` loads all users with `notifications_enabled=True` in an unpaginated loop inside a synchronous foreground HTTP request. For each user, it executes synchronous database queries and external HTTP calls to Mailgun (`msg.send()`). At ~200–400ms per Mailgun API request, notifying 200 users takes 40–80 seconds. This exceeds Gunicorn's default 30–60s worker timeout and GitHub Actions' curl `--max-time 90`, aborting the process midway with HTTP 502/504 and triggering the workflow's retry mechanism.
- **Fix**: Offload notification delivery to background tasks (Celery/RQ or an asynchronous runner) or chunk user batches with a strict execution budget, or invoke dispatch via a direct CLI management command rather than an HTTP webhook.

---

## 2. Important

### 5. [FIXED] N+1 Database Queries Inside User Dispatch Loop
- **File & Line**: `apps/notifications/services.py:65, 79-82, 144-156, 185-198`
- **Issue**: `send_due_notifications()` iterates over all `User.objects.filter(notifications_enabled=True)`. In every iteration, `user.habits.filter(is_archived=False, reminder_enabled=True)` runs a separate query, even for users whose local time does not match the window. Each due habit then executes individual `NotificationLog.objects.filter(...)` and individual `NotificationLog.objects.create(...)` queries. For 1,000 active users, this results in thousands of synchronous database round-trips every 15 minutes.
- **Fix**: Query active habits directly (`Habit.objects.filter(reminder_enabled=True, is_archived=False, user__notifications_enabled=True).select_related('user')`), prefetch today's logs and check-ins in bulk, and use `NotificationLog.objects.bulk_create()`.

### 6. Missing RFC 8058 One-Click Unsubscribe Headers
- **File & Line**: `apps/notifications/services.py:132-139, 256-263`
- **Issue**: Outgoing reminder and summary emails lack `List-Unsubscribe` and `List-Unsubscribe-Post: List-Unsubscribe=One-Click` MIME headers. Major inbox providers (Google and Yahoo) enforce RFC 8058 compliance for transactional and bulk emails; missing headers increase the likelihood of emails being routed to Spam or rejected by recipient servers.
- **Fix**: Add `List-Unsubscribe` (pointing to `<{unsubscribe_url}>`) and `List-Unsubscribe-Post: List-Unsubscribe=One-Click` to `msg.extra_headers`.

### 7. [FIXED] Silent Fallback to Console Email Backend and Missing Secret Validations in Production
- **File & Line**: `config/settings/base.py:162-171` and `config/settings/production.py:9-50`
- **Issue**: If `MAILGUN_API_KEY` is not set, `base.py` silently falls back to `django.core.mail.backends.console.EmailBackend`. Unlike `SECRET_KEY` and `ALLOWED_HOSTS`, `production.py` does not validate that `MAILGUN_API_KEY`, `MAILGUN_DOMAIN`, or `CRON_TOKEN` are present and non-empty. A misconfigured production instance starts successfully but silently discards all outgoing emails to container logs and rejects all incoming cron requests with 403 Forbidden.
- **Fix**: Add startup validation in `config/settings/production.py` raising `ImproperlyConfigured` if `CRON_TOKEN`, `MAILGUN_API_KEY`, or `MAILGUN_DOMAIN` are unset or empty.

### 8. Cron Endpoint Lacks Rate Limiting and Failure Observability
- **File & Line**: `apps/notifications/views.py:19-58` and `apps/notifications/services.py:321-322, 331-332`
- **Issue**:
  1. `SendNotificationsInternalView` has no throttling classes configured (`permission_classes = [permissions.AllowAny]`), allowing arbitrary clients to flood the endpoint and exhaust server resources.
  2. `send_due_notifications` catches individual delivery errors via `logger.exception` but does not record failed counts or error statuses. The API endpoint unconditionally returns HTTP 200 with `"status": "success"` even when 100% of emails fail to send due to Mailgun API/credential errors, masking outages from GitHub Actions and external monitors.
- **Fix**: Add scoped rate limiting to `SendNotificationsInternalView`, track `failed_count` in `send_due_notifications`, and return an error status or error breakdown if partial or total delivery failure occurs.

### 9. [FIXED] Unsubscribe Endpoint Renders Raw JSON to Browser Users
- **File & Line**: `apps/notifications/views.py:93-98` and `apps/notifications/tokens.py:34-37`
- **Issue**: When a user clicks the unsubscribe link in an email, the link opens `https://<SITE_URL>/api/v1/notifications/unsubscribe/<token>/`. The response is a raw DRF JSON payload (`{"detail": "...", "unsubscribed": True}`). For end users clicking from an email client on mobile or desktop, viewing raw JSON in the browser appears broken and unpolished.
- **Fix**: Render a styled HTML confirmation template or redirect to a dedicated frontend landing page (e.g. `${SITE_URL}/unsubscribed`).

### 10. [FIXED] Missing Test Coverage for External Failures, Query Counts, Concurrency, and Cron Delays
- **File & Line**: `apps/notifications/tests/test_services.py` and `apps/notifications/tests/test_views_and_commands.py`
- **Issue**:
  - No test verifying behavior when Mailgun raises an API exception or network timeout (`AnymailAPIError`, `RequestException`).
  - No concurrency test verifying that simultaneous cron triggers cannot send duplicate emails.
  - No query count assertions (`django_assert_num_queries`) to prevent N+1 query regressions during notification dispatch.
  - No test verifying resilience against delayed cron executions (e.g., cron running 15 minutes past reminder time).
  - No test verifying `List-Unsubscribe` email headers.
- **Fix**: Add dedicated test cases covering Mailgun exceptions, query limits, concurrent dispatch protection, and delayed cron windows.

---

## 3. Nice-to-Have

### 11. Semantic Mismatch in Notification Log Type Choice
- **File & Line**: `apps/notifications/models.py:15-17` and `apps/notifications/services.py:147`
- **Issue**: `NotificationLog.NotificationType` defines `HABIT_REMINDER = "habit_reminder"`, but `send_habit_reminders_for_user()` logs records with `NotificationLog.NotificationType.DAILY_REMINDER`. `HABIT_REMINDER` is dead code, and audit logs label per-habit reminders as legacy daily reminders.
- **Fix**: Set `notification_type=NotificationLog.NotificationType.HABIT_REMINDER` in `send_habit_reminders_for_user()`.

### 12. Discrepant Timezone Fallback Between User Model and Service Layer
- **File & Line**: `apps/accounts/models.py:91-93` and `apps/notifications/services.py:305-306`
- **Issue**: `User.get_today()` falls back to `"Europe/Kyiv"` if `user.timezone` is invalid, whereas `send_due_notifications()` falls back to `"UTC"`. If an invalid timezone string were present in the database, the user's dashboard date and reminder date calculations would diverge.
- **Fix**: Standardize both fallbacks to `"UTC"`.

### 13. Unsubscribe Token Lacks Invalidation or Expiry Mechanism
- **File & Line**: `apps/notifications/tokens.py:16, 22-27`
- **Issue**: `signing.dumps({"user_id": user.pk}, salt=UNSUBSCRIBE_SALT)` includes only `user_id`. It does not include a hash of the user's current credentials/salt version or an expiry window. If a user unsubscribes and later re-enables notifications in settings, old links in historical emails remain active indefinitely and could inadvertently toggle off notifications if clicked again.
- **Fix**: Use Django's `TimestampSigner` with an expiration window, or include a token version / hash of user state in the payload.

### 14. Potential Sensitive Information Leak in Workflow Logs
- **File & Line**: `.github/workflows/notifications.yml:58, 89`
- **Issue**: `echo "Response: $BODY"` unconditionally prints the full backend HTTP response body to workflow run logs. In the event of an unexpected 500 error or uncaught exception, internal tracebacks or server metadata could be logged to public GitHub Actions runs.
- **Fix**: Sanitize or truncate `$BODY` in workflow logs, logging only HTTP status code and parsed JSON summary keys.
