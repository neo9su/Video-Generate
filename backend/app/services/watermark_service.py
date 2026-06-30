"""Watermark detection and removal service."""
import os
import subprocess
import json
import uuid
from typing import Optional
from ..config import settings


class WatermarkService:
    """Service for video watermark detection annotation and removal."""

    def __init__(self):
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        for tool in ("ffmpeg", "ffprobe"):
            try:
                subprocess.run([tool, "-version"], capture_output=True, check=True)
            except (FileNotFoundError, subprocess.CalledProcessError):
                raise RuntimeError(f"{tool} is not installed")

    def get_video_info(self, video_path: str) -> dict:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", video_path
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        info = json.loads(r.stdout)
        stream = info["streams"][0]
        duration = float(info["format"]["duration"])
        fps = eval(stream.get("r_frame_rate", "25/1"))
        total_frames = int(duration * fps)
        return {
            "duration": duration, "fps": round(fps, 2),
            "total_frames": total_frames,
            "width": stream.get("width", 0),
            "height": stream.get("height", 0),
        }

    def extract_frame(self, video_path: str, timestamp: float, output_path: str) -> str:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(timestamp), "-i", video_path,
            "-vframes", "1", "-q:v", "2", output_path
        ], capture_output=True, check=True)
        return output_path

    def extract_first_last_frames(self, video_path: str, output_dir: str, task_id: str = "") -> dict:
        info = self.get_video_info(video_path)
        os.makedirs(output_dir, exist_ok=True)
        prefix = f"{task_id}_" if task_id else ""
        first_frame = os.path.join(output_dir, f"{prefix}first_frame.jpg")
        self.extract_frame(video_path, 0.0, first_frame)
        last_ts = max(0.0, info["duration"] - 0.5)
        last_frame = os.path.join(output_dir, f"{prefix}last_frame.jpg")
        self.extract_frame(video_path, last_ts, last_frame)
        return {
            "first_frame": first_frame, "first_frame_ts": 0.0,
            "last_frame": last_frame, "last_frame_ts": round(last_ts, 2),
            "video_info": info,
        }

    def detect_segments(self, video_path: str, threshold: float = 0.3) -> list[dict]:
        cmd = [
            "ffmpeg", "-i", video_path,
            "-filter:v", "select='gt(scene,{})',showinfo".format(threshold),
            "-f", "null", "-"
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        info = self.get_video_info(video_path)
        duration = info["duration"]
        changes = [0.0]
        for line in r.stderr.split("\n"):
            if "pts_time:" in line:
                for part in line.split():
                    if part.startswith("pts_time:"):
                        try:
                            ts = float(part.split(":")[1])
                            if 0 < ts < duration:
                                changes.append(ts)
                        except ValueError:
                            pass
        changes.append(duration)
        changes = sorted(set(changes))
        segments = []
        for i in range(len(changes) - 1):
            segments.append({
                "segment_id": i,
                "start_time": round(changes[i], 2),
                "end_time": round(changes[i + 1], 2),
                "duration": round(changes[i + 1] - changes[i], 2),
            })
        return segments

    def extract_segment_frames(self, video_path: str, segments: list[dict],
                               output_dir: str, task_id: str = "") -> list[dict]:
        os.makedirs(output_dir, exist_ok=True)
        prefix = f"{task_id}_" if task_id else ""
        result = []
        for seg in segments:
            first_path = os.path.join(output_dir, f"{prefix}seg{seg['segment_id']}_first.jpg")
            last_path = os.path.join(output_dir, f"{prefix}seg{seg['segment_id']}_last.jpg")
            self.extract_frame(video_path, seg["start_time"], first_path)
            last_ts = max(seg["start_time"], seg["end_time"] - 0.3)
            self.extract_frame(video_path, last_ts, last_path)
            result.append({
                "segment_id": seg["segment_id"],
                "start_time": seg["start_time"],
                "end_time": seg["end_time"],
                "first_frame": first_path,
                "last_frame": last_path,
            })
        return result


watermark_service = WatermarkService()
