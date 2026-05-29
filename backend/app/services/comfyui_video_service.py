"""Video generation service using local ComfyUI + Sulphur 2 (LTX-Video 2.3 GGUF).

Runs on GPU server (10.190.0.222) with RTX 3090 24GB.
Uses ComfyUI HTTP API to submit workflows and poll for completion.

Model: Sulphur 2 GGUF Q5_K_M (16GB, BF16 dequant)
Modes: T2V (text-to-video) and I2V (image-to-video)

Cost: FREE (local inference)
Duration: Up to ~8 seconds per clip (VRAM limited)
Resolution: 768x512

Confirmed working parameters:
  - I2V: euler sampler, 20 steps, LTXVScheduler, strength=0.6-0.8, NO distill LoRA
  - T2V: euler sampler, 20 steps, LTXVScheduler (lower quality, use I2V when possible)
"""
import asyncio
import json
import os
import time
import uuid
from typing import Optional

import httpx

from ..config import settings
from .prompt_enhancer_service import prompt_enhancer_service


class ComfyUIVideoService:
    """Generate video clips using local ComfyUI + Sulphur 2 GGUF model."""

    COMFYUI_HOST = "10.190.0.222"
    COMFYUI_PORT = 8188
    BASE_URL = f"http://{COMFYUI_HOST}:{COMFYUI_PORT}"

    # Model config
    GGUF_MODEL = "sulphur_dev-Q5_K_M.gguf"
    CHECKPOINT = "sulphur_dev_fp8mixed.safetensors"  # For VAE + text encoder
    TEXT_ENCODER = "gemma_3_12B_it_fp4_mixed.safetensors"

    # Generation defaults
    DEFAULT_WIDTH = 768
    DEFAULT_HEIGHT = 512
    DEFAULT_FRAMES = 97  # ~4 seconds at 24fps
    DEFAULT_FPS = 24
    DEFAULT_STEPS = 20
    DEFAULT_I2V_STRENGTH = 0.65  # Balance between fidelity and motion

    # Poll config
    MAX_POLL_TIME = 600  # 10 minutes
    POLL_INTERVAL = 5

    def __init__(self):
        self.client_id = str(uuid.uuid4())

    def _build_t2v_workflow(
        self,
        prompt: str,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        frames: int = DEFAULT_FRAMES,
        seed: int = -1,
        negative_prompt: str = "",
    ) -> dict:
        """Build T2V workflow using GGUF model."""
        actual_seed = seed if seed >= 0 else int(time.time()) % (2**32)
        neg = negative_prompt or "ugly, blurry, distorted, watermark, text, cartoon"

        return {
            "1": {"class_type": "GGUFLoaderKJ", "inputs": {
                "model_name": self.GGUF_MODEL, "extra_model_name": "none",
                "dequant_dtype": "bfloat16", "patch_dtype": "bfloat16",
                "patch_on_device": False, "enable_fp16_accumulation": False,
                "attention_override": "sdpa"
            }},
            "16": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": self.CHECKPOINT}},
            "2": {"class_type": "LTXAVTextEncoderLoader", "inputs": {
                "text_encoder": self.TEXT_ENCODER, "ckpt_name": self.CHECKPOINT, "device": "default"
            }},
            "3": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
            "4": {"class_type": "CLIPTextEncode", "inputs": {"text": neg, "clip": ["2", 0]}},
            "5": {"class_type": "LTXVConditioning", "inputs": {
                "positive": ["3", 0], "negative": ["4", 0], "frame_rate": self.DEFAULT_FPS
            }},
            "6": {"class_type": "EmptyLTXVLatentVideo", "inputs": {
                "width": width, "height": height, "length": frames, "batch_size": 1
            }},
            "7": {"class_type": "LTXVScheduler", "inputs": {
                "steps": self.DEFAULT_STEPS, "max_shift": 2.05, "base_shift": 0.95,
                "stretch": True, "terminal": 0.1, "latent": ["6", 0]
            }},
            "8": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
            "9": {"class_type": "RandomNoise", "inputs": {"noise_seed": actual_seed}},
            "10": {"class_type": "CFGGuider", "inputs": {
                "model": ["1", 0], "positive": ["5", 0], "negative": ["5", 1], "cfg": 1.0
            }},
            "11": {"class_type": "SamplerCustomAdvanced", "inputs": {
                "noise": ["9", 0], "guider": ["10", 0], "sampler": ["8", 0],
                "sigmas": ["7", 0], "latent_image": ["6", 0]
            }},
            "12": {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["16", 2]}},
            "13": {"class_type": "CreateVideo", "inputs": {"images": ["12", 0], "fps": self.DEFAULT_FPS}},
            "14": {"class_type": "SaveVideo", "inputs": {
                "video": ["13", 0], "filename_prefix": "video_gen/t2v",
                "format": "auto", "codec": "auto"
            }}
        }

    def _build_i2v_workflow(
        self,
        prompt: str,
        image_name: str,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        frames: int = DEFAULT_FRAMES,
        seed: int = -1,
        negative_prompt: str = "",
        strength: float = DEFAULT_I2V_STRENGTH,
    ) -> dict:
        """Build I2V workflow using GGUF model + reference image."""
        actual_seed = seed if seed >= 0 else int(time.time()) % (2**32)
        neg = negative_prompt or "ugly, blurry, distorted, watermark, text, cartoon"

        return {
            "1": {"class_type": "GGUFLoaderKJ", "inputs": {
                "model_name": self.GGUF_MODEL, "extra_model_name": "none",
                "dequant_dtype": "bfloat16", "patch_dtype": "bfloat16",
                "patch_on_device": False, "enable_fp16_accumulation": False,
                "attention_override": "sdpa"
            }},
            "16": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": self.CHECKPOINT}},
            "2": {"class_type": "LTXAVTextEncoderLoader", "inputs": {
                "text_encoder": self.TEXT_ENCODER, "ckpt_name": self.CHECKPOINT, "device": "default"
            }},
            "20": {"class_type": "LoadImage", "inputs": {"image": image_name}},
            "3": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
            "4": {"class_type": "CLIPTextEncode", "inputs": {"text": neg, "clip": ["2", 0]}},
            "5": {"class_type": "LTXVConditioning", "inputs": {
                "positive": ["3", 0], "negative": ["4", 0], "frame_rate": self.DEFAULT_FPS
            }},
            "21": {"class_type": "LTXVImgToVideo", "inputs": {
                "positive": ["5", 0], "negative": ["5", 1], "vae": ["16", 2],
                "image": ["20", 0], "width": width, "height": height,
                "length": frames, "batch_size": 1, "strength": strength
            }},
            "7": {"class_type": "LTXVScheduler", "inputs": {
                "steps": self.DEFAULT_STEPS, "max_shift": 2.05, "base_shift": 0.95,
                "stretch": True, "terminal": 0.1, "latent": ["21", 2]
            }},
            "8": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
            "9": {"class_type": "RandomNoise", "inputs": {"noise_seed": actual_seed}},
            "10": {"class_type": "CFGGuider", "inputs": {
                "model": ["1", 0], "positive": ["21", 0], "negative": ["21", 1], "cfg": 1.0
            }},
            "11": {"class_type": "SamplerCustomAdvanced", "inputs": {
                "noise": ["9", 0], "guider": ["10", 0], "sampler": ["8", 0],
                "sigmas": ["7", 0], "latent_image": ["21", 2]
            }},
            "12": {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["16", 2]}},
            "13": {"class_type": "CreateVideo", "inputs": {"images": ["12", 0], "fps": self.DEFAULT_FPS}},
            "14": {"class_type": "SaveVideo", "inputs": {
                "video": ["13", 0], "filename_prefix": "video_gen/i2v",
                "format": "auto", "codec": "auto"
            }}
        }

    async def _upload_image(self, image_path: str) -> str:
        """Upload image to ComfyUI input folder. Returns filename."""
        filename = f"vg_{int(time.time())}_{os.path.basename(image_path)}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            with open(image_path, "rb") as f:
                files = {"image": (filename, f, "image/png")}
                resp = await client.post(
                    f"{self.BASE_URL}/upload/image",
                    files=files,
                    data={"overwrite": "true"},
                )
            if resp.status_code != 200:
                raise RuntimeError(f"ComfyUI image upload failed: {resp.status_code} {resp.text[:200]}")
            return resp.json().get("name", filename)

    async def _queue_prompt(self, workflow: dict) -> str:
        """Submit workflow to ComfyUI. Returns prompt_id."""
        payload = {"prompt": workflow, "client_id": self.client_id}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self.BASE_URL}/prompt", json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"ComfyUI queue failed ({resp.status_code}): {resp.text[:500]}")
            prompt_id = resp.json().get("prompt_id")
            if not prompt_id:
                raise RuntimeError(f"ComfyUI: no prompt_id: {resp.text[:200]}")
            return prompt_id

    async def _poll_completion(self, prompt_id: str) -> dict:
        """Poll until prompt completes. Returns history entry."""
        start_time = time.time()
        async with httpx.AsyncClient(timeout=30.0) as client:
            while (time.time() - start_time) < self.MAX_POLL_TIME:
                await asyncio.sleep(self.POLL_INTERVAL)
                resp = await client.get(f"{self.BASE_URL}/history/{prompt_id}")
                if resp.status_code != 200:
                    continue
                history = resp.json()
                if prompt_id not in history:
                    elapsed = int(time.time() - start_time)
                    print(f"[ComfyUI] Generating... ({elapsed}s)")
                    continue
                entry = history[prompt_id]
                status = entry.get("status", {})
                if status.get("completed"):
                    return entry
                elif status.get("status_str") == "error":
                    messages = status.get("messages", [])
                    err_msg = "Unknown error"
                    for msg in messages:
                        if isinstance(msg, list) and len(msg) > 1 and isinstance(msg[1], dict):
                            if "exception_message" in msg[1]:
                                err_msg = msg[1]["exception_message"][:300]
                                break
                    raise RuntimeError(f"ComfyUI generation failed: {err_msg}")
        raise TimeoutError(f"ComfyUI timed out after {self.MAX_POLL_TIME}s for {prompt_id}")

    async def _download_output(self, history_entry: dict, output_path: str) -> str:
        """Download generated video from ComfyUI output."""
        outputs = history_entry.get("outputs", {})
        for node_id, node_output in outputs.items():
            for vtype in ["videos", "images"]:
                if vtype in node_output:
                    for item in node_output[vtype]:
                        filename = item.get("filename", "")
                        if not filename:
                            continue
                        subfolder = item.get("subfolder", "")
                        file_type = item.get("type", "output")
                        params = {"filename": filename, "subfolder": subfolder, "type": file_type}
                        async with httpx.AsyncClient(timeout=120.0) as client:
                            resp = await client.get(f"{self.BASE_URL}/view", params=params)
                            if resp.status_code == 200:
                                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                                with open(output_path, "wb") as f:
                                    f.write(resp.content)
                                return output_path
        raise RuntimeError("ComfyUI: no output found in history entry")

    async def text_to_video(
        self,
        prompt: str,
        output_path: str,
        image_size: str = "768x512",
        negative_prompt: str = "",
        seed: int = -1,
        frames: int = None,
        enhance_prompt: bool = True,
    ) -> str:
        """Generate video from text prompt (T2V). Compatible with SiliconFlow interface."""
        if "x" in image_size:
            parts = image_size.split("x")
            width, height = int(parts[0]), int(parts[1])
        else:
            width, height = self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT

        # Enhance prompt for better video quality
        final_prompt = prompt
        if enhance_prompt:
            final_prompt = await prompt_enhancer_service.enhance(prompt)

        num_frames = frames or self.DEFAULT_FRAMES
        workflow = self._build_t2v_workflow(
            prompt=final_prompt, width=width, height=height,
            frames=num_frames, seed=seed, negative_prompt=negative_prompt,
        )

        print(f"[ComfyUI] T2V: {width}x{height}, {num_frames} frames, 20 steps")
        prompt_id = await self._queue_prompt(workflow)
        print(f"[ComfyUI] Queued: {prompt_id}")
        history = await self._poll_completion(prompt_id)
        result = await self._download_output(history, output_path)
        print(f"[ComfyUI] Saved {os.path.getsize(result)/1024:.0f}KB to {result}")
        return result

    async def image_to_video(
        self,
        prompt: str,
        image_path: str,
        output_path: str,
        image_size: str = "768x512",
        negative_prompt: str = "",
        seed: int = -1,
        frames: int = None,
        strength: float = None,
        enhance_prompt: bool = True,
    ) -> str:
        """Generate video from image + text (I2V). Compatible with SiliconFlow interface."""
        if "x" in image_size:
            parts = image_size.split("x")
            width, height = int(parts[0]), int(parts[1])
        else:
            width, height = self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT

        # Enhance prompt for I2V (focus on motion)
        final_prompt = prompt
        if enhance_prompt:
            final_prompt = await prompt_enhancer_service.enhance_for_i2v(prompt)

        # Upload image to ComfyUI
        uploaded_name = await self._upload_image(image_path)
        num_frames = frames or self.DEFAULT_FRAMES
        i2v_strength = strength or self.DEFAULT_I2V_STRENGTH

        workflow = self._build_i2v_workflow(
            prompt=final_prompt, image_name=uploaded_name,
            width=width, height=height, frames=num_frames,
            seed=seed, negative_prompt=negative_prompt, strength=i2v_strength,
        )

        print(f"[ComfyUI] I2V: {width}x{height}, {num_frames} frames, strength={i2v_strength}")
        prompt_id = await self._queue_prompt(workflow)
        print(f"[ComfyUI] Queued: {prompt_id}")
        history = await self._poll_completion(prompt_id)
        result = await self._download_output(history, output_path)
        print(f"[ComfyUI] Saved {os.path.getsize(result)/1024:.0f}KB to {result}")
        return result

    async def generate_scenes_video(
        self,
        scenes: list[dict],
        output_dir: str,
        task_id: str = "",
        image_paths: Optional[list[str]] = None,
    ) -> list[str]:
        """Generate video clips for storyboard scenes. Same interface as SiliconFlow service."""
        videos_dir = os.path.join(output_dir, "video_clips")
        os.makedirs(videos_dir, exist_ok=True)

        video_paths = []
        for i, scene in enumerate(scenes):
            scene_num = scene.get("scene_number", i + 1)
            prompt = scene.get("visual_prompt") or scene.get("visual_description", "")
            motion = scene.get("motion_description", "")
            video_prompt = f"{prompt}. {motion}" if motion else prompt

            output_path = os.path.join(videos_dir, f"scene_{scene_num:04d}.mp4")

            has_image = (
                image_paths and i < len(image_paths)
                and image_paths[i] and os.path.exists(image_paths[i])
            )

            try:
                if has_image:
                    print(f"[ComfyUI] Scene {scene_num}: I2V with reference image")
                    await self.image_to_video(
                        prompt=video_prompt,
                        image_path=image_paths[i],
                        output_path=output_path,
                        strength=0.7,  # Product scenes: moderate motion
                    )
                else:
                    print(f"[ComfyUI] Scene {scene_num}: T2V (no reference image)")
                    await self.text_to_video(
                        prompt=video_prompt,
                        output_path=output_path,
                    )
                video_paths.append(output_path)
            except Exception as e:
                print(f"[ComfyUI] Scene {scene_num} FAILED: {e}")
                video_paths.append("")

        return video_paths

    async def check_connectivity(self) -> bool:
        """Check if ComfyUI is running."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.BASE_URL}/system_stats")
                return resp.status_code == 200
        except Exception:
            return False

    async def check_balance(self) -> float:
        """Return infinity since local inference is free."""
        return float("inf")


# Singleton
comfyui_video_service = ComfyUIVideoService()
