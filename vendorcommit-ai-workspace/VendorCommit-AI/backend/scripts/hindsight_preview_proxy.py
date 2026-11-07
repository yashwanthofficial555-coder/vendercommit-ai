"""Friendly port-8888 preview for the internal Hindsight API on port 8889.

Run Hindsight with `hindsight-api --host 127.0.0.1 --port 8889`, then run:
`uvicorn scripts.hindsight_preview_proxy:app --host 0.0.0.0 --port 8888`.
VendorCommit continues using HINDSIGHT_API_URL=http://127.0.0.1:8888.
"""
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import Response

UPSTREAM = 'http://127.0.0.1:8889'
HOP_BY_HOP = {'connection', 'content-length', 'transfer-encoding', 'content-encoding', 'keep-alive', 'upgrade'}


@asynccontextmanager
async def lifespan(_):
    async with httpx.AsyncClient(timeout=120) as client:
        app.state.http = client
        yield


app = FastAPI(title='Hindsight Preview Gateway', docs_url=None, redoc_url=None, lifespan=lifespan)


@app.get('/', include_in_schema=False)
def root():
    return {'service': 'Hindsight Memory Server', 'status': 'running', 'health': '/health', 'documentation': '/docs', 'api': '/v1/default/banks'}


@app.api_route('/{path:path}', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'])
async def proxy(path: str, request: Request):
    headers = {key: value for key, value in request.headers.items() if key.lower() not in {'host', *HOP_BY_HOP}}
    response = await app.state.http.request(
        request.method,
        f'{UPSTREAM}/{path}',
        params=request.query_params,
        content=await request.body(),
        headers=headers,
    )
    response_headers = {key: value for key, value in response.headers.items() if key.lower() not in HOP_BY_HOP}
    return Response(content=response.content, status_code=response.status_code, headers=response_headers, media_type=response.headers.get('content-type'))
