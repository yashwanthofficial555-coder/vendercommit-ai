# VendorCommit AI

Supplier Commitment Intelligence with a visible Hindsight memory advantage.

- React 18, Vite, Tailwind CSS, Lucide, Recharts
- FastAPI, Pydantic v2, SQLAlchemy, Alembic
- SQLite for local demo; PostgreSQL migration support
- Supplier-isolated local/cloud memory modes
- Database-backed dashboard and rule-based decision support

## Run the demo

The workspace preview starts Vite on port 5173 and FastAPI on port 8000. For local development:

```bash
# API
cd backend
pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend, from the repository root
npm install
npm run dev
```

For the open local hackathon demo, set `SEED_DEMO=true` and `AUTH_REQUIRED=false` in `backend/.env`. Production rejects disabled authentication.

## Validation

```bash
cd backend && pytest
npm run build
```

See [SAMPLE_DATA.md](./SAMPLE_DATA.md) for the fictional all-state QA dataset and repeatable live acceptance checks. See [HACKATHON_DEMO.md](./HACKATHON_DEMO.md) for the four-minute judge walkthrough, pitch, and criteria alignment. See `backend/README.md` for deployment and architecture details.
