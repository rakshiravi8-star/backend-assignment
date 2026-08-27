# Events Platform Backend

Django REST Framework backend for email-verified users, role-based event management, and capacity-safe enrollment.

## Setup

Use the existing virtual environment on Windows:

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

The project uses the configured PostgreSQL database `events_platform` on `localhost:5432`. The development email backend prints OTP messages to the console.

Set `POSTGRES_PASSWORD` and, outside local development, `DJANGO_SECRET_KEY` in the environment before running the server or management commands. Secrets are not stored in the repository.

The repository uses Django's default `User` model; signup generates its internal username. Use `Authorization: Bearer <access-token>` for protected endpoints.

## API

- `POST /api/auth/signup/`, `POST /api/auth/verify-email/`, `POST /api/auth/login/`, `POST /api/auth/refresh/`
- `GET/POST /api/facilitator/events/`
- `GET/PATCH/DELETE /api/facilitator/events/<id>/`
- `GET /api/events/?q=&location=&language=&starts_after=&starts_before=`
- `POST /api/events/<id>/enroll/` and `/cancel/`
- `GET /api/enrollments/?scope=upcoming|past`

Facilitator event lists include active enrollment and available-seat counts; unlimited capacity returns `available_seats: null`. Enrollments reuse the same row after cancellation. List responses use DRF's `count`, `next`, `previous`, and `results` shape, and handled API errors use `detail` plus `code`.

Authenticated API errors use `{ "detail": "...", "code": "..." }`; list endpoints use DRF pagination.

## Verification

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

The concurrency test uses PostgreSQL transactions and locks the event row before counting active enrollments.

## Evaluation

The suite covers auth, JWT refresh, OTP expiry/lockout/resend, role enforcement, CRUD ownership, discovery filters and pagination, enrollment scopes, and a PostgreSQL concurrency scenario with capacity 10, nine existing active enrollments, and five simultaneous contenders. For manual evaluation, sign up with role `FACILITATOR` or `SEEKER`, read the OTP from the runserver console, verify, log in, and use the returned access token.

## Architecture and limitations

`users` owns profiles, OTPs, and authentication; `events` owns events and enrollments; `common` owns pagination and normalized errors. There is no password reset, network-level rate limiter, facilitator roster endpoint, or soft delete; these are reasonable next-day improvements.