# Hindsight Cloud integration

VendorCommit uses the official `hindsight-client==1.2.0` Python SDK.

## Current integrated demo: Gemini-powered self-hosted Hindsight

The demo uses a separate Hindsight 1.2.0 server on port 8888, embedded PostgreSQL, Gemini for fact extraction, and Gemini embeddings. Install `requirements-hindsight.txt` in a separate virtual environment from the VendorCommit API, then start it with the documented `HINDSIGHT_API_*` variables from `.env.example`:

```bash
hindsight-api --host 0.0.0.0 --port 8888
```

Set VendorCommit's `HINDSIGHT_API_URL=http://127.0.0.1:8888`. A Hindsight Cloud API key is not needed for this self-hosted configuration.

For the hosted workspace preview, `scripts/hindsight_preview_proxy.py` provides a friendly `/` response on port 8888 while forwarding the API to Hindsight on internal port 8889. Run Hindsight on 8889 first, then start the gateway with `uvicorn scripts.hindsight_preview_proxy:app --host 0.0.0.0 --port 8888`. Normal local deployments can run Hindsight directly on 8888 without the gateway. The Gemini key is used only by the Hindsight server and must never be exposed to the browser.

## Enable Hindsight Cloud instead

Set these values in `backend/.env` (never in frontend environment files or source code):

```env
MEMORY_MODE=CLOUD
HINDSIGHT_API_URL=https://api.hindsight.vectorize.io
HINDSIGHT_API_KEY=your-server-side-key
HINDSIGHT_BANK_ID=vendorcommit-demo
MEMORY_MAX_RETRIES=3
MEMORY_RETRY_BACKOFF_SECONDS=0.5
```

Restart FastAPI after changing the configuration. Do not commit `.env` or share the key in screenshots, logs, the demo script, or browser code.

## Verify

```bash
curl http://localhost:8000/api/v1/memory/health?supplier_id=1
curl http://localhost:8000/api/v1/memory/status
```

A healthy cloud response includes `connected: true` and `status: connected`. The health check performs a real SDK recall against the supplier's isolated bank.

## Isolation and provenance

Each supplier uses a separate bank:

```text
{HINDSIGHT_BANK_ID}-supplier-{supplier_id}
```

For example, supplier 2 uses `vendorcommit-demo-supplier-2`. Retain uses the deterministic document ID `vendorcommit-memory-{local_id}` so retries do not intentionally create new document identities. Source interaction ID, category, title, and local memory ID are sent as metadata/tags.

## Honest fallback behavior

- Successful recall: `source=hindsight_cloud`, `cloud_retrieved=true`.
- Failed cloud recall: `source=local_database_fallback`, `cloud_retrieved=false`, with a visible warning.
- Failed retain: local source remains intact with `sync_status=failed`, retry count, and sanitized error provenance.
- Local mock: always `source=local_database`; no cloud or AI-generation claim.

Use `POST /api/v1/memory/{memory_id}/retry` to retry failed cloud retains.

## Existing local records

Changing to cloud mode does not erase local source records. Existing `local_only` records can be synchronized through the retry endpoint after switching to cloud mode. The UI exposes synchronized and failed counts. Before a judged demo, verify that Northstar and Vertex have synced records and that Memory Lab displays **Cloud recall** rather than a fallback warning.
