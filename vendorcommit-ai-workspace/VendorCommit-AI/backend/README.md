# VendorCommit AI API

Secure FastAPI backend for supplier commitment intelligence. SQLite is the default; PostgreSQL is supported through SQLAlchemy and Alembic.

## Run locally

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
# Set a unique JWT_SECRET in .env
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API documentation: `http://localhost:8000/docs`. Health check: `/health`.

The frontend runs separately with `npm run dev`; Vite proxies `/api` to port 8000. Set `VITE_API_URL` when the API is hosted on another origin. For a completely open local demo only, set `AUTH_REQUIRED=false`; the application will use the seeded local administrator without a login screen. This setting is rejected in production.

## Demo data

Demo records are disabled by default. Set `SEED_DEMO=true` only for local evaluation. This creates:

- `admin@example.com`
- `reviewer@example.com`
- `viewer@example.com`

The local demo password is `VendorCommit2026!`. Disable seeding and change/remove demo users before deployment.

## Roles

- `viewer`: read operational records and analytics.
- `procurement`: create/update suppliers, commitments, interactions, and memories; independently verify commitments.
- `admin`: all procurement permissions plus delete operations, user management, and audit log access.

A commitment creator cannot verify their own commitment. Any substantive commitment update clears verification.

## Database and migrations

```bash
alembic upgrade head                 # apply non-destructive migrations
alembic revision --autogenerate -m "describe change"
alembic check                        # compare models with migration head
pytest --cov=app                     # complete test suite
```

Back up the database before migrations. The initial migration only creates tables and indexes. No migration drops existing business records. For PostgreSQL:

```env
DATABASE_URL=postgresql+psycopg://vendorcommit:strong-password@db:5432/vendorcommit
```

Run Alembic against the target database before starting multiple API workers. Use managed PostgreSQL backups in production.

## Hindsight memory

`MEMORY_MODE=LOCAL_MOCK` stores source records locally and performs deterministic supplier-isolated text recall. Responses explicitly report `ai_generated: false` and `cloud_retrieved: false`; local mock results are not represented as AI output.

`MEMORY_MODE=CLOUD` enables the pinned official `hindsight-client==1.2.0` adapter and requires `HINDSIGHT_API_URL`, `HINDSIGHT_API_KEY`, and `HINDSIGHT_BANK_ID`. Each supplier receives an isolated bank named `{HINDSIGHT_BANK_ID}-supplier-{id}`. Retain uses deterministic document IDs, retries with exponential backoff, and persists failure status, retry count, and error provenance. Cloud recall reports `source=hindsight_cloud`; failures explicitly fall back to local source records with a warning. Failed retains can be retried through `/api/v1/memory/{id}/retry`. Verify connectivity with `/api/v1/memory/health?supplier_id=1`.

## Production deployment

1. Set `APP_ENV=production`, a random 32+ character `JWT_SECRET`, `SEED_DEMO=false`, and explicit HTTPS `CORS_ORIGINS`.
2. Use PostgreSQL and run `alembic upgrade head` as a controlled release step.
3. Install and configure the Hindsight SDK for cloud memory.
4. Deploy behind TLS and a trusted reverse proxy. Configure request body limits and proxy client-IP handling.
5. Replace the single-process in-memory rate limiter with Redis when running multiple workers.
6. Store secrets in a secret manager; never commit `.env` or database files.
7. Add centralized log shipping, metrics, backups, and token revocation/session management appropriate to your compliance requirements.

Docker:

```bash
docker build -t vendorcommit-api ./backend
docker run --env-file backend/.env -p 8000:8000 vendorcommit-api
```

## Security notes

Argon2 password hashing, signed short-lived JWTs, role checks, ORM-bound queries, Pydantic v2 validation, constrained pagination/sorting, CORS allowlists, audit events, foreign keys, and generic 500 responses are enabled. The generic error handler logs details server-side without returning stack traces to clients.
