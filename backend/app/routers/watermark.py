"""Watermark annotation endpoints."""
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..config import settings
from ..services.watermark_service import watermark_service

router = APIRouter()


class FrameRequest(BaseModel):
    video_path: str
    task_id: str = ""


class SegmentRequest(BaseModel):
    video_path: str
    threshold: float = 0.3


@router.post("/frames")
async def get_frames(req: FrameRequest):
    if not os.path.exists(req.video_path):
        raise HTTPException(404, "Video file not found")
    d = os.path.join(settings.output_dir, "watermark_frames", req.task_id or "temp")
    r = watermark_service.extract_first_last_frames(req.video_path, d, req.task_id)
    r["first_frame_url"] = "/api/v1/files/" + os.path.relpath(r["first_frame"], settings.output_dir)
    r["last_frame_url"] = "/api/v1/files/" + os.path.relpath(r["last_frame"], settings.output_dir)
    return r


@router.post("/segments")
async def get_segments(req: SegmentRequest):
    if not os.path.exists(req.video_path):
        raise HTTPException(404, "Video file not found")
    segs = watermark_service.detect_segments(req.video_path, req.threshold)
    return {"segments": segs, "total": len(segs)}
