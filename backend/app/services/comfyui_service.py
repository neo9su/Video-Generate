"""ComfyUI API integration service.

Connects to a ComfyUI instance (default: 10.190.0.222:8188) to:
- Queue image generation workflows (text-to-image via SD3.5/SDXL)
- Queue video generation via WanVideoWrapper
- Monitor task progress
- Retrieve generated outputs
"""
import asyncio
import json
import os
import time
from typing import Optional
import httpx
from ..config import settings


class ComfyUIService:
    """Service for interacting with the ComfyUI API for image and video generation."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.comfyui_url).rstrip("/")
        self.client_timeout = 300.0  # 5 minutes for generation tasks
        self.poll_interval = 2.0     # seconds between progress checks

    async def queue_workflow(self, workflow: dict) -> str:
        """Queue a workflow on ComfyUI.

        POST /api/prompt with the workflow JSON.

        Args:
            workflow: Complete ComfyUI workflow JSON dict.

        Returns:
            prompt_id (str) for tracking progress.

        Raises:
            ConnectionError if ComfyUI is unreachable.
            ValueError if the workflow is rejected.
        """
        url = f"{self.base_url}/api/prompt"
        payload = {"prompt": workflow}

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as e:
                raise ValueError(f"ComfyUI rejected workflow: {e.response.text}")
            except httpx.RequestError as e:
                raise ConnectionError(f"ComfyUI unreachable at {self.base_url}: {e}")

        prompt_id = data.get("prompt_id")
        if not prompt_id:
            raise ValueError(f"No prompt_id in ComfyUI response: {data}")
        return prompt_id

    async def get_progress(self, prompt_id: str) -> dict:
        """Get the progress of a queued workflow.

        GET /api/progress?prompt_id=xxx

        Args:
            prompt_id: The prompt ID returned by queue_workflow.

        Returns:
            dict with keys like 'progress' (0-1), 'eta_seconds', 'current_node'.
        """
        url = f"{self.base_url}/api/progress"
        params = {"prompt_id": prompt_id}

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                return {"error": str(e), "progress": 0}

    async def get_history(self, prompt_id: str) -> dict:
        """Get the completed output info for a workflow.

        GET /api/history/{prompt_id}

        Args:
            prompt_id: The prompt ID to check.

        Returns:
            dict with output file paths/URLs, or {"status": "pending"} if not done.
        """
        url = f"{self.base_url}/api/history/{prompt_id}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(url)
                if resp.status_code == 404:
                    return {"status": "pending", "prompt_id": prompt_id}
                resp.raise_for_status()
                data = resp.json()

                # Extract outputs from the history structure
                history = data.get(prompt_id, data)
                outputs = history.get("outputs", {})
                status_info = history.get("status", {})

                result = {
                    "status": status_info.get("status_str", "completed"),
                    "completed": status_info.get("completed", True),
                    "outputs": outputs,
                    "prompt_id": prompt_id,
                }

                # Try to extract file paths
                files = []
                for node_id, node_output in outputs.items():
                    for output_type, output_data in node_output.items():
                        if isinstance(output_data, list):
                            for item in output_data:
                                if isinstance(item, dict) and "filename" in item:
                                    files.append({
                                        "filename": item["filename"],
                                        "type": output_type,
                                        "node_id": node_id,
                                        **item,
                                    })
                result["files"] = files
                return result

            except httpx.RequestError as e:
                return {"error": str(e), "status": "error", "prompt_id": prompt_id}

    async def _wait_for_completion(self, prompt_id: str, timeout: float = 300.0) -> dict:
        """Poll until the workflow completes or timeout is reached.

        Args:
            prompt_id: The prompt ID to wait for.
            timeout: Max seconds to wait.

        Returns:
            The history dict with output info.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            history = await self.get_history(prompt_id)
            if history.get("status") == "completed" or history.get("completed"):
                return history
            if history.get("status") == "error":
                return history
            await asyncio.sleep(self.poll_interval)
        return {"status": "timeout", "prompt_id": prompt_id}

    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        model: str = "sd3.5",
        seed: int = -1,
    ) -> str:
        """Generate an image via ComfyUI text-to-image workflow.

        Args:
            prompt: Text description of the desired image.
            negative_prompt: Things to avoid in the image.
            width: Image width (must be multiple of 8).
            height: Image height (must be multiple of 8).
            model: Model ID ('sd3.5', 'sdxl', 'sd15', etc.).
            seed: Random seed (-1 for random).

        Returns:
            URL/path to the generated image.
        """
        # Build a minimal ComfyUI workflow for text-to-image
        workflow = self._build_t2i_workflow(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            model=model,
            seed=seed,
        )

        prompt_id = await self.queue_workflow(workflow)
        history = await self._wait_for_completion(prompt_id)

        if history.get("status") == "error":
            raise RuntimeError(f"Image generation failed: {history.get('error', 'unknown')}")
        if history.get("status") == "timeout":
            raise TimeoutError(f"Image generation timed out after {self.client_timeout}s")

        # Extract output image URL
        files = history.get("files", [])
        if files:
            # Return a composable URL
            filename = files[0].get("filename", "")
            subfolder = files[0].get("subfolder", "")
            output_type = files[0].get("type", "output")
            return f"{self.base_url}/view?filename={filename}&subfolder={subfolder}&type={output_type}"

        return ""

    async def generate_video_from_images(
        self,
        image_paths: list[str],
        prompt: str,
        motion: str = "slow",
    ) -> str:
        """Generate a video from a sequence of images using WanVideoWrapper.

        Args:
            image_paths: List of paths to input images to animate.
            prompt: Text description of the motion/animation.
            motion: Motion intensity ('slow', 'medium', 'fast').

        Returns:
            URL/path to the generated video.
        """
        # Build a WanVideoWrapper workflow for image-to-video
        workflow = self._build_video_workflow(
            image_paths=image_paths,
            prompt=prompt,
            motion=motion,
        )

        prompt_id = await self.queue_workflow(workflow)
        history = await self._wait_for_completion(prompt_id)

        if history.get("status") == "error":
            raise RuntimeError(f"Video generation failed: {history.get('error', 'unknown')}")
        if history.get("status") == "timeout":
            raise TimeoutError(f"Video generation timed out after {self.client_timeout}s")

        # Extract output video URL
        files = history.get("files", [])
        video_files = [f for f in files if any(ext in f.get("filename", "") for ext in (".mp4", ".webm", ".gif"))]
        if video_files:
            filename = video_files[0].get("filename", "")
            subfolder = video_files[0].get("subfolder", "")
            output_type = video_files[0].get("type", "output")
            return f"{self.base_url}/view?filename={filename}&subfolder={subfolder}&type={output_type}"

        if files:
            filename = files[0].get("filename", "")
            subfolder = files[0].get("subfolder", "")
            output_type = files[0].get("type", "output")
            return f"{self.base_url}/view?filename={filename}&subfolder={subfolder}&type={output_type}"

        return ""

    def _build_t2i_workflow(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        model: str = "sd3.5",
        seed: int = -1,
    ) -> dict:
        """Build a ComfyUI text-to-image workflow JSON.

        This is a template that assumes the standard ComfyUI node naming.
        Node IDs may need adjustment based on the specific ComfyUI instance setup.
        """
        workflow = {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed if seed != -1 else int(time.time()),
                    "steps": 20,
                    "cfg": 7.0,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0],
                },
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": self._get_model_name(model),
                },
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": width,
                    "height": height,
                    "batch_size": 1,
                },
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": prompt,
                    "clip": ["4", 1],
                },
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": negative_prompt or "",
                    "clip": ["4", 1],
                },
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2],
                },
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "video_generate_",
                    "images": ["8", 0],
                },
            },
        }
        return workflow

    def _build_video_workflow(
        self,
        image_paths: list[str],
        prompt: str,
        motion: str = "slow",
    ) -> dict:
        """Build a WanVideoWrapper workflow for video generation from images.

        This assumes WanVideoWrapper nodes are installed in ComfyUI.
        Node IDs may need adjustment.
        """
        # Motion strength mapping
        motion_map = {"slow": 0.3, "medium": 0.6, "fast": 0.9}
        motion_strength = motion_map.get(motion, 0.5)

        workflow = {
            "1": {
                "class_type": "WanVideoWrapper",
                "inputs": {
                    "image": self._load_images_node(image_paths),
                    "prompt": prompt,
                    "motion_strength": motion_strength,
                    "num_frames": 49,
                    "fps": 8,
                    "guidance_scale": 5.0,
                    "num_inference_steps": 30,
                },
            },
            "2": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["1", 0],
                    "vae": ["3", 2],
                },
            },
            "3": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "wan2.1_i2v_480p.safetensors",
                },
            },
            "4": {
                "class_type": "VideoCombine",
                "inputs": {
                    "frame_rate": 8,
                    "loop_count": 1,
                    "filename_prefix": "video_generate_wan_",
                    "images": ["2", 0],
                },
            },
        }
        return workflow

    @staticmethod
    def _load_images_node(image_paths: list[str]) -> list:
        """Create a LoadImage node reference for each input image.

        In a real workflow, you'd use individual LoadImage nodes for each image.
        This creates a structure that can be referenced.
        """
        # For simplicity, return a reference to a single LoadImage node.
        # In a multi-image scenario, you'd chain multiple LoadImage nodes.
        return ["5", 0]

    @staticmethod
    def _get_model_name(model: str) -> str:
        """Map simplified model names to ComfyUI checkpoint filenames."""
        model_map = {
            "sd3.5": "sd3.5_large.safetensors",
            "sd3.5_medium": "sd3.5_medium.safetensors",
            "sdxl": "sd_xl_base_1.0.safetensors",
            "sdxl_turbo": "sd_xl_turbo_1.0.safetensors",
            "sd15": "v1-5-pruned-emaonly.safetensors",
            "sd21": "sd2.1_base.ckpt",
            "flux": "flux1-dev.safetensors",
        }
        return model_map.get(model, "sd3.5_large.safetensors")

    async def check_connectivity(self) -> bool:
        """Check if the ComfyUI API is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/prompts")
                # ComfyUI returns a list/object or an empty array
                return resp.status_code < 500
        except Exception:
            return False


# Singleton
comfyui_service = ComfyUIService()
