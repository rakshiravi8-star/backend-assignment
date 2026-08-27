# Debugging Log

## Django 6.1 check constraint API

The supplied implementation used `CheckConstraint(check=...)`, but the installed Django 6.1 API requires `condition=...`. The event model was corrected and migrations were generated from the installed version.

## OTP attempt rollback

Initially, invalid OTP handling saved `failed_attempts` and then raised an exception inside the surrounding transaction. The exception rolled back the increment, preventing lockout. Invalid-code responses now return after the increment is saved, while lockout and expiry errors remain normalized through the global exception handler.

## Email backend

The starter settings used `MAILERS`, which Django does not read for `send_mail()`. It was replaced with `EMAIL_BACKEND` and `DEFAULT_FROM_EMAIL` so local OTP delivery uses the console backend.