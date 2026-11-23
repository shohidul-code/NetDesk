# Phase 3 — Authentication and authorization: viva notes

## What was built and why

- `POST /auth/login` with the OAuth2 password form, so Swagger's **Authorize** button works. It returns a 30-minute HS256 JWT that holds only `sub` (user id) and `exp`.
- `get_current_user` now verifies the token and loads the user and role from the database on every request. Missing, forged, expired, unknown-user or inactive tokens all get 401 with `WWW-Authenticate: Bearer`.
- Login gives the same 401 body for an unknown email and a wrong password, and runs a dummy Argon2 check for unknown emails so timing does not reveal which accounts exist.
- `POST /auth/register` is claim-style: a customer proves they own a connection by its code and phone; the row is locked so two people cannot claim it at once.
- Admin user endpoints: create technicians, list by role, activate/deactivate; the last active admin cannot be deactivated.
- Rate limits: login 5/min and register 3/min per client IP, returning the 429 envelope with `Retry-After`. The IP is real behind Render because uvicorn trusts the proxy's `X-Forwarded-For`.
- An access sweep with real tokens: every write route rejects customers (except creating complaints) and technicians (except updating complaints); every non-public route rejects a missing token; IDOR tests prove another customer's data returns 404.
- `smoke.sh` now logs in and calls `/auth/me`; CI seeds demo data first.

## Five locations to explain

- `app/core/security.py:24`: `DUMMY_HASH`. An unknown email still costs one Argon2 check, so response time does not leak whether the account exists.
- `app/core/security.py:52`: `algorithms=[ALGORITHM]`. Fixing the allowed algorithm stops a forged token that claims `alg: none` or switches algorithms.
- `app/modules/auth/dependencies.py:28`: `get_current_user`. The token only names the user; role and `is_active` come from the database each time, so deactivation and role changes apply immediately (tested).
- `app/modules/users/repositories.py:41`: `with_for_update()` on the claim lookup locks the connection row until the transaction ends, so two simultaneous registrations cannot both claim it.
- `app/core/rate_limit.py:10`: the limiter keys on `request.client.host`. In memory, one instance: limits reset on restart, a limit PROPOSAL §10.4 states openly.

## Likely viva questions

1. **Why not put the role in the JWT?** A token cannot be taken back. If the role were inside it, a demoted or deactivated user would keep their old powers for up to 30 minutes. Loading the role from the database costs one indexed query and makes changes immediate.
2. **How do you prevent user enumeration at login?** Same 401 message and body for both failures, plus a dummy hash check so both paths take about the same time. Registration still returns 409 for a taken email, which the rubric asks for; it is rate-limited to 3/min per IP to slow down probing.
3. **What is IDOR and how is it tested?** Insecure Direct Object Reference: changing an id in the URL to reach someone else's record. Repositories filter by the caller's Scope, and `tests/test_access_sweep.py` proves another customer's connection, bills, complaints and notices are invisible, with the same 404 body as a random id.
4. **Why does a customer get 403 before a 422 on a write route?** `require_roles` runs as a dependency before the body is used, so a forbidden role never learns anything about validation. The sweep sends an empty body to every write route and expects 403.
5. **What does the rate limiter not protect against?** A distributed attack from many IPs, and limits reset on restart or across instances. The answer for production is a shared store (Redis), deliberately out of scope here.

## Rubric rows this phase moves (PROPOSAL §4)

- **B10 Auth:** register (claim), login, `/auth/me`, Argon2id, 30-minute JWT, roles table, admin-only domain writes, identical login error. Done and tested.
- **B5 Errors:** 401 and 429 now have tests on real routes.
- **Security matrix rows** for brute force, user enumeration, broken access control and IDOR (PROPOSAL §10.2).
