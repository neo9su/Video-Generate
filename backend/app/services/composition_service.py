"""Video composition service — combines all assets into final video using FFmpeg."""
import json
import os
import subprocess
from typing import Optional
from ..config import settings


class CompositionService:
    """Service that composes final videos from scenes, audio, and subtitles using FFmpeg."""

    def __init__(self):
        self.output_dir = settings.output_dir
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        """Verify FFmpeg is available."""
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            raise RuntimeError("FFmpeg is not installed or not in PATH. Install it with: brew install ffmpeg")

    def _ensure_dir(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)

    async def compose_video(
        self,
        scenes: list[dict],
        audio_path: str,
        subtitles: Optional[str] = None,
        output_path: str = "",
        resolution: str = "1080p",
        aspect_ratio: str = "16:9",
    ) -> str:
        """Compose a final video from storyboard scenes, background audio, and optional subtitles.

        Args:
            scenes: List of scene dicts, each with 'image_path', 'duration_seconds', 'narration'.
            audio_path: Path to background/narration audio file.
            subtitles: Optional path to an SRT subtitle file.
            output_path: Destination path for the output video.
            resolution: '1080p' (default), '720p', '4k'.
            aspect_ratio: '16:9' (horizontal, default) or '9:16' (vertical/shorts).

        Returns:
            Path to the composed video file.
        """
        if not output_path:
            output_path = os.path.join(self.output_dir, "composed", "final_video.mp4")
        self._ensure_dir(output_path)

        # Determine resolution
        width, height = self._get_resolution(resolution, aspect_ratio)

        # Create a concat file for scenes
        scenes_dir = os.path.join(self.output_dir, "scenes")
        os.makedirs(scenes_dir, exist_ok=True)

        # If scenes have video/image paths, create video segments
        scene_files = []
        for i, scene in enumerate(scenes):
            video_clip_path = scene.get("video_path", "")
            image_path = scene.get("image_path", "")
            duration = float(scene.get("duration_seconds", 5.0))
            scene_output = os.path.join(scenes_dir, f"scene_{i:04d}.mp4")

            if video_clip_path and os.path.exists(video_clip_path):
                # Use AI-generated video clip, scale to target resolution
                self._scale_video_clip(video_clip_path, scene_output, width, height)
            elif image_path and os.path.exists(image_path):
                # Create a video segment from image with duration
                self._image_to_video(image_path, scene_output, duration, width, height)
            else:
                # Create a blank/color segment
                self._create_blank_segment(scene_output, duration, width, height, i)

            scene_files.append(scene_output)

        # Concatenate all scene videos
        concat_list = os.path.join(self.output_dir, "scenes_concat.txt")
        with open(concat_list, "w") as f:
            for sf in scene_files:
                f.write(f"file '{sf}'\n")

        concatenated_video = os.path.join(self.output_dir, "scenes_merged.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
            concatenated_video,
        ]
        subprocess.run(cmd, capture_output=True, check=True)

        # Add audio
        video_with_audio = os.path.join(self.output_dir, "with_audio.mp4")
        if os.path.exists(audio_path):
            cmd = [
                "ffmpeg", "-y",
                "-i", concatenated_video,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                video_with_audio,
            ]
            subprocess.run(cmd, capture_output=True, check=True)
        else:
            video_with_audio = concatenated_video

        # Add subtitles if provided
        result_file = video_with_audio
        if subtitles and os.path.exists(subtitles):
            subtitled_output = os.path.join(self.output_dir, "with_subtitles.mp4")
            cmd = [
                "ffmpeg", "-y",
                "-i", video_with_audio,
                "-vf", f"subtitles={subtitles}",
                "-c:a", "copy",
                subtitled_output,
            ]
            subprocess.run(cmd, capture_output=True, check=True)
            result_file = subtitled_output

        # Copy to final output path if different
        if result_file != output_path:
            cmd = ["cp", result_file, output_path]
            subprocess.run(cmd, check=True)

        # Cleanup intermediate files
        self._cleanup_intermediate(scene_files + [concat_list, concatenated_video, video_with_audio])

        return output_path

    def _image_to_video(self, image_path: str, output_path: str, duration: float, width: int, height: int):
        """Create a video segment from a single image with Ken Burns slow zoom effect."""
        total_frames = int(duration * 30)
        cmd = [
            "ffmpeg", "-y",
            "-i", image_path,
            "-vf", (
                f"zoompan=z='if(lte(on,1),1,min(zoom+0.002,1.06))':"
                f"d={total_frames}:s={width}x{height}:fps=30"
            ),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            output_path,
        ]
        subprocess.run(cmd, capture_output=True, check=True)

    def _scale_video_clip(self, input_path: str, output_path: str, width: int, height: int):
        """Scale an AI-generated video clip to the target resolution and normalize FPS to 30."""
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", (
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
                f"fps=30"
            ),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-an",  # Strip original audio (we'll add TTS audio later)
            output_path,
        ]
        subprocess.run(cmd, capture_output=True, check=True)

    def _create_blank_segment(self, output_path: str, duration: float, width: int, height: int, index: int):
        """Create a blank/colored video segment (fallback when no image)."""
        colors = ["#1a1a2e", "#16213e", "#0f3460", "#e94560", "#533483", "#3b82f6", "#10b981", "#f59e0b"]
        color = colors[index % len(colors)]
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c={color}:s={width}x{height}:d={duration}:r=30",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-t", str(duration),
            output_path,
        ]
        subprocess.run(cmd, capture_output=True, check=True)

    def _get_resolution(self, resolution: str, aspect_ratio: str) -> tuple[int, int]:
        """Get width x height from resolution name and aspect ratio."""
        res_map = {
            "720p": (720, 1280),
            "1080p": (1080, 1920),
            "4k": (2160, 3840),
        }
        base = res_map.get(resolution, (1080, 1920))
        if aspect_ratio == "16:9":
            # Horizontal: width x height where height is the smaller
            return (base[1], base[0])  # e.g., 1920x1080
        else:
            # Vertical / 9:16
            return base  # e.g., 1080x1920

    def add_subtitles(self, video_path: str, subtitle_path: str, output_path: str) -> str:
        """Burn subtitles into a video."""
        self._ensure_dir(output_path)
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"subtitles={subtitle_path}",
            "-c:a", "copy",
            output_path,
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path

    def add_background_music(self, video_path: str, music_path: str, output_path: str, volume: float = 0.3) -> str:
        """Add background music to a video, mixing with existing audio."""
        self._ensure_dir(output_path)
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", music_path,
            "-filter_complex",
            f"[1:a]volume={volume}[music];[0:a][music]amix=inputs=2:duration=first[audio]",
            "-map", "0:v",
            "-map", "[audio]",
            "-c:v", "copy",
            output_path,
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path

    def _cleanup_intermediate(self, files: list[str]):
        """Remove intermediate files."""
        for f in files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except OSError:
                pass

    async def check_connectivity(self) -> bool:
        """Check if FFmpeg is available."""
        try:
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False


# Singleton
composition_service = CompositionService()
