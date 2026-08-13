"""
KrishiSetu — Main FastAPI Application Entry Point
Layer: API Gateway (Production Security & Concurrency Hardened)
"""
import os
import pathlib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

from api.routes import ingestion, advisory, farmer, prices, cross_domain, compliance, mock_agristack, push, auth
from api.security import SecurityHeadersMiddleware, global_exception_handler

app = FastAPI(
    title="KrishiSetu API",
    description="AI-powered agritech platform for rural farmers — IIT Guwahati Hackathon",
    version="2.1.0",
    docs_url="/docs" if os.getenv("APP_ENV") != "production" else None,
    redoc_url=None,
)

# ── 1. Security Headers & Rate Limiting Middleware ──────────────────────────
app.add_middleware(SecurityHeadersMiddleware)

# ── 2. CORS Policy ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ── 3. Global Exception Handler (Zero Stack Trace Disclosure) ───────────────
app.add_exception_handler(Exception, global_exception_handler)

# ── 4. API Routers ──────────────────────────────────────────────────────────
app.include_router(auth.router,           prefix="/api/v1/auth",         tags=["Supabase Real-Time Auth"])
app.include_router(ingestion.router,      prefix="/api/v1/data",         tags=["Data Ingestion"])
app.include_router(advisory.router,       prefix="/api/v1/advisory",     tags=["AI Advisory"])
app.include_router(farmer.router,         prefix="/api/v1/farmer",       tags=["Farmer Registry"])
app.include_router(prices.router,         prefix="/api/v1/prices",       tags=["Market Prices"])
app.include_router(cross_domain.router,   prefix="/api/v1/cross-domain", tags=["Cross-Domain Intelligence"])
app.include_router(compliance.router,     prefix="/api/v1/compliance",   tags=["DPDP Compliance"])
app.include_router(push.router,           prefix="/api/v1/push",         tags=["Web Push Notifications"])
app.include_router(mock_agristack.router, prefix="/mock/agristack",      tags=["AgriStack Mock"])


@app.get("/api/v1/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "project": "KrishiSetu",
        "version": "2.1.0",
        "database": "supabase_postgresql",
        "security": "hardened",
        "rate_limiting": "enabled",
        "layers": [
            "offline-pwa", "data-ingestion", "streaming-engine",
            "ai-advisory", "multilingual-voice", "role-delivery",
            "dpdp-compliance", "web-push-notifications", "security-hardening"
        ],
    }


# ── 5. Serve Frontend PWA ───────────────────────────────────────────────────
from fastapi.responses import FileResponse

_frontend_dir = pathlib.Path(__file__).parent / "frontend"

@app.get("/")
async def root_dashboard():
    """Default entry point: serve Officer Dashboard as the primary public landing page."""
    dash_path = _frontend_dir / "dashboard.html"
    if dash_path.exists():
        return FileResponse(str(dash_path))
    return {"message": "KrishiSetu API Server Running"}

@app.get("/landing.html")
async def serve_landing():
    """Explicit landing page route serving index.html for local Uvicorn runs."""
    landing_path = _frontend_dir / "index.html"
    if landing_path.exists():
        return FileResponse(str(landing_path))
    return FileResponse(str(_frontend_dir / "dashboard.html"))

if _frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")

