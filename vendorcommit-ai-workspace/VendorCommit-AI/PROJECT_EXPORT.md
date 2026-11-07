# Complete project workspace

The `vendorcommit-ai-workspace.zip` archive contains the full VendorCommit AI source project from the Git `main` branch.

## Included

- React/Vite frontend and all UI components
- FastAPI backend, SQLAlchemy models, and Alembic migrations
- Official Hindsight client integration and optional preview gateway
- Gemini-powered self-hosted Hindsight configuration examples
- Fictional, idempotent demo and QA data generators
- Automated tests and live acceptance checks
- Docker/backend configuration and dependency lockfiles
- Setup, hackathon demo, sample-data, and QA documentation
- Safe `.env.example` templates

## Intentionally excluded

- `.env` and API credentials
- Local SQLite/PostgreSQL/Hindsight database files
- `node_modules`, Python caches, build output, and tool caches
- Local Git metadata and machine-specific runtime state

These exclusions do not remove source functionality. Install dependencies, copy the environment templates, run migrations, and load the supplied fixtures to recreate the workspace safely.

## Restore and run

```bash
unzip vendorcommit-ai-workspace.zip
cd VendorCommit-AI

# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
# Set a strong JWT_SECRET. For the open local demo only, set:
# AUTH_REQUIRED=false and SEED_DEMO=true
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

In another terminal:

```bash
cd VendorCommit-AI
npm ci
npm run dev -- --host 0.0.0.0
```

To recreate all fictional sample records:

```bash
cd VendorCommit-AI/backend
source .venv/bin/activate
python scripts/seed_acceptance_data.py
```

For self-hosted Hindsight, install `requirements-hindsight.txt` in a separate virtual environment and follow `backend/HINDSIGHT_CLOUD_SETUP.md`. VendorCommit also supports explicitly labelled `LOCAL_MOCK` mode without Hindsight.

## Validate the restored workspace

```bash
cd VendorCommit-AI/backend
pytest
python scripts/verify_live.py  # while the API is running
cd ..
npm run build
```
