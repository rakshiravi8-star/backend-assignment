# Events Platform API

A Django REST API for an Events Platform with secure authentication, role-based access control, event discovery, and event enrollment.

The project focuses on the core requirements of the assignment: **correctness, security, database constraints, concurrency handling, OTP lifecycle management, and automated testing**.

---

## 1. Overview

The API supports two user roles:

* **Seeker** — discovers events, enrolls in events, cancels enrollments, and views upcoming/past enrollments.
* **Facilitator** — creates and manages their own events and can view enrollment and available-seat information.

The backend uses JWT authentication and email OTP verification before allowing users to log in.

The implementation also addresses the three engineering challenges specified in the assignment:

1. **Concurrent enrollment with event capacity**
2. **Cancellation and re-enrollment lifecycle**
3. **OTP resend and invalidation behaviour**

---

## 2. Technology Stack

* **Python**
* **Django**
* **Django REST Framework**
* **PostgreSQL**
* **SimpleJWT**
* **Django's default User model**
* **Git / GitHub**

Email delivery uses Django's development email backend as permitted by the assignment.

---

## 3. Architecture

The project follows a Django application structure with separate responsibilities for users, events, shared API behaviour, and project configuration.

```text
backend_assignment/
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── users/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── utils.py
│   ├── tests.py
│   └── migrations/
│
├── events/
│   ├── models.py
│   ├── serializers.py
│   ├── permissions.py
│   ├── views.py
│   ├── urls.py
│   ├── test_event_suite.py
│   └── migrations/
│
├── common/
│   ├── exceptions.py
│   └── pagination.py
│
├── manage.py
├── requirements.txt
├── PROMPT_LOG.md
├── DECISIONS.md
└── DEBUGGING.md
```

### Request flow

```text
Client
   │
   ▼
Django URL routing
   │
   ▼
DRF Views
   │
   ├── Authentication / JWT
   ├── Role & ownership checks
   ├── Input validation
   ├── Event / enrollment business rules
   │
   ▼
Serializers / Models
   │
   ▼
PostgreSQL
```

The application keeps authentication, authorization, validation, domain logic, persistence, pagination, and error handling separated across the relevant Django components.

---

# 4. Authentication

The authentication flow is based on:

**Signup → OTP verification → Login → JWT authentication**

### Signup

A user registers with:

* Email
* Password
* Role (`Seeker` or `Facilitator`)

A username is not required as signup input.

The newly created account remains unverified until the email OTP is successfully verified.

### OTP verification

A six-digit OTP is generated for email verification.

The OTP implementation includes:

* Expiry
* Failed-attempt limits
* Lockout behaviour
* Resend cooldown
* Previous OTP invalidation
* OTP invalidation after successful verification

OTP values are not returned in API responses.

### Login

Only verified users can log in.

Successful authentication returns JWT access and refresh tokens.

### Token refresh

The refresh endpoint allows a valid refresh token to obtain a new access token.

---

# 5. Role-Based Access Control

The backend enforces roles rather than relying on the client.

### Seeker

A seeker can:

* Discover events
* Search and filter events
* Enroll in events
* Cancel an enrollment
* Re-enroll after cancellation
* View upcoming enrollments
* View past enrollments

### Facilitator

A facilitator can:

* Create events
* View their own events
* Update their own events
* Partially update their own events
* Delete their own events
* View enrollment and available-seat information

Ownership is enforced on the backend, so a facilitator cannot manage another facilitator's event.

---

# 6. Events

An event contains the required domain information including:

* Title
* Description
* Language
* Location
* Start time
* End time
* Optional capacity
* Creator
* Timestamps

Event validation includes checks for required fields, valid values, time consistency, and capacity constraints.

Events can be discovered using search and filtering.

Supported discovery filters are:

* `q`
* `location`
* `language`
* `starts_after`
* `starts_before`

Results use pagination and upcoming-first ordering.

---

# 7. Enrollments

Seekers can enroll in available events.

The enrollment implementation handles:

* Successful enrollment
* Duplicate active enrollment
* Full-capacity events
* Events without a capacity limit
* Cancellation
* Re-enrollment
* Upcoming enrollments
* Past enrollments
* Available-seat calculation
* Active enrollment counts

The database/application design also supports the required cancellation → re-enrollment lifecycle without creating duplicate active enrollments.

---

# 8. Concurrency Handling

The assignment requires the following scenario to be handled safely:

```text
Event capacity       = 10
Existing enrollments = 9
Concurrent seekers   = 5
```

