import time
from collections import defaultdict, deque
from fastapi import HTTPException, Request
from .config import settings

_hits: dict[str, deque] = defaultdict(deque)

def rate_limit(request: Request):
    now = time.time()
    ip = request.client.host if request.client else "unknown"
    q = _hits[ip]
    while q and q[0] < now - 60:
        q.popleft()
    if len(q) >= settings.RATE_LIMIT_PER_MINUTE:
        raise HTTPException(429, "Too many requests. Try again in a minute.")
    q.append(now)