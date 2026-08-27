# Architecture Decisions

## Default User and roles

The assignment requires Django's default `User`, but that model requires a username while signup accepts only email, password, and role. A custom user model or exposing username were rejected. The service generates an opaque username and stores product state in a one-to-one `Profile`. This preserves compatibility at the cost of an internal generated field.

## OTP resend policy

The ambiguity is whether OTP 1 remains valid after OTP 2 is sent. Keeping multiple hashes would require extra state and could permit an older code during the resend window. The selected policy is latest OTP wins: one `EmailOTP` row is overwritten, so OTP 1 becomes invalid immediately. A 30-second cooldown limits resend abuse. The trade-off is that a user who loses OTP 2 must wait for another resend.

## Enrollment concurrency

A count-then-insert approach has a TOCTOU race under concurrent requests. Database-only capacity checks would require a different counter design. The selected approach locks the event row with `select_for_update()` inside `transaction.atomic()` before counting active enrollments. This serializes enrollment decisions per event and is simple to reason about, at the cost of contention on a popular event.

## Cancellation and re-enrollment

The lifecycle could insert a new history row or reuse one row. The selected design keeps a unique `(event, seeker)` constraint and flips status between `ENROLLED` and `CANCELED`. This prevents duplicate active rows and makes capacity accounting straightforward, at the cost of not retaining every enrollment cycle as separate rows.