The backend uses transaction/locking/database logic to ensure that concurrent requests cannot cause the active enrollment count to exceed the event capacity.

The automated concurrency test verifies:

```text
5 concurrent enrollment attempts
        │
        ▼
Only 1 additional enrollment succeeds
        │
        ▼
Final active enrollments = 10
```

The remaining attempts are rejected because the event has reached capacity.

The concurrency strategy and trade-offs are documented separately in `DECISIONS.md`.

---

# 9. API Endpoints

## Authentication

| Method | Endpoint                | Purpose                          |
| ------ | ----------------------- | -------------------------------- |
| `POST` | `/api/auth/signup/`     | Register a seeker or facilitator |
| `POST` | `/api/auth/verify-otp/` | Verify email using OTP           |
| `POST` | `/api/auth/resend-otp/` | Request a new OTP                |
| `POST` | `/api/auth/login/`      | Login and obtain JWT tokens      |
| `POST` | `/api/auth/refresh/`    | Refresh the access token         |

## Events

| Method   | Endpoint            | Purpose                   |
| -------- | ------------------- | ------------------------- |
| `GET`    | `/api/events/`      | Discover/search events    |
| `POST`   | `/api/events/`      | Create an event           |
| `GET`    | `/api/events/<id>/` | Retrieve an event         |
| `PUT`    | `/api/events/<id>/` | Update an event           |
| `PATCH`  | `/api/events/<id>/` | Partially update an event |
| `DELETE` | `/api/events/<id>/` | Delete an event           |

## Facilitator

| Method | Endpoint                   | Purpose                                             |
| ------ | -------------------------- | --------------------------------------------------- |
| `GET`  | `/api/facilitator/events/` | List facilitator events with enrollment information |

## Enrollments

| Method | Endpoint                        | Purpose              |
| ------ | ------------------------------- | -------------------- |
| `GET`  | `/api/enrollments/`             | List enrollments     |
| `POST` | `/api/enrollments/`             | Enroll in an event   |
| `POST` | `/api/enrollments/<id>/cancel/` | Cancel an enrollment |

### Enrollment scope

The enrollment listing supports the tested scope behaviour:

```text
/api/enrollments/?scope=upcoming
```

and the corresponding past-enrollment behaviour.

### Authentication header

Protected endpoints use JWT authentication:

```http
Authorization: Bearer <access_token>
```

---

# 10. Pagination

Paginated API responses follow the required DRF structure:

```json
{
    "count": 0,
    "next": null,
    "previous": null,
    "results": []
}
```

The implementation uses:

* `count`
* `next`
* `previous`
* `results`

Pagination behaviour is covered by the automated test suite.

---

# 11. Error Handling

The API uses a consistent error structure where applicable:

```json
{
    "detail": "Error description",
    "code": "error_code"
}
```

The test suite verifies relevant validation, authentication, authorization, and not-found responses.

The API avoids exposing unnecessary internal database information through standardized error responses.

---

# 12. Database Design

The project uses PostgreSQL with Django migrations.

The main domain entities are:

```text
User
 │
 ├── Seeker / Facilitator role
 │
 └── OTP verification data

Facilitator
     │
     └── Event
            │
            └── Enrollment
                   │
                   └── Seeker
```

Database migrations include the required schema and indexes for the main event/enrollment queries.

The enrollment design also preserves the required active-enrollment uniqueness while allowing cancellation followed by re-enrollment.

---

# 13. Automated Testing

Automated tests cover the major functional, security, and constraint-related behaviours of the application.

The verified final test run completed successfully:

```text
Ran 16 tests in 156.800s

OK
```

### Final verified result

| Result           |  Count |
| ---------------- | -----: |
| Tests discovered | **16** |
| Passed           | **16** |
| Failed           |  **0** |
| Errors           |  **0** |
| Skipped          |  **0** |

The test suite includes coverage for:

### Authentication

* User signup
* Seeker/facilitator roles
* Email verification
* Unverified login rejection
* Valid login
* Invalid credentials
* JWT refresh

### OTP

* OTP verification
* OTP expiry
* Failed attempts
* Lockout
* Resend cooldown
* Resend invalidation
* Latest-OTP-wins behaviour
* OTP not returned in API responses
* OTP lifecycle after successful verification

### Events

* Event creation
* Event retrieval
* Event update
* Event deletion
* Event ownership
* Event discovery
* Search and filters
* Pagination
* Validation

### Enrollment

