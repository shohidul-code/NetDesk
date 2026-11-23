# Phase 2 — Database and domain API: viva notes

## What was built and why

- Eight tables via Alembic: `0001_core` (roles, users, areas, packages, connections, bills, complaints, area_notices) and `0002_payment_trail` (payment method, unique TrxID, verifier, paid ⇔ paid_at). Two migrations show the schema evolving on a table with rows.
- Lookup tables use `int` ids; everything else `uuid`, so customers cannot guess other customers' ids.
- Rules live in the database too: CHECK constraints for every enum value, the billing period format, money ≥ 0, a notice ending after it starts, and one bill per connection per month.
- Every module has the same layers: controllers (HTTP only), services (rules + `commit`), repositories (SQL only, always given the caller's `Scope`).
- A stub `get_current_user` (first active admin) and `require_roles` sit on every route now, so Phase 3 replaces one function instead of retrofitting checks.
- Endpoints: areas, package CRUD, connection CRUD with filters/search/sort/pages, idempotent bill generation, TrxID payment verification, dues summary, complaints with a status machine and the `ALLOW_CUSTOMER_COMPLAINTS` flag, area notices.
- An idempotent synthetic seed: running it twice changes nothing; demo passwords are Argon2id hashes.
- Tests run in a rolled-back transaction per test; the app's commits become SAVEPOINTs, so tests never see each other's rows.
- Found and fixed: the route-auth rubric test was passing without checking anything (FastAPI 0.163 nests included routers).

## Five locations to explain

- `app/modules/auth/dependencies.py:23`: the stub `get_current_user`. Every route depends on it (directly or via `require_roles`/`get_scope`), so Phase 3 swaps only this function for JWT checks.
- `app/modules/billing/repositories.py:52`: `ON CONFLICT (connection_id, period) DO NOTHING`. The unique constraint makes generating a month twice safe, even if two admins click at once.
- `app/modules/billing/repositories.py:85`: `SELECT ... FOR UPDATE` locks the bill while a payment is verified, so two payments for one bill cannot both succeed.
- `app/modules/complaints/services.py:17`: `ALLOWED_TRANSITIONS`. A complaint can only move open → in_progress → resolved → closed, or reopen from resolved; anything else is a 409 state conflict.
- `tests/conftest.py:45`: `join_transaction_mode="create_savepoint"`. The service's `commit()` only releases a SAVEPOINT inside the test's outer transaction, which is rolled back at the end.

## Likely viva questions

1. **Why does an out-of-scope id return 404 and not 403?** A 403 would confirm the id exists. 404 for "not yours" means nobody can probe which connections exist; 403 is only for actions a role may never do, like a customer creating a package.
2. **How is bill generation idempotent?** The database has `unique(connection_id, period)`, and the insert uses `ON CONFLICT DO NOTHING ... RETURNING id`. The second run inserts nothing, and the returned ids give the created count.
3. **How do you stop a TrxID being reused?** A partial unique index on `trx_id` where it is not null, a pre-check that gives a clear 409, and a catch of the database's IntegrityError for the race the pre-check cannot see.
4. **Why are search terms escaped?** `q` goes into `ILIKE '%q%'`. Without escaping, `%` or `_` in the input act as wildcards; the query itself is always parameterised, so SQL injection is impossible either way, and a test proves `%' OR 1=1 --` returns nothing.
5. **Why are the roles inserted by a migration and not the seed?** The app cannot work without them, and tests build the schema with `alembic upgrade head` only; data the code depends on belongs with the schema.

## Rubric rows this phase moves (PROPOSAL §4)

- **B2 Structure:** module layout with controllers, services, repositories, schemas, models; the `Depends` chain.
- **B3 Database:** async SQLAlchemy 2, Alembic migrations with working downgrades, `alembic check` in tests, idempotent seed. (Twelve tables complete after Phases 4–5.)
- **B4 Domain API:** connection and package CRUD with filters, search and limit/offset pages with a total.
- **B5 Errors:** 201, 204, 403, 404, 409 and 422 now have tests on real routes.
- **E3 Roles & realistic data:** three roles and a seeded synthetic ISP.
