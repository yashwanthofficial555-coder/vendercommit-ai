import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .config import get_settings
from .database import Base, SessionLocal, engine
from .middleware.rate_limit import RateLimitMiddleware
from .routes import audit, auth, commitments, dashboard, interactions, memory, suppliers
from .seed import seed_demo, seed_hackathon_story
from .acceptance_fixtures import seed_acceptance_story

settings = get_settings()
settings.validate_security()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('vendorcommit')

@asynccontextmanager
async def lifespan(_):
    # Non-destructive development convenience. Production deployments run `alembic upgrade head`.
    Base.metadata.create_all(bind=engine)
    if settings.seed_demo:
        with SessionLocal() as db:
            seed_demo(db)
            seed_hackathon_story(db)
            seed_acceptance_story(db)
    yield

app = FastAPI(title='VendorCommit AI API', version='1.0.0', description='Supplier Commitment Intelligence with independently verifiable records and database-backed analytics.', lifespan=lifespan)
app.add_middleware(RateLimitMiddleware, requests=settings.rate_limit_requests, window_seconds=settings.rate_limit_window_seconds)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=['GET','POST','PATCH','PUT','DELETE','OPTIONS'], allow_headers=['Authorization','Content-Type'])

@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError):
    errors = json.loads(json.dumps(exc.errors(), default=str))
    return JSONResponse(status_code=422, content={'detail': 'Validation failed', 'errors': errors})

@app.exception_handler(Exception)
async def safe_error_handler(request: Request, exc: Exception):
    logger.exception('Unhandled error on %s', request.url.path, exc_info=exc)
    return JSONResponse(status_code=500, content={'detail': 'An internal error occurred'})

@app.get('/', include_in_schema=False)
def root():
    return {'service': 'VendorCommit AI API', 'status': 'running', 'health': '/health', 'documentation': '/docs', 'api_prefix': settings.api_prefix}

@app.get('/health', tags=['System'])
def health(): return {'status': 'ok', 'service': 'vendorcommit-api'}

for route in [auth, suppliers, commitments, interactions, dashboard, memory, audit]:
    app.include_router(route.router, prefix=settings.api_prefix)