* Successful enrollment
* Capacity enforcement
* Duplicate active enrollment
* Cancellation
* Re-enrollment
* Upcoming/past enrollment behaviour
* Enrollment counts
* Available seats

### Concurrency

The exact assignment scenario is tested:

```text
Capacity = 10
Existing active enrollments = 9
Concurrent enrollment attempts = 5

Expected:
1 succeeds
4 are rejected
Final active count = 10
```

### Error and authorization behaviour

The suite also covers authentication and authorization boundaries and standardized error responses.

---

# 14. Engineering Challenges

## Challenge A — Concurrent Enrollment

The implementation protects the event capacity at the backend/database level rather than relying on the client.

The concurrency test demonstrates that five simultaneous enrollment requests cannot push the active enrollment count beyond the configured capacity.

## Challenge B — Cancellation and Re-enrollment

An enrollment can move from active to canceled and subsequently be reused for re-enrollment.

This avoids creating multiple active enrollment records for the same seeker and event while still supporting the required lifecycle.

## Challenge C — OTP Resend

The implementation follows a **latest OTP wins** policy.

When a new OTP is issued, the previous OTP is no longer accepted.

The API-level test verifies:

```text
OTP 1 requested
      ↓
OTP 2 requested
      ↓
OTP 1 rejected
      ↓
OTP 2 accepted
```

Neither OTP is exposed in the API response.

---

# 15. Running the Project

## Prerequisites

* Python 3.x
* PostgreSQL
* Git

## 1. Clone the repository

```bash
git clone <repository-url>
cd backend_assignment
```

## 2. Create and activate the virtual environment

### Windows PowerShell

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

## 3. Install dependencies

```powershell
pip install -r requirements.txt
```

## 4. Configure PostgreSQL

Create a PostgreSQL database named:

```text
events_platform
```

Configure the PostgreSQL password through the environment variable:

```powershell
$env:POSTGRES_PASSWORD="your-postgres-password"
```

The project reads the PostgreSQL password from the environment rather than storing the credential directly in the repository.

## 5. Apply migrations

```powershell
.\venv\Scripts\python.exe manage.py migrate
```

## 6. Run Django checks

```powershell
.\venv\Scripts\python.exe manage.py check
```

## 7. Run the automated tests

```powershell
.\venv\Scripts\python.exe manage.py test -v 2
```

Expected verified result for the submitted implementation:

```text
Ran 16 tests in 156.800s

OK
```

---

# 16. Evaluation Convenience

The repository includes:

* Django migrations
* Automated tests
* `PROMPT_LOG.md`
* `DECISIONS.md`
* `DEBUGGING.md`
* `README.md`

The assignment's required concurrency, re-enrollment, and OTP scenarios are represented in the automated test suite, allowing the core behaviour to be evaluated without requiring a separate Postman collection.

A Postman collection was therefore not required for the submission because the assignment explicitly states that API examples are optional when the tests and README are strong.

---

# 17. Documentation

### `PROMPT_LOG.md`

Records material AI-assisted development work, including prompts, what was used, what was changed or rejected, and verification.

It also documents cases where AI output required correction.

### `DECISIONS.md`

Documents the important engineering decisions and their trade-offs, including the concurrency, enrollment lifecycle, and OTP behaviour.

### `DEBUGGING.md`

Documents real implementation/debugging issues, including the symptom, diagnosis, root cause, fix, and verification.

---

# 18. What I Would Improve With Another Day

If I had another 24 hours, I would focus on improvements that build on the existing backend rather than expanding the scope unnecessarily:

1. **Increase automated test coverage further** around additional edge cases and failure paths.
2. **Improve API documentation** with more complete request/response examples for each endpoint.
3. **Add more evaluation-friendly sample data/setup** so the main flows can be demonstrated quickly.
4. **Perform additional security and concurrency testing** under a wider range of request patterns.
5. **Improve deployment readiness** with additional environment and operational configuration.

The priority would remain correctness, security, reliability, and maintainability rather than adding unrelated features.

---

# 19. Project Status

The submitted implementation has been verified with PostgreSQL and the complete test suite.

```text
Django checks          PASS
Migration check        PASS
PostgreSQL migration   PASS
Automated tests        16 / 16 PASS
Concurrency challenge  PASS
Re-enrollment          PASS
OTP resend challenge   PASS
Git working tree       CLEAN
```

The project is structured around the assignment's core requirements and keeps the implementation focused on a compact, testable Django REST backend.

