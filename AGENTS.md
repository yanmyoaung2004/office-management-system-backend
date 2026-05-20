# School Office Management System — Backend

Stack: Django 6.0.5, DRF 3.17+, Python 3.13, SQLite, JWT (simplejwt), Waitress.

## Commands

```bash
# Dev server
python manage.py runserver

# Migrations
python manage.py makemigrations
python manage.py migrate

# Seed data (creates users: yma/admission/finance/exam, all password=password)
python manage.py seed_data

# After enabling DEBUG fast hasher, re-hash existing passwords:
python manage.py fast_password yma admission finance exam

# Production
waitress-serve --port=8000 config.wsgi:application
docker compose up --build
```

## Architecture

- **Settings**: `config/settings.py` — `DJANGO_SECRET_KEY`, `DEBUG` env vars. SQLite at `db.db`.
- **URL root**: `config/urls.py` → `api/` → `core/urls.py` → sub-routers: `admission/`, `finance/`, `exam/`.
- **Custom User model**: `core.User` (`AUTH_USER_MODEL`), FK to `Role`. All endpoints except `/api/auth/login` require JWT.
- **ID scheme**: Custom prefixed sequential IDs (`U001`, `STU001`, `MAJ001`) via `generate_id()`.
- **Response format**: `{success, data, message}` on success, `{success, error, code}` on error. Paginated lists include `{pagination: {page, limit, total, totalPages}}`.
- **RBAC**: `Role` + `RolePermission` (module/action pairs). `seed_data.py` wires Django `auth.Permission` to roles.
- **API sub-packages** under `core/api/` (`admission/`, `finance/`, `exam/`) — each has own `urls.py`, `views.py`, `serializers.py`.

## Gotchas

- **DB in OneDrive** = slow. Default path is `backend/db.db`.
- **DEBUG fast hasher**: `core/hashers.FastPBKDF2PasswordHasher` (2000 iterations). Enabled when `DEBUG=True`. After enabling, run `fast_password` to re-hash existing passwords — login drops from ~1.5s to ~50ms.
- **N+1 queries**: Many views use `.only()` — add `.select_related()`/`.prefetch_related()` when adding nested data.
- **django-q** commented out in INSTALLED_APPS (Django 6.x compat). Daily task logic in `core/tasks.py`.
- **Seeded user passwords**: All default to `password` (see `seed_data.py`).
- **Orphan scripts**: `genetic.py`, `util.py`, `util1.py` are standalone timetable algorithms (not part of Django app).
- **`models.test.py`** is a draft — real models are in `models.py`.
- **No test framework detected** — no tests exist yet.
