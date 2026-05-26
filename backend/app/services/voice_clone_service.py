"""Voice cloning service using CosyVoice2.

Generates TTS audio with a cloned voice timbre from a reference audio sample.
CosyVoice2 runs locally on macOS (Apple Silicon) for low-latency inference.

Pipeline:
  1. User provides reference audio (voice sample)
  2. Split text into manageable chunks (~60 chars each)
  3. CosyVoice2 generates each chunk with cloned voice
  4. Concatenate all chunks into final audio
  5. Optionally adjust speed to match target video duration
"""
import asyncio
import os
import subprocess
import tempfile
import uuid
from typing import Optional

from ..config import settings


class VoiceCloneService:
    """Clone voice from reference audio and generate narration."""

    COSYVOICE_PYTHON = os.path.expanduser("~/cosyvoice-env/bin/python")
    COSYVOICE_SCRIPT = os.path.expanduser("~/cosyvoice2/cosyvoice_synth.py")
    COSYVOICE_MODEL = os.path.expanduser(
        "~/.cosyvoice/models/iic/CosyVoice2-0___5B"
    )
    # Max chars per chunk to avoid CosyVoice2 timeout
    MAX_CHUNK_CHARS = 80

    def __init__(self):
        self.default_ref_audio = os.path.expanduser(
            "~/Movies/5月9日(2)/5月9日(2).wav"
        )

    async def clone_voice_narration(
        self,
        text: str,
        ref_audio_path: str,
        output_path: str,
        target_duration: Optional[float] = None,
    ) -> str:
        """Generate narration audio with cloned voice.

        Args:
            text: Full narration text to synthesize.
            ref_audio_path: Path to reference audio for voice cloning.
            output_path: Where to save the final audio.
            target_duration: If set, adjust audio speed to match this duration (seconds).

        Returns:
            Path to the generated audio file.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Split text into chunks
        chunks = self._split_text(text)
        print(f"[VoiceClone] Generating {len(chunks)} chunks...")

        # Generate each chunk
        chunk_files = []
        tmp_dir = tempfile.mkdtemp(prefix="voice_clone_")

        for i, chunk in enumerate(chunks):
            chunk_path = os.path.join(tmp_dir, f"chunk_{i:03d}.wav")
            await self._generate_chunk(chunk, ref_audio_path, chunk_path)
            if os.path.exists(chunk_path):
                chunk_files.append(chunk_path)
                print(f"[VoiceClone] Chunk {i+1}/{len(chunks)} done")
            else:
                print(f"[VoiceClone] Chunk {i+1} FAILED, skipping")

        if not chunk_files:
            raise RuntimeError("Voice cloning failed: no chunks generated")

        # Concatenate chunks
        concat_path = os.path.join(tmp_dir, "concat.wav")
        await self._concat_audio(chunk_files, concat_path)

        # Adjust speed if target duration specified
        if target_duration and target_duration > 0:
            audio_dur = await self._get_duration(concat_path)
            if audio_dur > 0 and abs(audio_dur - target_duration) > 1.0:
                tempo = audio_dur / target_duration
                # atempo filter only supports 0.5 - 100.0
                tempo = max(0.5, min(100.0, tempo))
                print(
                    f"[VoiceClone] Adjusting speed: {audio_dur:.1f}s -> "
                    f"{target_duration:.1f}s (tempo={tempo:.3f})"
                )
                await self._adjust_speed(concat_path, output_path, tempo)
            else:
                subprocess.run(["cp", concat_path, output_path], check=True)
        else:
            subprocess.run(["cp", concat_path, output_path], check=True)

        # Cleanup temp files
        subprocess.run(["rm", "-rf", tmp_dir], capture_output=True)

        final_dur = await self._get_duration(output_path)
        print(f"[VoiceClone] Final audio: {final_dur:.1f}s -> {output_path}")
        return output_path

    async def _generate_chunk(
        self, text: str, ref_audio: str, output_path: str
    ):
        """Generate a single chunk with CosyVoice2."""
        cmd = [
            self.COSYVOICE_PYTHON,
            self.COSYVOICE_SCRIPT,
            "--text", text,
            "--out", output_path,
            "--ref-audio", ref_audio,
            "--ref-text", "",
            "--model-dir", self.COSYVOICE_MODEL,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=120
        )
        if proc.returncode != 0:
            print(f"[VoiceClone] Chunk error: {stderr.decode()[-200:]}")

    async def _concat_audio(self, files: list[str], output_path: str):
        """Concatenate audio files using FFmpeg."""
        list_file = output_path + ".list"
        with open(list_file, "w") as f:
            for fp in files:
                f.write(f"file '{fp}'\n")

        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", list_file, "-c", "copy", output_path,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        os.remove(list_file)

    async def _adjust_speed(self, input_path: str, output_path: str, tempo: float):
        """Adjust audio playback speed using FFmpeg atempo filter."""
        # atempo supports 0.5 to 100.0, chain multiple for extreme values
        filters = []
        remaining = tempo
        while remaining > 2.0:
            filters.append("atempo=2.0")
            remaining /= 2.0
        while remaining < 0.5:
            filters.append("atempo=0.5")
            remaining /= 0.5
        filters.append(f"atempo={remaining:.4f}")

        filter_str = ",".join(filters)
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-filter:a", filter_str, output_path,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()

    async def _get_duration(self, audio_path: str) -> float:
        """Get audio duration in seconds."""
        cmd = [
            "ffprobe", "-v", "quiet", "-show_format", "-print_format", "json",
            audio_path,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        import json
        try:
            data = json.loads(stdout.decode())
            return float(data["format"]["duration"])
        except (json.JSONDecodeError, KeyError):
            return 0.0

    def _split_text(self, text: str) -> list[str]:
        """Split text into chunks suitable for CosyVoice2.

        Splits on sentence boundaries (。！？，；) keeping chunks under MAX_CHUNK_CHARS.
        """
        # Split on Chinese punctuation
        import re
        sentences = re.split(r'([。！？；])', text)

        # Recombine punctuation with preceding sentence
        parts = []
        for i in range(0, len(sentences) - 1, 2):
            s = sentences[i]
            if i + 1 < len(sentences):
                s += sentences[i + 1]
            if s.strip():
                parts.append(s.strip())
        # Handle last part if odd
        if len(sentences) % 2 == 1 and sentences[-1].strip():
            parts.append(sentences[-1].strip())

        # Merge short sentences, split long ones
        chunks = []
        current = ""
        for part in parts:
            if len(current) + len(part) <= self.MAX_CHUNK_CHARS:
                current += part
            else:
                if current:
                    chunks.append(current)
                # If single part is too long, split on comma
                if len(part) > self.MAX_CHUNK_CHARS:
                    sub_parts = re.split(r'([，,])', part)
                    sub_current = ""
                    for sp in sub_parts:
                        if len(sub_current) + len(sp) <= self.MAX_CHUNK_CHARS:
                            sub_current += sp
                        else:
                            if sub_current:
                                chunks.append(sub_current)
                            sub_current = sp
                    current = sub_current
                else:
                    current = part

        if current:
            chunks.append(current)

        return chunks

    async def check_connectivity(self) -> bool:
        """Check if CosyVoice2 is available."""
        return (
            os.path.exists(self.COSYVOICE_PYTHON)
            and os.path.exists(self.COSYVOICE_SCRIPT)
            and os.path.exists(self.COSYVOICE_MODEL)
        )


# Singleton
voice_clone_service = VoiceCloneService()
