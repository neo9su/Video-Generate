"""Text-to-Speech service — CosyVoice2 integration."""
import json
import httpx
from typing import Optional
from ..config import settings


class TTSService:
    """Service that calls CosyVoice2 at 10.190.0.222:8000."""

    def __init__(self):
        self.base_url = settings.cosyvoice_url.rstrip("/")
        self.timeout = 120.0

    async def generate_voice(self, text: str, voice_id: str = "default") -> bytes:
        """Generate audio from text using CosyVoice2 TTS.

        Returns raw audio bytes (WAV format expected).
        """
        url = f"{self.base_url}/v1/tts"
        payload = {
            "text": text,
            "voice_id": voice_id,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            # CosyVoice may return audio directly or a JSON with audio_url
            content_type = resp.headers.get("content-type", "")
            if "application/json" in content_type:
                data = resp.json()
                audio_url = data.get("audio_url") or data.get("url")
                if audio_url:
                    # Fetch the actual audio
                    audio_resp = await client.get(audio_url)
                    audio_resp.raise_for_status()
                    return audio_resp.content
                # Check for base64-encoded audio
                audio_base64 = data.get("audio") or data.get("audio_base64")
                if audio_base64:
                    import base64
                    return base64.b64decode(audio_base64)
                raise ValueError(f"Unexpected CosyVoice response: {data}")
            return resp.content

    async def clone_voice(self, audio_file_path: str) -> str:
        """Clone a voice from an audio file via the CosyVoice2 API.

        Returns the new voice_id string.
        """
        url = f"{self.base_url}/v1/voice/clone"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            with open(audio_file_path, "rb") as f:
                files = {"audio": ("voice_sample.wav", f, "audio/wav")}
                resp = await client.post(url, files=files)
            resp.raise_for_status()
            data = resp.json()
            return data.get("voice_id", data.get("id", "cloned_voice"))

    async def list_voices(self) -> list[dict]:
        """List available voices from CosyVoice2."""
        url = f"{self.base_url}/v1/voices"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return data
            return data.get("voices", data.get("data", []))

    async def check_connectivity(self) -> bool:
        """Check if CosyVoice2 is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/health")
                return resp.status_code < 500
        except Exception:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(f"{self.base_url}/")
                    return resp.status_code < 500
            except Exception:
                return False


# Singleton
tts_service = TTSService()
