# Mentor Review — Oleksandr Pechak (2026-10-23)

> Reviewed while Phase 2 (JWT) was in progress. Items 1–2, registration throttling and lowercase email were already fixed in later commits.

Що сподобалося:
1. Структура, все чітко і логічно поділено.
2. Налаштований email користувач з самого початку, це важливо.
3. Streak logic файна і круто що то все винесено в services, там і має жити бізнес логіка.
4. Чудово що додала docs це допомагає легше переходити в інші сесії і бачити загальну картину.

Ти велика молодчина, доволі швидко впоралася, дякую за це!

Над чим варто попрацювати:
Critical:
1. No data isolation (security).
views.py builds HabitViewSet.get_queryset from Habit.objects with no filter(user=request.user).
No DEFAULT_PERMISSION_CLASSES is set anywhere, so DRF's default AllowAny applies.
Anyone, logged in or not, can read, edit or delete every user's habits and check-ins by ID.
2. Shared default@example.com user. perform_create assigns habits created without a login to this account, which hides the missing authentication.
Remove the fallback and require IsAuthenticated.
Filter the queryset by user=self.request.user, so other users' habits return 404.
Add tests that user A cannot see, edit, check in or delete user B's habits.

Important: 
3. Date handling.
is_checked_today takes a ?date= query parameter and silently ignores invalid values.
TIME_ZONE is hardcoded to Europe/Kyiv, so "today" is always Kyiv time. Users in other time zones will get wrong streaks.
Decide whether the client sends its local date, or the user has a timezone field.
4. Duplicate validation. Future dates are rejected in the model's clean, in HabitCheckInSerializer and in CheckInActionSerializer. Keep it in one place. Also, save() calls clean() on every save, which adds overhead and gets in the way of fixtures and bulk operations.
5. check is not race-safe. get_or_create relies on the unique constraint, but a concurrent insert raises IntegrityError, which isn't handled and would return a 500.
6. Performance. The list view prefetches every check-in for every habit just to compute streaks. That grows without bound.
Cache the streaks or limit the window.
The is_archived, -created_at index doesn't include user, which will be the main filter.
7. Registration.
It has no throttling.
8. It leaks which emails are already registered, through the "email exists" validation error.
The email isn't normalized to lowercase for uniqueness.
The JWT access token lasts 60 minutes with no refresh rotation or blacklist.
archive and unarchive as POST actions. This is acceptable, but is_archived is read-only in the serializer, so PATCH can't change it. That's fine as long as it's documented.
Production and deployment concerns
Production settings:
STATICFILES_STORAGE is deprecated in Django 5.1 and removed in 5.1+. Use STORAGES.
whitenoise, gunicorn and psycopg are only in production.txt, so the Docker and Render builds must install that file.
base.py sets ALLOWED_HOSTS default to ['*'].
base.py also has a hardcoded insecure SECRET_KEY default, with the .env.example value identical to it. It's guarded in production, but it's risky if DJANGO_SETTINGS_MODULE isn't set correctly.
Missing pieces:
CORS (django-cors-headers) is needed once the React frontend exists.
Pagination is on by default, which the React client must account for.
There is no .dockerignore or Dockerfile yet, as expected at this stage.
Linting: Nothing is configured: no ruff, black or CI. Add a GitHub Action that runs pytest.
Test dependencies: requirements/local.txt has factory-boy. Check that it's actually used.
Minor issues
Emoji validator: The regex is complicated and fragile. The hardcoded \U0001f468\U0001f469\U0001f467 alternative is a red flag, and the extra category check after the regex partly contradicts it. Consider the emoji package, or just limit the length.
Unused imports:
models.py and views.py import things they don't use or only need for the removed default-user logic (get_user_model).
HabitCheckInSerializer is used only for listing.
Per-request cache: _streaks_cache is stored on the model instance. It's fine, but it goes stale after a check-in unless the instance is refetched, so the view manually clears the prefetch cache. It would be cleaner to return the updated state from a service function.
Consistency: The code has no type hints in some places, and the docs and code are mixed. Keep language and docstrings consistent.



Щось забув, але додай CI/CD gitactions для автоматичного запуску тестів під час push і перевірку на lint
