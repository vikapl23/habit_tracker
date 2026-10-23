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
