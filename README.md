# Events Platform Backend

A Django REST Framework backend for managing users, events, and enrollments, with email verification, JWT authentication, role-based access, event discovery, and capacity-safe enrollment.

The project was built around the assignment requirements, with particular attention to database constraints, authorization, concurrency handling, and automated testing.

## Tech Stack

* Python
* Django 6.1
* Django REST Framework
* PostgreSQL
* SimpleJWT
* Django email console backend
* Git

## Features

### Authentication

* Signup using email, password, and role
* Uses Django's default `User` model
* Internal username is generated automatically
* Email verification using a 6-digit OTP
* OTP expiry and failed-attempt limit
* OTP resend cooldown
* Latest OTP invalidates the previous OTP
* Passwords are stored using Django's password hashing
* Unverified users cannot log in
* JWT access and refresh tokens
* JWT refresh endpoint

### Roles

The application supports two roles:

* **Seeker** — discover events, enroll, cancel enrollment, and view upcoming/past enrollments
* **Facilitator** — create, update, delete, and list their own events

Role and ownership checks are enforced on the backend.

### Events

Events contain:

* Title
* Description
* Language
* Location
* Start and end time
* Optional capacity
* Creator
* Created and updated timestamps

Facilitators can manage only their own events.

Facilitator event lists include active enrollment counts and available-seat counts.

### Event Discovery

Seekers can search and filter events using:

* `q` — searches title and description
* `location`
* `language`
* `starts_after`
* `starts_before`

List responses use DRF pagination:

```text
count
next
previous
results
```

Events are ordered with upcoming events first.

### Enrollments

Seekers can:

* Enroll in an event
* Cancel an enrollment
* Re-enroll after cancellation
* View upcoming enrollments
* View past enrollments

A canceled enrollment can be reused when the same seeker enrolls again, avoiding duplicate `(event, seeker)` records.

## API Endpoints

### Authentication

```text
POST /api/auth/signup/
POST /api/auth/verify-email/
POST /api/auth/login/
POST /api/auth/refresh/
```

### Facilitator

```text
GET    /api/facilitator/events/
POST   /api/facilitator/events/
GET    /api/facilitator/events/<id>/
PATCH  /api/facilitator/events/<id>/
DELETE /api/facilitator/events/<id>/
```

### Event Discovery and Enrollment

```text
GET  /api/events/
POST /api/events/<id>/enroll/
POST /api/events/<id>/cancel/
GET  /api/enrollments/?scope=upcoming
GET  /api/enrollments/?scope=past
```

Protected endpoints require:

```text
Authorization: Bearer <access-token>
```

## Architecture

The project is organized into three main areas:

```text
users/
    Authentication
    User profiles and roles
    OTP generation and verification
    Authentication-related API handling

events/
    Events
    Enrollments
    Role and ownership permissions
    Event discovery
    Capacity and concurrency handling

common/
    Pagination
    Consistent API error handling
```

The project keeps Django's default `User` model. Application-specific role information is stored in a related profile.

## Database

PostgreSQL is used as the primary database.

Migrations are included in:

```text
users/migrations/
events/migrations/
```

Indexes are included for commonly used event and enrollment queries.

The application reads the PostgreSQL password from the `POSTGRES_PASSWORD` environment variable and the Django secret key from `DJANGO_SECRET_KEY`.

No database password or production secret key is stored in the repository.

## Setup

### 1. Activate the virtual environment

Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Configure PostgreSQL

Create the PostgreSQL database used by the project and provide the database password through the environment.

Example:

```powershell
$env:POSTGRES_PASSWORD="your-password"
$env:DJANGO_SECRET_KEY="your-development-secret-key"
```

The PostgreSQL configuration uses:

```text
Host: localhost
Port: 5432
Database: events_platform
```

### 4. Apply migrations

```powershell
python manage.py migrate
```

### 5. Run the development server

```powershell
python manage.py runserver
```

The development email backend prints OTP messages to the terminal, so an external email provider is not required for local testing.

## Testing

Run the complete test suite with:

```powershell
python manage.py test
```

Additional verification commands:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
```

The final verification completed with:

```text
16 tests
16 passed
0 failed
```

The test suite covers authentication, JWT refresh, OTP expiry, failed-attempt limits, resend behaviour, role enforcement, event CRUD and ownership, discovery filters, pagination, enrollment, cancellation, re-enrollment, and the required concurrency scenario.

### Concurrency Test

The concurrency test covers the assignment scenario:

```text
Event capacity       = 10
Existing enrollments = 9
Concurrent seekers   = 5
Successful attempts  = 1
Rejected attempts    = 4
Final active count   = 10
```

Enrollment uses `transaction.atomic()` and locks the event row with `select_for_update()` before checking capacity and creating or reusing the enrollment.

## Error Responses

Handled API errors follow a consistent structure:

```json
{
    "detail": "message",
    "code": "error_code"
}
```

## Known Limitations & Future Improvements

The implementation is focused on the requirements of this assignment.

With additional development time, I would improve the project by:

* Adding OpenAPI/Swagger documentation for easier API exploration
* Adding more PostgreSQL integration tests around database constraints and concurrent behaviour
* Adding API-level rate limiting for authentication and OTP endpoints
* Adding Docker configuration to simplify setup across environments

These are outside the required assignment scope.

## Assignment Evidence

The main assignment requirements can be verified directly from the repository:

| Requirement                          | Where to verify                                |
| ------------------------------------ | ---------------------------------------------- |
| Authentication and OTP               | `users/`                                       |
| Events and enrollments               | `events/`                                      |
| Concurrency implementation           | `events/views.py`                              |
| Concurrency test                     | `events/test_event_suite.py`                   |
| Cancellation and re-enrollment       | `events/models.py`, `events/views.py`          |
| Re-enrollment test                   | `events/test_event_suite.py`                   |
| OTP expiry, lockout and resend tests | `users/tests.py`                               |
| Design decisions                     | `DECISIONS.md`                                 |
| Debugging issues and fixes           | `DEBUGGING.md`                                 |
| AI usage and corrections             | `PROMPT_LOG.md`                                |
| Database migrations                  | `users/migrations/`, `events/migrations/`      |
| Automated tests                      | `users/tests.py`, `events/test_event_suite.py` |

## Required Assignment Documents

The repository includes all four required documentation files:

* `README.md` — setup, architecture, API usage, testing, limitations, and future improvements
* `PROMPT_LOG.md` — material AI prompts, what was used or changed, corrections, and verification
* `DECISIONS.md` — non-trivial implementation decisions and trade-offs
* `DEBUGGING.md` — issues encountered, diagnosis, fixes, and verification

The repository also contains the required Django migrations and automated tests.

## Evaluation Notes

For a quick manual evaluation:

1. Start PostgreSQL and configure the database credentials.
2. Run the migrations.
3. Start the Django development server.
4. Create a Seeker or Facilitator account using the signup API.
5. Read the OTP from the development server console.
6. Verify the email.
7. Log in to obtain the JWT access token.
8. Use the access token to test the role-specific event and enrollment APIs.

The automated test suite can then be used to verify authentication, authorization, OTP edge cases, event lifecycle, re-enrollment behaviour, and the required concurrency scenario.
