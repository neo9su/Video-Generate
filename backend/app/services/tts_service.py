"""TTS service - Edge TTS primary for English, CosyVoice2 fallback for Chinese."""
from typing import Optional
import asyncio
import json
import os
import re
import httpx
from ..config import settings


# Detect if text is primarily Chinese
_CHINESE_RE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf]')


def _is_chinese(text: str) -> bool:
    """Returns True if the text contains significant Chinese characters."""
    chinese_chars = len(_CHINESE_RE.findall(text))
    return chinese_chars > 0 and chinese_chars >= len(text) * 0.1


class EdgeTTSEngine:
    """TTS engine using Microsoft Edge TTS (free, no API key, excellent English)."""

    VOICE_MAP = {
        "default": "en-US-JennyNeural",
        "female": "en-US-JennyNeural",
        "male": "en-US-GuyNeural",
        "nova": "en-US-NovaNeural",
        "en-uk": "en-GB-SoniaNeural",
        "en-au": "en-AU-NatashaNeural",
    }

    def __init__(self):
        self._check_edge()

    def _check_edge(self):
        """Verify edge-tts is installed."""
        import subprocess
        try:
            subprocess.run(["edge-tts", "--help"], capture_output=True, timeout=5, check=False)
        except FileNotFoundError:
            pass  # Will be reported at runtime

    async def generate(self, text: str, voice_id: str = "default") -> bytes:
        """Generate WAV audio using edge-tts CLI."""
        voice = self.VOICE_MAP.get(voice_id, voice_id)
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            out_path = f.name

        try:
            proc = await asyncio.create_subprocess_exec(
                "edge-tts",
                "--text", text,
                "--voice", voice,
                "--write-media", out_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)

            if proc.returncode != 0:
                raise RuntimeError(f"edge-tts failed (exit {proc.returncode}): {stderr.decode()[:200]}")

            with open(out_path, "rb") as f:
                audio_data = f.read()

            if len(audio_data) < 500:
                raise RuntimeError(f"Edge TTS output too small: {len(audio_data)} bytes")

            return audio_data
        except asyncio.TimeoutError:
            raise RuntimeError("Edge TTS timed out after 30s")
        finally:
            try:
                os.unlink(out_path)
            except OSError:
                pass

    async def check_connectivity(self) -> bool:
        """Check if edge-tts is usable."""
        try:
            result = await self.generate("Hello", "default")
            return len(result) > 500
        except Exception:
            return False


class CosyVoice2Engine:
    """TTS engine using CosyVoice2 Gradio API (for Chinese text)."""

    def __init__(self):
        self.base_url = settings.cosyvoice_url.rstrip("/")

    async def generate(self, text: str, voice_id: str = "default") -> bytes:
        """Generate TTS using CosyVoice2 Gradio API."""
        payload = {
            "data": [
                text,
                "预训练音色",
                "",
                "",
                None,
                None,
                "",
                0,
                False,
                1.0,
            ]
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            # Submit job
            resp = await client.post(
                f"{self.base_url}/gradio_api/call/generate_audio",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            event_id = data.get("event_id")
            if not event_id:
                raise RuntimeError(f"CosyVoice2: no event_id: {data}")

            # Poll SSE for completion
            audio_hash = None
            for attempt in range(60):
                await asyncio.sleep(1)
                sse_resp = await client.get(
                    f"{self.base_url}/gradio_api/call/generate_audio/{event_id}"
                )
                body = sse_resp.text

                if not audio_hash:
                    for line in body.split("\n"):
                        if line.startswith("data:"):
                            try:
                                result_data = json.loads(line[5:].strip())
                                if isinstance(result_data, list) and result_data:
                                    info = result_data[0]
                                    if isinstance(info, dict) and "path" in info:
                                        audio_hash = info["path"].split("/")[0]
                            except (json.JSONDecodeError, IndexError):
                                continue

                if "event: complete" in body:
                    break
                if "event: error" in body:
                    for line in body.split("\n"):
                        if line.startswith("data:"):
                            try:
                                err_data = json.loads(line[5:].strip())
                                if isinstance(err_data, dict) and err_data.get("error"):
                                    raise RuntimeError(f"CosyVoice2 error: {err_data['error']}")
                            except json.JSONDecodeError:
                                pass
                    break

            if not audio_hash:
                raise RuntimeError("CosyVoice2: no audio hash from Gradio API")

            # Read WAV from shared volume
            wav_path = f"/tmp/gradio/{audio_hash}/audio.wav"
            for retry in range(30):
                await asyncio.sleep(1)
                try:
                    if not os.path.exists(wav_path):
                        continue
                    stat = os.stat(wav_path)
                    if stat.st_size > 500:
                        with open(wav_path, "rb") as f:
                            return f.read()
                except (FileNotFoundError, OSError):
                    continue

            raise RuntimeError(f"CosyVoice2: WAV not found at {wav_path}")

    async def check_connectivity(self) -> bool:
        """Check if CosyVoice2 is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/gradio_api/info")
                return resp.status_code == 200
        except Exception:
            return False


class TTSService:
    """TTS service that auto-selects engine based on text language.

    - English text → Edge TTS (high quality, natural English)
    - Chinese text → CosyVoice2 (high quality Chinese TTS)
    """

    def __init__(self):
        self.edge = EdgeTTSEngine()
        self.cosyvoice = CosyVoice2Engine()

    async def generate_voice(self, text: str, voice_id: str = "default") -> bytes:
        """Generate TTS audio. Auto-selects engine based on language.

        Returns raw audio bytes (WAV or MP3).
        """
        if not text or not text.strip():
            raise ValueError("TTS: empty text")

        use_chinese = _is_chinese(text)

        if use_chinese:
            try:
                return await self.cosyvoice.generate(text, voice_id)
            except Exception as e:
                # Fallback: try Edge TTS anyway
                try:
                    return await self.edge.generate(text, voice_id)
                except Exception:
                    raise RuntimeError(f"TTS failed (CosyVoice2: {e})")

        # English → Edge TTS
        try:
            return await self.edge.generate(text, voice_id)
        except Exception as e:
            # Fallback: try CosyVoice2
            try:
                return await self.cosyvoice.generate(text, voice_id)
            except Exception:
                raise RuntimeError(f"TTS failed (Edge TTS: {e})")

    async def check_connectivity(self) -> bool:
        """Check if at least one TTS engine is available."""
        edge_ok = await self.edge.check_connectivity()
        cosy_ok = await self.cosyvoice.check_connectivity()
        return edge_ok or cosy_ok


# Singleton
tts_service = TTSService()
