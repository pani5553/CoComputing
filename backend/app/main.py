"""
Co-Computing FastAPI application entry point.

Configures:
- CORS (allow_origins from FRONTEND_URL env var)
- Security headers middleware (X-Content-Type-Options, X-Frame-Options)
- Router registration with correct prefixes
- OpenAPI docs disabled in production
"""
import logging

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.routers import auth, client, compute, profile, tasks, wallet, work

# ──────────────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.WARNING if settings.is_production else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("co-computing")

# ──────────────────────────────────────────────────────────────────────────────
# FastAPI application
# ──────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Co-Computing API",
    description="API REST para la plataforma de computación distribuida Co-Computing.",
    version="1.0.0",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

# ──────────────────────────────────────────────────────────────────────────────
# CORS Middleware
# ──────────────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────────────────────
# Security headers middleware
# ──────────────────────────────────────────────────────────────────────────────


@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    """Add security headers to every response."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


# ──────────────────────────────────────────────────────────────────────────────
# Global exception handler for unhandled errors
# ──────────────────────────────────────────────────────────────────────────────


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"},
    )


# ──────────────────────────────────────────────────────────────────────────────
# Router registration
# ──────────────────────────────────────────────────────────────────────────────

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(wallet.router, prefix="/wallet", tags=["wallet"])
app.include_router(profile.router, prefix="/profile", tags=["profile"])
app.include_router(compute.router, prefix="/jobs", tags=["compute"])
app.include_router(work.router, prefix="/work", tags=["work"])
app.include_router(client.router, prefix="/client", tags=["client"])


# ──────────────────────────────────────────────────────────────────────────────
# Health check
# ──────────────────────────────────────────────────────────────────────────────


@app.get("/health", tags=["health"], include_in_schema=not settings.is_production)
def health_check() -> dict:
    """Simple health check endpoint."""
    return {"status": "ok", "environment": settings.environment}
