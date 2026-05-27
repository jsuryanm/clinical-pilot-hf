"""Audit middleware — every state-mutating request gets a row in audit_log.

Owner: Person C. Read-only GET/HEAD requests are skipped to keep the table lean.
"""

from __future__ import annotations

import time
import uuid
from typing import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

log = structlog.get_logger(__name__)

_READONLY = {"GET", "HEAD", "OPTIONS"}


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        rid = uuid.uuid4().hex[:12]
        t0 = time.perf_counter()
        request.state.request_id = rid

        response = await call_next(request)

        if request.method not in _READONLY:
            dt_ms = round((time.perf_counter() - t0) * 1000, 1)
            actor = request.headers.get("X-API-Key", "anonymous")[:8]
            log.info(
                "audit",
                rid=rid,
                actor=actor,
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                ms=dt_ms,
            )
            # TODO(Person C): persist to AuditLog table — opening a session
            # in middleware needs a bit of care; do it on Day 10.
        response.headers["X-Request-ID"] = rid
        return response
