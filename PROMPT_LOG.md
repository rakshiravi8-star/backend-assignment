 # AI Prompt Log

## Initial implementation review

- **Tool/model:** GitHub Copilot in VS Code.
- **Prompt:** Integrate the supplied Django REST vertical slice into the existing project, preserving the default User model and PostgreSQL, then run checks, migrations, tests, and an API smoke test.
- **Used:** Auth, OTP, roles, events, enrollment, documentation, and migrations were integrated and tested.
- **Changed/rejected:** Supplied code was treated as unverified and adapted to the actual starter repository and installed Django version.
- **Verification:** Django checks, migration checks, PostgreSQL migrations, automated tests, and live HTTP requests.

## Final audit prompt

- **Tool/model:** GitHub Copilot in VS Code.
- **Prompt:** Audit every assignment requirement line by line, repair missing evidence or implementation, and run the complete unlabelled test suite.
- **Used:** Added query indexes, model validation, locked cancellation, expanded tests, and corrected documentation.
- **Changed/rejected:** The original small concurrency test was rejected and replaced with the required capacity-10, nine-existing, five-contender scenario.
- **Verification:** Full test discovery and targeted tests are rerun after changes.

## What AI got wrong / what I corrected

1. The supplied code used Django 5-era `CheckConstraint(check=...)`; installed Django 6.1 requires `condition=...`. The model was corrected and migrations regenerated.
2. Invalid OTP attempts were saved and then rolled back because an exception was raised inside `transaction.atomic()`. The response now returns after persisting the increment, and lockout tests verify persistence.
3. Event tests were initially omitted by full discovery because both apps had top-level `tests.py` modules. The event suite was moved to `test_event_suite.py` and imported into the discovered users test module.
