"""
KrishiSetu — Main FastAPI Application Entry Point
Layer: API Gateway
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

from api.routes import ingestion, advisory, farmer, prices, cross_domain, compliance, mock_agristack

app = FastAPI(
    title="KrishiSetu API",
    description="AI-powered agritech platform for rural farmers — IIT Guwahati Hackathon",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(ingestion.router, prefix="/api/v1/data", tags=["Data Ingestion"])
app.include_router(advisory.router, prefix="/api/v1/advisory", tags=["AI Advisory"])
app.include_router(farmer.router, prefix="/api/v1/farmer", tags=["Farmer Registry"])
app.include_router(prices.router, prefix="/api/v1/prices", tags=["Market Prices"])
app.include_router(cross_domain.router, prefix="/api/v1/cross-domain", tags=["Cross-Domain Intelligence"])
app.include_router(compliance.router, prefix="/api/v1/compliance", tags=["DPDP Compliance"])
app.include_router(mock_agristack.router, prefix="/mock/agristack", tags=["AgriStack Mock"])

# Serve frontend PWA (graceful if directory doesn't exist)
import pathlib
_frontend_dir = pathlib.Path(__file__).parent / "frontend"
if _frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")



@app.get("/api/v1/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "project": "KrishiSetu",
        "version": "1.0.0",
        "layers": ["offline-pwa", "ingestion", "streaming", "ai-advisory", "multilingual", "role-delivery", "compliance"],
    }
