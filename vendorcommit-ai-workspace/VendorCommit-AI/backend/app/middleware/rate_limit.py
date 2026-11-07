import time
from collections import defaultdict, deque
from threading import Lock
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Small in-memory limiter suitable for one process. Use Redis for multi-worker deployments."""
    def __init__(self, app, requests: int = 120, window_seconds: int = 60):
        super().__init__(app)
        self.requests = requests
        self.window = window_seconds
        self.clients = defaultdict(deque)
        self.lock = Lock()

    async def dispatch(self, request, call_next):
        if request.url.path in {'/health', '/docs', '/openapi.json'}:
            return await call_next(request)
        key = request.client.host if request.client else 'unknown'
        now = time.monotonic()
        with self.lock:
            bucket = self.clients[key]
            while bucket and bucket[0] <= now - self.window:
                bucket.popleft()
            if len(bucket) >= self.requests:
                return JSONResponse(status_code=429, content={'detail': 'Rate limit exceeded'}, headers={'Retry-After': str(self.window)})
            bucket.append(now)
        response = await call_next(request)
        response.headers['X-RateLimit-Limit'] = str(self.requests)
        return response
