# Fictional QA sample data and acceptance checks

All records prefixed **QA** are fictional fixtures, not real suppliers, transactions, or verified business events. Loading is non-destructive and idempotent: rerunning does not duplicate records or reset user data.

## Load the sample data

```bash
cd backend
python scripts/seed_acceptance_data.py
```

When `SEED_DEMO=true`, application startup also loads these fixtures after the base demo users and hackathon story exist.

## Included coverage

| Area | Fictional examples |
|---|---|
| Supplier statuses | QA Atlas Packaging: active; QA Beacon Electronics: onboarding; QA Cobalt Textiles: suspended; QA Delta Freight: inactive |
| Commitment types | Price, delivery, quantity, quality, and SLA |
| Commitment states | Pending, fulfilled, overdue, and breached |
| Calculations | Positive savings, negative savings/cost increase, reliability, delivery score, risk, and active totals |
| Verification | One independently verified record and one reviewer-created target for live verification |
| Interactions | Call, email, meeting, delivery, note, and negotiation |
| Memory | Pricing, negotiation, preference, and risk evidence with source interaction IDs |
| Failure recovery | `QA-RETRY-RECOVERY`, explicitly labelled as a simulated failure |
| Performance | Initial database-derived snapshots for every QA supplier |

The live checker additionally creates one persistent **QA live automatic-learning check** interaction and its linked source memory. Temporary CRUD records are prefixed `QA-LIVE-CRUD` and only those temporary records are removed after the check.

## Run live acceptance checks

Start the API and, for cloud mode, Hindsight first. Then run:

```bash
cd backend
python scripts/verify_live.py
```

The checker covers supplier/commitment CRUD, filters, validation errors, duplicate handling, missing-record handling, calculated fields, performance history, Hindsight synchronization, supplier-scoped recall, automatic interaction learning, independent verification, self-verification rejection, and dashboard totals. It is safe to rerun.

For an authenticated deployment:

```bash
DEMO_ADMIN_EMAIL=admin@example.com \
DEMO_ADMIN_PASSWORD='your-local-password' \
python scripts/verify_live.py
```

To point at another API:

```bash
VENDORCOMMIT_API_URL=http://127.0.0.1:8000 python scripts/verify_live.py
```

## Repeat the failure/retry demonstration

This resets **only the labelled QA retry fixture** to a simulated failed state:

```bash
cd backend
python scripts/seed_acceptance_data.py --simulate-failure
python scripts/verify_live.py
```

In cloud mode the verifier retries it and confirms Hindsight synchronization. In local mock mode, the unit tests verify that cloud retry is honestly rejected and cloud outages produce an explicit local fallback.

## Full offline regression suite

```bash
cd backend
pytest
npm --prefix .. run build
```

The automated suite additionally covers authentication/RBAC, cloud failures, retries, local fallback, provenance, decision comparisons, and fixture idempotency without calling external services.
