"""Custom middleware for the PowerSymphony workflow system."""

import uuid
import logging
from typing import Callable, Awaitable
from fastapi import Request, HTTPException, FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import time
import re
import os

from utils.structured_logger import get_server_logger, LogType
from utils.exceptions import SecurityError

logger = logging.getLogger(__name__)

PUBLIC_PATHS = {
    "/api/auth/signup",
    "/api/auth/login",
    "/api/auth/logout",
    "/health",
    "/health/",
    "/health/live",
    "/health/ready",
}

PUBLIC_PREFIXES = (
    "/docs",
    "/openapi",
    "/redoc",
)


async def auth_middleware(request: Request, call_next: Callable):
    path = request.url.path

    if path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES):
        return await call_next(request)

    if not path.startswith("/api/"):
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})

    token = auth_header[7:]
    try:
        from server.services.auth_service import decode_jwt, get_user_by_id
        payload = decode_jwt(token)
        if not payload:
            return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})
        user = get_user_by_id(payload["sub"])
        if not user:
            return JSONResponse(status_code=401, content={"detail": "User not found"})
        request.state.user = dict(user)
    except Exception as e:
        logger.error(f"Auth middleware error: {e}")
        return JSONResponse(status_code=401, content={"detail": "Authentication failed"})

    return await call_next(request)


async def correlation_id_middleware(request: Request, call_next: Callable):
    """Add correlation ID to requests for tracing."""
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    # Log the request and response
    logger = get_server_logger()
    logger.log_request(
        request.method,
        str(request.url),
        correlation_id=correlation_id,
        path=request.url.path,
        query_params=dict(request.query_params),
        client_host=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    logger.log_response(
        response.status_code,
        duration,
        correlation_id=correlation_id,
        content_length=response.headers.get("content-length")
    )
    
    # Add correlation ID to response headers
    response.headers["X-Correlation-ID"] = correlation_id
    
    return response


async def security_middleware(request: Request, call_next: Callable):
    """Security middleware to validate requests."""
    if request.url.path.startswith("/api/") and request.method in ["POST", "PUT", "PATCH"]:
        content_type = request.headers.get("content-type", "").lower()
        content_length = request.headers.get("content-length", "0")
        has_body = content_length != "0" and content_type
        if has_body and not content_type.startswith("application/json") and not content_type.startswith("multipart/form-data"):
            raise HTTPException(
                status_code=400,
                detail="Content-Type must be application/json for API endpoints"
            )
    
    # Validate file paths to prevent path traversal
    # Check URL path for suspicious patterns
    path = request.url.path
    if ".." in path or "./" in path:
        # Use a more thorough check
        if re.search(r"(\.{2}[/\\])|([/\\]\.{2})", path):
            logger = get_server_logger()
            logger.log_security_event(
                "PATH_TRAVERSAL_ATTEMPT",
                f"Suspicious path detected: {path}",
                correlation_id=getattr(request.state, 'correlation_id', str(uuid.uuid4()))
            )
            raise HTTPException(status_code=400, detail="Invalid path")
    
    response = await call_next(request)
    return response


_rate_limit_store: dict = {}
_RATE_LIMIT_WINDOW = 60
_RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "120"))


async def rate_limit_middleware(request: Request, call_next: Callable):
    """In-memory per-IP sliding-window rate limiter."""
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()

    window_start = now - _RATE_LIMIT_WINDOW
    entries = _rate_limit_store.get(client_ip, [])
    entries = [t for t in entries if t > window_start]

    if len(entries) >= _RATE_LIMIT_MAX:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Try again later."},
        )

    entries.append(now)
    _rate_limit_store[client_ip] = entries

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(_RATE_LIMIT_MAX)
    response.headers["X-RateLimit-Remaining"] = str(max(0, _RATE_LIMIT_MAX - len(entries)))
    return response


def add_cors_middleware(app: FastAPI) -> None:
    """Configure and attach CORS middleware."""
    # Dev defaults; override via CORS_ALLOW_ORIGINS (comma-separated)
    default_origins = [
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    env_origins = os.getenv("CORS_ALLOW_ORIGINS")
    if env_origins:
        origins = [o.strip() for o in env_origins.split(",") if o.strip()]
        origin_regex = None
    else:
        origins = default_origins
        # Allow localhost, 127.0.0.1 on any port, and Replit proxy domains
        origin_regex = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$|^https://.*\.repl\.co$|^https://.*\.replit\.dev$|^https://.*\.kirk\.replit\.dev$"

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID"],
        max_age=600,
    )


def add_middleware(app: FastAPI):
    """Add all middleware to the FastAPI application."""
    # Attach CORS first to handle preflight requests and allow origins.
    add_cors_middleware(app)

    app.middleware("http")(correlation_id_middleware)
    app.middleware("http")(auth_middleware)
    app.middleware("http")(security_middleware)
    
    return app
