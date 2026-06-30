"""FastAPI entry point for Video-Generate backend."""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .config import settings
from .database import engine, Base
from .routers import auth, tasks, videos, voices, prompts, health, analysis
from .routers import admin, api_keys, webhooks, billing
from .routers import remake
from .routers import watermark
from .middleware import RateLimitMiddleware

app = FastAPI(
    title="Video-Generate API",
    version="0.1.0",
    description="AI-powered video generation platform",
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    RateLimitMiddleware,
    default_limit=600,
    window_seconds=60,
)

# Existing routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(videos.router, prefix="/api/v1/videos", tags=["videos"])
app.include_router(voices.router, prefix="/api/v1/voices", tags=["voices"])
app.include_router(prompts.router, prefix="/api/v1/prompts", tags=["prompts"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["analysis"])

# Phase 3 routers
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(api_keys.router, prefix="/api/v1/api-keys", tags=["api-keys"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])
app.include_router(billing.router, prefix="/api/v1/billing", tags=["billing"])

# Path B: Face swap + voice clone
app.include_router(remake.router, prefix="/api/v1/remake", tags=["remake"])
app.include_router(watermark.router, prefix="/api/v1/watermark", tags=["watermark"])
os.makedirs(settings.output_dir, exist_ok=True)
app.mount("/api/v1/files", StaticFiles(directory=settings.output_dir), name="files")


@app.on_event("startup")
async def startup():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception:
        # ENUM type may already exist from another worker
        pass
