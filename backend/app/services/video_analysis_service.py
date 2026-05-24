"""Reference video analysis service — extracts style, pacing, scene changes, and visual metadata."""
import json
import os
import re
import subprocess
import tempfile
from typing import Optional
import httpx
from ..config import settings


class VideoAnalysisService:
    """Service that analyzes reference videos for visual style, pacing, transitions, and more.

    Uses FFmpeg to extract video metadata and scene changes, and the LLM API
    (at 10.190.0.214:8080/v1) to analyze visual style from frame descriptions.
    """

    def __init__(self):
        self.llm_api_key = settings.llm_api_key
        self.llm_api_url = settings.llm_api_url.rstrip("/")
        self.llm_model = "deepseek-v4-pro"
        self.timeout = 120.0
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        """Verify FFmpeg tools are available and raise if not."""
        for tool in ("ffmpeg", "ffprobe"):
            try:
                subprocess.run([tool, "-version"], capture_output=True, check=True)
            except (FileNotFoundError, subprocess.CalledProcessError):
                raise RuntimeError(
                    f"{tool} is not installed or not in PATH. Install it with: brew install ffmpeg"
                )

    @staticmethod
    def _ensure_dir(path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)

    async def analyze_reference_video(self, video_path: str, output_dir: Optional[str] = None) -> dict:
        """Analyze a reference video and return a comprehensive analysis report.

        Args:
            video_path: Path to the reference video file.
            output_dir: Optional directory to store intermediate keyframes.

        Returns:
            dict with keys: style_analysis, pacing, scene_changes, transitions,
                            subtitle_style, color_palette, estimated_mood
        """
        if not os.path.exists(video_path):
            return {"error": f"Video file not found: {video_path}"}

        # 1. Extract video metadata via ffprobe
        video_info = self._extract_metadata(video_path)

        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="video_analysis_")
        else:
            self._ensure_dir(output_dir + "/")

        # 2. Extract keyframes at intervals
        frame_descriptions = []
        keyframe_paths = await self.extract_keyframes(video_path, output_dir, interval=2)
        for kf in keyframe_paths:
            desc = self._describe_frame(kf)
            frame_descriptions.append(desc)

        # 3. Detect scene changes
        scene_changes = self.detect_scene_changes(video_path)

        # 4. Analyze pacing and transitions from scene changes
        pacing = self._analyze_pacing(scene_changes, video_info.get("duration", 0))
        transitions = self._analyze_transitions(scene_changes)

        # 5. Use LLM to analyze visual style
        style_analysis = await self.analyze_with_llm(video_info, frame_descriptions)

        # 6. Extract approximate subtitle pacing (if available) or estimate
        subtitle_style = self._estimate_subtitle_style(pacing, video_info)

        return {
            "style_analysis": style_analysis,
            "pacing": pacing,
            "scene_changes": scene_changes,
            "transitions": transitions,
            "subtitle_style": subtitle_style,
            "color_palette": style_analysis.get("color_palette", []),
            "estimated_mood": style_analysis.get("estimated_mood", "neutral"),
            "video_info": video_info,
        }

    def _extract_metadata(self, video_path: str) -> dict:
        """Extract video metadata using ffprobe."""
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
            data = json.loads(result.stdout)
        except (subprocess.CalledProcessError, json.JSONDecodeError, subprocess.TimeoutExpired) as e:
            return {"error": f"ffprobe failed: {e}"}

        metadata = {
            "format": data.get("format", {}).get("format_name", ""),
            "duration": float(data.get("format", {}).get("duration", 0)),
            "size": int(data.get("format", {}).get("size", 0)),
            "bitrate": int(data.get("format", {}).get("bit_rate", 0)),
            "streams": [],
        }

        for stream in data.get("streams", []):
            if stream["codec_type"] == "video":
                metadata["video_stream"] = {
                    "codec": stream.get("codec_name", ""),
                    "width": int(stream.get("width", 0)),
                    "height": int(stream.get("height", 0)),
                    "fps": self._parse_fps(stream.get("r_frame_rate", "0/1")),
                    "pixel_format": stream.get("pix_fmt", ""),
                }
            elif stream["codec_type"] == "audio":
                metadata.setdefault("audio_streams", []).append({
                    "codec": stream.get("codec_name", ""),
                    "sample_rate": int(stream.get("sample_rate", 0)),
                    "channels": int(stream.get("channels", 0)),
                })
            metadata["streams"].append({
                "index": stream.get("index"),
                "codec_type": stream["codec_type"],
                "codec": stream.get("codec_name", ""),
            })

        return metadata

    @staticmethod
    def _parse_fps(r_frame_rate: str) -> float:
        """Parse a FFmpeg frame rate string like '30000/1001' -> 29.97."""
        try:
            if "/" in r_frame_rate:
                num, den = r_frame_rate.split("/")
                return round(float(num) / float(den), 2)
            return float(r_frame_rate)
        except (ValueError, ZeroDivisionError):
            return 30.0

    async def extract_keyframes(self, video_path: str, output_dir: str, interval: int = 2) -> list[str]:
        """Extract one frame every N seconds from the video.

        Args:
            video_path: Path to the video file.
            output_dir: Directory to save extracted frames.
            interval: Extract one frame every N seconds.

        Returns:
            List of paths to extracted frame images.
        """
        os.makedirs(output_dir, exist_ok=True)
        output_pattern = os.path.join(output_dir, "frame_%04d.jpg")

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"fps=1/{interval},scale=640:-1",
            "-frames:v", "20",  # limit to 20 frames max
            "-q:v", "5",
            output_pattern,
        ]
        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=120)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            return []

        # Collect generated frames
        frames = sorted(
            [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.startswith("frame_") and f.endswith(".jpg")]
        )
        return frames

    def detect_scene_changes(self, video_path: str) -> list[dict]:
        """Detect scene changes using FFmpeg scene detection filter.

        Returns:
            List of dicts with 'timestamp' (float, seconds) and 'score' (float, 0-1).
        """
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-show_entries", "frame=pts_time",
            "-of", "csv=p=0",
            "-f", "lavfi",
            f"movie={video_path},select=gt(scene\\,0.3)",
            video_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                return []
            lines = [l.strip() for l in result.stdout.split("\n") if l.strip()]
            scene_changes = []
            for line in lines:
                try:
                    ts = float(line)
                    scene_changes.append({"timestamp": round(ts, 2), "score": 0.5})
                except ValueError:
                    continue
            return scene_changes
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            # Fallback: use a simpler approach
            return self._detect_scene_changes_fallback(video_path)

    def _detect_scene_changes_fallback(self, video_path: str) -> list[dict]:
        """Fallback scene detection using FFmpeg scene filter output."""
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", "select='gt(scene,0.4)',showinfo",
            "-f", "null",
            "-",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            timestamps = []
            pattern = re.compile(r"pts_time:([\d.]+)")
            for line in result.stderr.split("\n"):
                match = pattern.search(line)
                if match:
                    ts = float(match.group(1))
                    timestamps.append({"timestamp": round(ts, 2), "score": 0.5})
            return timestamps
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return []

    @staticmethod
    def _describe_frame(image_path: str) -> str:
        """Generate a basic description of a frame (resolution info, no actual vision)."""
        if not os.path.exists(image_path):
            return ""
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", image_path],
                capture_output=True, text=True, timeout=10,
            )
            data = json.loads(result.stdout)
            streams = data.get("streams", [])
            for s in streams:
                if s.get("codec_type") == "video":
                    w, h = s.get("width", 0), s.get("height", 0)
                    return f"Frame at {image_path}: {w}x{h}, format {s.get('pix_fmt', 'unknown')}"
            return f"Frame at {image_path}"
        except Exception:
            return f"Frame at {image_path}"

    async def analyze_with_llm(self, video_info: dict, frame_descriptions: list[str]) -> dict:
        """Send video info and frame descriptions to the LLM for style analysis.

        Args:
            video_info: Metadata dict from _extract_metadata.
            frame_descriptions: List of text descriptions of extracted frames.

        Returns:
            Dict with keys: visual_style, color_palette, estimated_mood, composition_notes, recommendations
        """
        resolution = "unknown"
        video_stream = video_info.get("video_stream", {})
        if video_stream:
            resolution = f"{video_stream.get('width', '?')}x{video_stream.get('height', '?')}"

        frame_summary = "\n".join(frame_descriptions[:20]) if frame_descriptions else "No frames extracted."

        system_prompt = (
            "You are a professional video style analyst. Analyze the provided video metadata and frame descriptions "
            "and return a JSON object with the following keys:\n"
            '  - "visual_style": str (e.g., "cinematic", "vlog", "tutorial", "commercial", "documentary")\n'
            '  - "color_palette": list[str] (dominant colors from the frames)\n'
            '  - "estimated_mood": str (e.g., "energetic", "calm", "professional", "whimsical")\n'
            '  - "composition_notes": str (observations about framing, lighting, subject placement)\n'
            '  - "recommendations": list[str] (style recommendations for generated video)\n\n'
            "Return ONLY the JSON object, no extra text or markdown."
        )

        user_prompt = (
            f"Video Resolution: {resolution}\n"
            f"Duration: {video_info.get('duration', 0):.1f}s\n"
            f"FPS: {video_stream.get('fps', '?')}\n"
            f"Codec: {video_stream.get('codec', '?')}\n\n"
            f"Frame Descriptions:\n{frame_summary}\n\n"
            "Analyze the visual style, color palette, and mood of this video."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        headers = {
            "Authorization": f"Bearer {self.llm_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.llm_model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 2048,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.llm_api_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
                result = data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return {
                "visual_style": "unknown",
                "color_palette": [],
                "estimated_mood": "neutral",
                "composition_notes": f"LLM analysis failed: {e}",
                "recommendations": [],
            }

        # Clean up potential markdown fences
        if result.startswith("```"):
            result = result.split("\n", 1)[1] if "\n" in result else result[3:]
            if result.endswith("```"):
                result = result[:-3]
            result = result.strip()

        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {
                "visual_style": "unknown",
                "color_palette": [],
                "estimated_mood": "neutral",
                "composition_notes": result,
                "recommendations": [],
            }

    @staticmethod
    def _analyze_pacing(scene_changes: list[dict], total_duration: float) -> dict:
        """Analyze pacing based on detected scene changes."""
        if not scene_changes or total_duration <= 0:
            return {"avg_scene_duration": 0, "scene_count": 0, "pace": "unknown"}

        scene_count = len(scene_changes) + 1  # N cuts = N+1 scenes
        avg_duration = total_duration / scene_count if scene_count > 0 else 0

        if avg_duration < 2:
            pace = "very_fast"
        elif avg_duration < 5:
            pace = "fast"
        elif avg_duration < 10:
            pace = "moderate"
        else:
            pace = "slow"

        return {
            "avg_scene_duration": round(avg_duration, 2),
            "scene_count": scene_count,
            "pace": pace,
            "total_duration": total_duration,
        }

    @staticmethod
    def _analyze_transitions(scene_changes: list[dict]) -> dict:
        """Analyze transition patterns from scene changes."""
        if not scene_changes:
            return {"predominant": "cut", "change_frequency": 0}

        timestamps = [s["timestamp"] for s in scene_changes]
        gaps = []
        for i in range(1, len(timestamps)):
            gaps.append(timestamps[i] - timestamps[i - 1])

        avg_gap = sum(gaps) / len(gaps) if gaps else 0
        if avg_gap < 2:
            predominant = "fast_cut"
        elif avg_gap < 5:
            predominant = "cut"
        else:
            predominant = "slow_transition"

        return {
            "predominant": predominant,
            "change_frequency": round(len(scene_changes) / (timestamps[-1] if timestamps else 1), 2),
            "transition_count": len(scene_changes),
        }

    @staticmethod
    def _estimate_subtitle_style(pacing: dict, video_info: dict) -> dict:
        """Estimate appropriate subtitle style based on video pacing and metadata."""
        pace = pacing.get("pace", "moderate")
        style_map = {
            "very_fast": {"style": "tiktok_dynamic", "size": "large", "animation": "scale_in", "position": "center"},
            "fast": {"style": "kinetic", "size": "medium", "animation": "fade_in", "position": "bottom"},
            "moderate": {"style": "elegant", "size": "medium", "animation": "slide_up", "position": "bottom"},
            "slow": {"style": "cinematic", "size": "small", "animation": "typewriter", "position": "bottom_center"},
        }
        return style_map.get(pace, {"style": "standard", "size": "medium", "animation": "fade", "position": "bottom"})

    async def check_connectivity(self) -> bool:
        """Check if FFmpeg/ffprobe are available."""
        try:
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
            probe_result = subprocess.run(["ffprobe", "-version"], capture_output=True, timeout=5)
            return result.returncode == 0 and probe_result.returncode == 0
        except Exception:
            return False


# Singleton
video_analysis_service = VideoAnalysisService()
