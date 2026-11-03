"""
GlucoShield — Production API Middleware (Phase 16)
==================================================
Provides:
  1. Structured JSON Request & Observability Logging (Zero secrets/passwords/JWTs logged).
  2. Rate Limiting & Abuse Prevention (Token bucket / sliding window per client IP).
  3. Request Size Enforcement (Rejects oversized payloads > 10MB).
  4. Global Exception Sanitization (Prevents leaking stack traces or internal paths to clients).
"""

import time
import json
import uuid
import logging
from collections import defaultdict
from typing import Dict, List, Tuple
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger("glucoshield.access")

# ------------------------------------------------------------------------------
# 1. Rate Limiting Tracker
# ------------------------------------------------------------------------------
class RateLimiter:
    """Sliding-window in-memory rate limiter per client IP."""
    def __init__(self, general_rpm: int = 120, inference_rpm: int = 30):
        self.general_rpm = general_rpm
        self.inference_rpm = inference_rpm
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self.inference_requests: Dict[str, List[float]] = defaultdict(list)
        self.expensive_paths = {
            "/api/v1/forecast",
            "/api/v1/what-if",
            "/api/v1/food/analyze",
            "/api/v1/decision/full-flow",
            "/api/v1/analytics"
        }

    def is_allowed(self, ip: str, path: str) -> Tuple[bool, int]:
        now = time.time()
        window_start = now - 60.0

        # Health checks are never rate-limited
        if path.startswith("/api/v1/health"):
            return True, 0

        # Clean old requests
        self.requests[ip] = [t for t in self.requests[ip] if t > window_start]
        if len(self.requests[ip]) >= self.general_rpm:
            return False, int(60 - (now - self.requests[ip][0]))

        is_expensive = any(path.startswith(p) for p in self.expensive_paths)
        if is_expensive:
            self.inference_requests[ip] = [t for t in self.inference_requests[ip] if t > window_start]
            if len(self.inference_requests[ip]) >= self.inference_rpm:
                return False, int(60 - (now - self.inference_requests[ip][0]))
            self.inference_requests[ip].append(now)

        self.requests[ip].append(now)
        return True, 0

# ------------------------------------------------------------------------------
# 2. Hardened Security & Observability Middleware
# ------------------------------------------------------------------------------
class HardenedProductionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, config):
        super().__init__(app)
        self.config = config
        self.limiter = RateLimiter(
            general_rpm=config.rate_limit_general_rpm,
            inference_rpm=config.rate_limit_inference_rpm
        )

    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = str(uuid.uuid4())
        request.state.request_id = req_id
        start_time = time.time()

        # 1. Payload Size Check
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.config.max_request_size_bytes:
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "error": "Payload Too Large",
                            "detail": f"Request size exceeds allowed limit of {self.config.max_request_size_bytes // 1048576}MB.",
                            "request_id": req_id
                        },
                        headers={"X-Request-ID": req_id}
                    )
            except ValueError:
                pass

        # 2. Rate Limiting Check
        if self.config.rate_limit_enabled:
            client_ip = request.client.host if request.client else "127.0.0.1"
            allowed, retry_after = self.limiter.is_allowed(client_ip, request.url.path)
            if not allowed:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Rate Limit Exceeded",
                        "detail": "Too many requests. Please throttle your requests.",
                        "request_id": req_id
                    },
                    headers={
                        "X-Request-ID": req_id,
                        "Retry-After": str(max(1, retry_after))
                    }
                )

        # 3. Request Processing & Sanitized Error Handling
        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            # Log full error internally
            logger.error(
                json.dumps({
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "request_id": req_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "duration_ms": duration_ms,
                    "error": str(exc),
                    "exception_type": exc.__class__.__name__
                })
            )
            # Return sanitized response to client (zero internal details leaked)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal Server Error",
                    "detail": "An unexpected error occurred. This incident has been logged.",
                    "request_id": req_id
                },
                headers={"X-Request-ID": req_id}
            )

        duration_ms = round((time.time() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = req_id

        # 4. Structured JSON Access Log (Strictly Omitting Secrets and Sensitive Data)
        client_ip = request.client.host if request.client else "unknown"
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "request_id": req_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "client_ip": client_ip
        }
        logger.info(json.dumps(log_entry))

        return response
