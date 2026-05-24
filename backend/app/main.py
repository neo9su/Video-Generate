"""FastAPI entry point for Video-Generate backend."""
from fastapi import FastAPI
from .config import settings
from .database import engine, Base
from .routers import auth, tasks, videos, voices, prompts, health

app = FastAPI(
    title="Video-Generate API",
    version="0.1.0",
    description="AI-powered video generation platform",
)

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(videos.router, prefix="/api/v1/videos", tags=["videos"])
app.include_router(voices.router, prefix="/api/v1/voices", tags=["voices"])
app.include_router(prompts.router, prefix="/api/v1/prompts", tags=["prompts"])


@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)
