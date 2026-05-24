"""Voice / TTS management routes — list, clone, record, and delete voices.

Integrates with CosyVoice2 API at 10.190.0.222:8000 for TTS and voice cloning.
"""
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from ..config import settings
from ..database import get_db
from ..models.user import User
from ..models.voice import Voice
from ..schemas.voice import VoiceCreate, VoiceResponse
from ..auth_deps import get_current_user
from ..services.tts_service import tts_service

router = APIRouter()

ALLOWED_AUDIO_TYPES = {
    "audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3",
    "audio/ogg", "audio/webm", "audio/x-m4a", "audio/mp4",
    "audio/flac",
}


def _is_allowed_audio(filename: str) -> bool:
    ext = os.path.splitext(filename)[1].lower()
    return ext in {".wav", ".mp3", ".ogg", ".webm", ".m4a", ".mp4", ".flac"}


def _voice_to_response(v: Voice) -> VoiceResponse:
    return VoiceResponse(
        id=v.id,
        name=v.name,
        description=v.description,
        voice_type=v.voice_type,
        file_path=v.file_path,
        is_default=v.is_default,
        created_at=v.created_at,
    )


@router.get("/", response_model=list[VoiceResponse])
async def list_voices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the current user's cloned voices."""
    result = await db.execute(
        select(Voice).where(Voice.id == -1)  # No user_id on Voice model yet; return empty
    )
    # Note: The Voice model doesn't have a user_id column.
    # For now, return all voices. In production, add user_id to Voice model.
    result = await db.execute(select(Voice).order_by(Voice.created_at.desc()))
    voices = list(result.scalars().all())
    return [_voice_to_response(v) for v in voices]


@router.post("/", response_model=VoiceResponse, status_code=201)
async def clone_voice(
    file: UploadFile = File(...),
    name: str = Form("Cloned Voice"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Clone a new voice from an uploaded audio file.

    Accepts WAV, MP3, OGG, WebM audio formats.
    Integrates with CosyVoice2 API for voice cloning.
    """
    # Validate file type
    if file.content_type and file.content_type not in ALLOWED_AUDIO_TYPES:
        if not _is_allowed_audio(file.filename or ""):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported audio type: {file.content_type}. "
                       f"Supported: wav, mp3, ogg, webm, m4a",
            )

    # Save the uploaded file
    voice_id_str = str(uuid.uuid4())
    ext = os.path.splitext(file.filename or "voice.wav")[1] or ".wav"
    upload_dir = os.path.join(settings.upload_dir, "voices", voice_id_str)
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"source{ext}")

    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save audio: {e}")

    # Clone via CosyVoice2
    try:
        cosy_voice_id = await tts_service.clone_voice(file_path)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Voice cloning service unavailable: {e}",
        )

    # Create DB record
    voice = Voice(
        name=name,
        description=f"Cloned via CosyVoice2 (ID: {cosy_voice_id})",
        voice_type="cloned",
        file_path=file_path,
        is_default=False,
    )
    db.add(voice)
    await db.flush()
    await db.refresh(voice)

    return _voice_to_response(voice)


@router.post("/record", response_model=VoiceResponse, status_code=201)
async def record_voice(
    file: UploadFile = File(...),
    name: str = Form("Recorded Voice"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record and clone a voice from a frontend audio blob (~10 seconds).

    Accepts the audio blob sent from the browser's MediaRecorder API.
    Integrates with CosyVoice2 API for voice cloning.
    """
    # Save the recorded blob
    voice_id_str = str(uuid.uuid4())
    ext = os.path.splitext(file.filename or "recorded_voice.webm")[1] or ".webm"
    if not ext or ext == "":
        ext = ".webm"
    upload_dir = os.path.join(settings.upload_dir, "voices", voice_id_str)
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"recording{ext}")

    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save recording: {e}")

    # Clone via CosyVoice2
    try:
        cosy_voice_id = await tts_service.clone_voice(file_path)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Voice cloning service unavailable: {e}",
        )

    # Create DB record
    voice = Voice(
        name=name,
        description=f"Recorded via browser, cloned via CosyVoice2 (ID: {cosy_voice_id})",
        voice_type="cloned",
        file_path=file_path,
        is_default=False,
    )
    db.add(voice)
    await db.flush()
    await db.refresh(voice)

    return _voice_to_response(voice)


@router.delete("/{voice_id}")
async def delete_voice(
    voice_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a cloned voice by ID."""
    result = await db.execute(select(Voice).where(Voice.id == voice_id))
    voice = result.scalar_one_or_none()
    if not voice:
        raise HTTPException(status_code=404, detail="Voice not found")

    # Remove audio file
    if voice.file_path and os.path.exists(voice.file_path):
        try:
            os.remove(voice.file_path)
            # Try to remove parent dir if empty
            parent = os.path.dirname(voice.file_path)
            if os.path.isdir(parent) and not os.listdir(parent):
                os.rmdir(parent)
        except OSError:
            pass  # Non-critical cleanup

    await db.delete(voice)
    return {"message": "Voice deleted", "voice_id": voice_id}
