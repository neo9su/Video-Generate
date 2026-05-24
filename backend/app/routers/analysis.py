"""Video analysis routes — reference video analysis with style, pacing, and scene detection."""
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import json

from ..config import settings
from ..database import get_db
from ..services.video_analysis_service import video_analysis_service

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])


@router.post("/reference", status_code=202)
async def analyze_reference_video(
    file: UploadFile = File(...),
    task_id: Optional[str] = Query(None, description="Optional task ID to associate this analysis with"),
):
    """Upload a reference video for style, pacing, and scene analysis.

    Accepts a video file, extracts metadata via FFmpeg, detects scene changes,
    and uses LLM for visual style analysis. Returns an analysis task ID that
    can be polled for results.
    """
    # Validate file type
    allowed_types = {"video/mp4", "video/quicktime", "video/x-msvideo", "video/webm", "video/x-matroska"}
    if file.content_type and file.content_type not in allowed_types:
        # Check file extension as fallback
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in (".mp4", ".mov", ".avi", ".webm", ".mkv"):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported video type: {file.content_type or ext}. "
                       f"Supported: mp4, mov, avi, webm, mkv",
            )

    # Generate analysis task ID
    analysis_id = task_id or str(uuid.uuid4())

    # Save uploaded video to temp location
    upload_dir = os.path.join(settings.upload_dir, "analysis", analysis_id)
    os.makedirs(upload_dir, exist_ok=True)

    video_path = os.path.join(upload_dir, file.filename or "reference.mp4")
    try:
        content = await file.read()
        with open(video_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded video: {e}")

    # Run analysis
    try:
        analysis_result = await video_analysis_service.analyze_reference_video(video_path, upload_dir)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video analysis failed: {e}")

    # Save analysis result to JSON for polling
    result_path = os.path.join(upload_dir, "analysis_result.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(analysis_result, f, ensure_ascii=False, indent=2)

    # Clean up extracted frames to save space (keep the report)
    for fname in os.listdir(upload_dir):
        if fname.startswith("frame_") and fname.endswith(".jpg"):
            os.remove(os.path.join(upload_dir, fname))

    return {
        "task_id": analysis_id,
        "status": "completed",
        "message": "Reference video analysis complete",
        "result": analysis_result,
    }


@router.get("/{analysis_id}")
async def get_analysis_result(analysis_id: str):
    """Get the analysis results for a previously uploaded reference video.

    Args:
        analysis_id: The analysis task ID returned from the POST endpoint.
    """
    upload_dir = os.path.join(settings.upload_dir, "analysis", analysis_id)
    result_path = os.path.join(upload_dir, "analysis_result.json")

    if not os.path.exists(result_path):
        raise HTTPException(status_code=404, detail=f"Analysis not found: {analysis_id}")

    try:
        with open(result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to read analysis result: {e}")

    return {
        "task_id": analysis_id,
        "status": "completed",
        "result": result,
    }
