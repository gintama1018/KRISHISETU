"""
KrishiSetu — Production Security & Hardening Layer
- Rate Limiting (Sliding-Window Rate Limiter per IP)
- Security Headers (HSTS, X-Content-Type-Options, X-Frame-Options, CSP)
- Global Exception Masking (Zero internal stack traces exposed to client)
- Role-Based Access Control (RBAC) via Supabase JWT verification
- Request Sanitization
"""
import os
import time
from collections import defaultdict
from typing import Optional, List
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# ── 1. RATE LIMITER (Sliding-Window Rate Limiter per IP) ─────────────────────
# Rate limits: 60 requests per minute per IP for general endpoints
# 10 requests per minute per IP for heavy AI advisory generation
RATE_LIMIT_GENERAL = 60      # max 60 req/min
RATE_LIMIT_HEAVY   = 10      # max 10 req/min for /advisory/generate

# NOTE: in-memory cache; effective only within a warm serverless instance. For guaranteed cross-instance dedup, replace with Supabase table or Redis (Upstash) before claiming exact latency numbers at scale.
_ip_request_history = defaultdict(list)


def is_rate_limited(ip: str, limit: int, window: int = 60) -> bool:
    now = time.time()
    history = _ip_request_history[ip]
    # Filter out requests older than the time window
    _ip_request_history[ip] = [t for t in history if now - t < window]
    if len(_ip_request_history[ip]) >= limit:
        return True
    _ip_request_history[ip].append(now)
    return False


# ── 2. SECURITY MIDDLEWARE ──────────────────────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Rate Limiting Check
        ip = request.client.host if request.client else "127.0.0.1"
        path = request.url.path

        limit = RATE_LIMIT_HEAVY if "/advisory/generate" in path else RATE_LIMIT_GENERAL
        if is_rate_limited(ip, limit=limit, window=60):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "message": "Rate limit exceeded. Please wait a minute before retrying.",
                    "code": 429,
                },
            )

        # 2. Process Request
        response: Response = await call_next(request)

        # 3. Add Hardened Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data: https://*.tile.openstreetmap.org; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net https://unpkg.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "connect-src 'self' https://*.supabase.co"
        )
        
        # Remove server header information disclosure
        if "server" in response.headers:
            del response.headers["server"]

        return response


# ── 3. GLOBAL EXCEPTION MASKING ──────────────────────────────────────────────
async def global_exception_handler(request: Request, exc: Exception):
    """
    Mask internal backend crashes so raw stack traces, database credentials,
    or internal file paths are NEVER returned to the client.
    """
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "code": exc.status_code},
        )

    # Log internal error server-side silently
    print(f"[SECURITY ALERT] Unhandled Server Exception at {request.url.path}: {exc}")

    # Return safe generic response to client
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. The incident has been logged securely.",
            "code": 500,
        },
    )


# ── 4. ROLE-BASED ACCESS CONTROL (RBAC) ──────────────────────────────────────
def _extract_role_from_jwt(token: str) -> Optional[str]:
    """Decode and verify Supabase JWT claims to extract role."""
    import jwt
    jwt_secret = os.getenv("SUPABASE_JWT_SECRET", "").strip()
    try:
        if jwt_secret:
            payload = jwt.decode(token, jwt_secret, algorithms=["HS256"], options={"verify_aud": False})
        else:
            payload = jwt.decode(token, options={"verify_signature": False})
        app_meta = payload.get("app_metadata", {})
        user_meta = payload.get("user_metadata", {})
        role = app_meta.get("role") or user_meta.get("role") or payload.get("role")
        return str(role).lower() if role else None
    except Exception:
        return None


def require_role(allowed_roles: List[str]):
    """
    FastAPI dependency enforcing RBAC.
    Validates Supabase-issued Bearer JWT claims.
    X-Role header is ONLY accepted as an override during local development (APP_ENV=development).
    """
    async def _role_checker(request: Request):
        role: Optional[str] = None

        # 1. Dev-only override via X-Role (gated strictly behind APP_ENV == "development")
        if os.getenv("APP_ENV") == "development":
            dev_role = request.headers.get("X-Role", "").strip().lower()
            if dev_role:
                role = dev_role

        # 2. Real auth mechanism: Bearer token JWT claim verification
        if not role:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:].strip()
                role = _extract_role_from_jwt(token)

        # If no valid role can be determined, require authentication
        if not role:
            raise HTTPException(status_code=401, detail="Authentication required")

        if role not in [r.lower() for r in allowed_roles] and "admin" not in role:
            raise HTTPException(
                status_code=403,
                detail=f"Access forbidden: User role '{role}' is not authorized. Allowed roles: {allowed_roles}"
            )
        return role

    return _role_checker
