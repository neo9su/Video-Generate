"""Health check routes — verifies connectivity to all backend services."""
from fastapi import APIRouter
from ..database import check_db_connection, check_redis_connection
from ..services.llm_service import llm_service
from ..services.tts_service import tts_service
from ..services.composition_service import composition_service

router = APIRouter()


@router.get("/health")
async def health_check():
    """Comprehensive health check that verifies all backend services."""
    db_ok = await check_db_connection()
    redis_ok = await check_redis_connection()
    llm_ok = await llm_service.check_connectivity()
    tts_ok = await tts_service.check_connectivity()
    ffmpeg_ok = await composition_service.check_connectivity()

    all_ok = all([db_ok, redis_ok, llm_ok, tts_ok, ffmpeg_ok])

    return {
        "status": "healthy" if all_ok else "degraded",
        "service": "video-generate-api",
        "checks": {
            "database": "ok" if db_ok else "unreachable",
            "redis": "ok" if redis_ok else "unreachable",
            "llm_api": "ok" if llm_ok else "unreachable",
            "cosyvoice_tts": "ok" if tts_ok else "unreachable",
            "ffmpeg": "ok" if ffmpeg_ok else "unavailable",
        },
    }
