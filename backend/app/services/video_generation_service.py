"""Video generation service using SiliconFlow Wan2.2 API.

Supports text-to-video (T2V) and image-to-video (I2V) generation
via SiliconFlow's cloud API with Wan-AI/Wan2.2 models.

API Flow:
  1. POST /v1/video/submit → returns requestId
  2. POST /v1/video/status (poll) → returns video URL when done
"""
import asyncio
import base64
import os
import time
from typing import Optional

import httpx

from ..config import settings


class VideoGenerationService:
    """Generate real AI video clips using SiliconFlow Wan2.2 API."""

    BASE_URL = "https://api.siliconflow.cn/v1"
    T2V_MODEL = "Wan-AI/Wan2.2-T2V-A14B"
    I2V_MODEL = "Wan-AI/Wan2.2-I2V-A14B"

    # Poll config
    MAX_POLL_TIME = 600  # 10 minutes max wait
    POLL_INTERVAL = 10   # Check every 10 seconds

    def __init__(self):
        self.api_key = settings.siliconflow_api_key

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def text_to_video(
        self,
        prompt: str,
        output_path: str,
        image_size: str = "720x1280",
        negative_prompt: str = "",
        seed: int = -1,
    ) -> str:
        """Generate a video from text prompt (T2V).

        Args:
            prompt: Text description of the video to generate.
            output_path: Where to save the downloaded video.
            image_size: Resolution - '720x1280' (vertical) or '1280x720' (horizontal).
            negative_prompt: Things to avoid.
            seed: Random seed (-1 for random).

        Returns:
            Path to the saved video file.
        """
        payload = {
            "model": self.T2V_MODEL,
            "prompt": prompt,
            "image_size": image_size,
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        if seed >= 0:
            payload["seed"] = seed

        return await self._submit_and_download(payload, output_path)

    async def image_to_video(
        self,
        prompt: str,
        image_path: str,
        output_path: str,
        image_size: str = "720x1280",
        negative_prompt: str = "",
        seed: int = -1,
    ) -> str:
        """Generate a video from an image + text prompt (I2V).

        Args:
            prompt: Text description of the motion/action to apply.
            image_path: Path to the reference image (first frame).
            output_path: Where to save the downloaded video.
            image_size: Resolution - '720x1280' (vertical) or '1280x720' (horizontal).
            negative_prompt: Things to avoid.
            seed: Random seed (-1 for random).

        Returns:
            Path to the saved video file.
        """
        # Encode image to base64
        with open(image_path, "rb") as f:
            image_data = f.read()

        # Detect image type
        if image_path.lower().endswith(".png"):
            mime_type = "image/png"
        else:
            mime_type = "image/jpeg"

        b64_image = base64.b64encode(image_data).decode()
        image_url = f"data:{mime_type};base64,{b64_image}"

        payload = {
            "model": self.I2V_MODEL,
            "prompt": prompt,
            "image_size": image_size,
            "image": image_url,
        }
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        if seed >= 0:
            payload["seed"] = seed

        return await self._submit_and_download(payload, output_path)

    async def _submit_and_download(self, payload: dict, output_path: str) -> str:
        """Submit a video generation request, poll until complete, download result.

        Returns:
            Path to the saved video file.

        Raises:
            RuntimeError: If generation fails or times out.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Submit request
            resp = await client.post(
                f"{self.BASE_URL}/video/submit",
                headers=self._headers(),
                json=payload,
            )
            if resp.status_code != 200:
                raise RuntimeError(
                    f"SiliconFlow video submit failed: {resp.status_code} - {resp.text[:300]}"
                )
            request_id = resp.json().get("requestId")
            if not request_id:
                raise RuntimeError(f"SiliconFlow: no requestId in response: {resp.text[:200]}")

            print(f"[VideoGen] Submitted request: {request_id}, polling for result...")

            # 2. Poll for completion
            start_time = time.time()
            while (time.time() - start_time) < self.MAX_POLL_TIME:
                await asyncio.sleep(self.POLL_INTERVAL)

                status_resp = await client.post(
                    f"{self.BASE_URL}/video/status",
                    headers=self._headers(),
                    json={"requestId": request_id},
                )
                if status_resp.status_code != 200:
                    print(f"[VideoGen] Status poll error: {status_resp.status_code}")
                    continue

                status_data = status_resp.json()
                status = status_data.get("status", "")

                if status == "Succeed":
                    # Get video URL
                    videos = status_data.get("results", {}).get("videos", [])
                    if not videos:
                        raise RuntimeError("SiliconFlow: succeeded but no video URLs")
                    video_url = videos[0].get("url", "")
                    if not video_url:
                        raise RuntimeError("SiliconFlow: empty video URL")

                    # Download video
                    print(f"[VideoGen] Generation complete! Downloading...")
                    dl_resp = await client.get(video_url, timeout=60.0)
                    if dl_resp.status_code != 200:
                        raise RuntimeError(
                            f"SiliconFlow: video download failed: {dl_resp.status_code}"
                        )
                    with open(output_path, "wb") as f:
                        f.write(dl_resp.content)

                    file_size = os.path.getsize(output_path)
                    elapsed = time.time() - start_time
                    print(
                        f"[VideoGen] Saved {file_size/1024:.0f}KB to {output_path} "
                        f"(took {elapsed:.0f}s)"
                    )
                    return output_path

                elif status == "Failed":
                    reason = status_data.get("reason", "unknown")
                    raise RuntimeError(f"SiliconFlow video generation failed: {reason}")

                elif status == "InProgress":
                    elapsed = int(time.time() - start_time)
                    print(f"[VideoGen] Still generating... ({elapsed}s elapsed)")
                    continue

                else:
                    print(f"[VideoGen] Unknown status: {status}")
                    continue

            raise TimeoutError(
                f"SiliconFlow video generation timed out after {self.MAX_POLL_TIME}s "
                f"for request {request_id}"
            )

    async def generate_scenes_video(
        self,
        scenes: list[dict],
        output_dir: str,
        task_id: str = "",
        image_paths: Optional[list[str]] = None,
    ) -> list[str]:
        """Generate video clips for all scenes in a storyboard.

        For each scene:
          - If a reference image is available → use I2V (image_to_video)
          - Otherwise → use T2V (text_to_video)

        Args:
            scenes: List of scene dicts with 'visual_prompt', 'motion_description',
                    'scene_number', etc.
            output_dir: Directory for output video clips.
            task_id: Optional task ID.
            image_paths: Optional list of reference image paths (from ComfyUI).

        Returns:
            List of paths to generated video clips (empty string for failures).
        """
        videos_dir = os.path.join(output_dir, "video_clips")
        os.makedirs(videos_dir, exist_ok=True)

        video_paths = []
        for i, scene in enumerate(scenes):
            scene_num = scene.get("scene_number", i + 1)
            prompt = scene.get("visual_prompt") or scene.get("visual_description", "")
            motion = scene.get("motion_description", "")

            # Combine prompt with motion description for video
            video_prompt = prompt
            if motion:
                video_prompt = f"{prompt}. Motion: {motion}"

            output_path = os.path.join(videos_dir, f"scene_{scene_num:04d}.mp4")

            # Check if we have a reference image for this scene
            has_image = (
                image_paths
                and i < len(image_paths)
                and image_paths[i]
                and os.path.exists(image_paths[i])
            )

            try:
                if has_image:
                    print(f"[VideoGen] Scene {scene_num}: I2V with reference image")
                    await self.image_to_video(
                        prompt=video_prompt,
                        image_path=image_paths[i],
                        output_path=output_path,
                        image_size="720x1280",
                    )
                else:
                    print(f"[VideoGen] Scene {scene_num}: T2V (no reference image)")
                    await self.text_to_video(
                        prompt=video_prompt,
                        output_path=output_path,
                        image_size="720x1280",
                    )
                video_paths.append(output_path)
            except Exception as e:
                print(f"[VideoGen] Scene {scene_num} FAILED: {e}")
                video_paths.append("")

        return video_paths

    async def check_balance(self) -> float:
        """Check remaining SiliconFlow account balance."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.siliconflow.cn/v1/user/info",
                headers=self._headers(),
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                return float(data.get("totalBalance", 0))
        return 0.0

    async def check_connectivity(self) -> bool:
        """Check if SiliconFlow API is reachable and key is valid."""
        try:
            balance = await self.check_balance()
            return balance >= 0
        except Exception:
            return False


# Singleton
video_gen_service = VideoGenerationService()
