"""Image generation service using ComfyUI API (http://10.190.0.222:8188).

Uses ComfyUI's prompt queue API to generate product photography images.
Replaces the old SD WebUI API approach.
"""
import asyncio
import base64
import io
import json
import os
import uuid
from typing import Optional
import httpx
from ..config import settings


# ComfyUI txt2img workflow template
def _build_workflow(prompt: str, negative_prompt: str, width: int, height: int,
                   steps: int, cfg_scale: float, seed: int = -1,
                   checkpoint: str = "dreamshaper_8.safetensors") -> dict:
    """Build a ComfyUI workflow JSON for txt2img."""
    if seed < 0:
        import random
        seed = random.randint(0, 2**32 - 1)

    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint}
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": prompt,
                "clip": ["1", 1]
            }
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": negative_prompt,
                "clip": ["1", 1]
            }
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": 1
            }
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
                "seed": seed,
                "steps": steps,
                "cfg": cfg_scale,
                "sampler_name": "euler_ancestral",
                "scheduler": "normal",
                "denoise": 1.0
            }
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["5", 0],
                "vae": ["1", 2]
            }
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["6", 0],
                "filename_prefix": "api_gen"
            }
        }
    }


class ImageGenerationService:
    """Generates images from storyboard descriptions using ComfyUI API at port 8188.

    Uses dreamshaper_8 model for product photography style images.
    """

    def __init__(self):
        self.base_url = settings.comfyui_url.rstrip("/")
        self.api_timeout = 120.0  # 2 min per image
        self.checkpoint = "dreamshaper_8.safetensors"

    async def generate_scene_image(
        self,
        prompt: str,
        output_path: str,
        negative_prompt: Optional[str] = None,
        width: int = 768,
        height: int = 768,
        steps: int = 25,
        cfg_scale: float = 7.0,
        product_image_path: str = "",
    ) -> str:
        """Generate a single product photography image via ComfyUI.

        Args:
            prompt: SD product photography prompt (from storyboard visual_prompt).
            output_path: Where to save the image.
            negative_prompt: Things to avoid (auto-set for product shots if None).
            width, height: Image dimensions.
            steps: Sampling steps (25=balanced product quality).
            cfg_scale: Classifier-free guidance scale.
            product_image_path: Currently unused (ComfyUI img2img needs different workflow).

        Returns:
            Path to saved image file, or empty string on failure.
        """
        if negative_prompt is None:
            negative_prompt = (
                "nsfw, ugly, deformed, text, watermark, signature, logo, "
                "low quality, blurry, distorted, bad anatomy, extra limbs, "
                "poorly drawn, mutation, mutated, bad proportions, "
                "disfigured, gross, amateur photo"
            )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        workflow = _build_workflow(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            steps=steps,
            cfg_scale=cfg_scale,
            checkpoint=self.checkpoint,
        )

        # Queue the prompt
        client_id = str(uuid.uuid4())
        payload = {"prompt": workflow, "client_id": client_id}

        async with httpx.AsyncClient(timeout=self.api_timeout) as client:
            # Submit workflow
            resp = await client.post(f"{self.base_url}/prompt", json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"ComfyUI queue failed: {resp.status_code} {resp.text[:200]}")
            queue_data = resp.json()
            prompt_id = queue_data.get("prompt_id")
            if not prompt_id:
                raise RuntimeError(f"ComfyUI: no prompt_id: {queue_data}")

            # Poll for completion
            for _ in range(120):  # max 120 seconds
                await asyncio.sleep(1)
                hist_resp = await client.get(f"{self.base_url}/history/{prompt_id}")
                if hist_resp.status_code != 200:
                    continue
                history = hist_resp.json()
                if prompt_id not in history:
                    continue
                entry = history[prompt_id]
                if entry.get("status", {}).get("status_str") == "error":
                    raise RuntimeError(f"ComfyUI generation error: {entry}")
                outputs = entry.get("outputs", {})
                # Find SaveImage node output
                for node_id, node_output in outputs.items():
                    images = node_output.get("images", [])
                    if images:
                        img_info = images[0]
                        filename = img_info["filename"]
                        subfolder = img_info.get("subfolder", "")
                        img_type = img_info.get("type", "output")
                        # Download image
                        params = {"filename": filename, "subfolder": subfolder, "type": img_type}
                        img_resp = await client.get(f"{self.base_url}/view", params=params)
                        if img_resp.status_code == 200:
                            with open(output_path, "wb") as f:
                                f.write(img_resp.content)
                            return output_path
                        raise RuntimeError(f"ComfyUI: failed to download image: {img_resp.status_code}")
                # If outputs is non-empty but no images found, something is wrong
                if outputs:
                    raise RuntimeError(f"ComfyUI: no images in output: {outputs}")

            raise TimeoutError(f"ComfyUI: generation timed out after 120s for prompt_id {prompt_id}")

    async def generate_scenes_batch(
        self,
        scenes: list[dict],
        output_dir: str,
        task_id: str = "",
        product_images: Optional[list[str]] = None,
    ) -> list[str]:
        """Generate images for all scenes in a storyboard.

        Uses each scene's 'visual_prompt' (fallback to 'visual_description')
        with professional product photography enhancement.

        Args:
            scenes: List of scene dicts, each with 'visual_prompt', 'scene_type', 'scene_number'.
            output_dir: Directory to save generated images.
            task_id: Optional task ID for organizing output.
            product_images: Optional list of product reference image paths (for future img2img).

        Returns:
            List of paths to generated images.
        """
        scenes_dir = os.path.join(output_dir, "scenes")
        os.makedirs(scenes_dir, exist_ok=True)

        image_paths = []
        for i, scene in enumerate(scenes):
            # Use visual_prompt if available (richer), fallback to visual_description
            raw_prompt = scene.get("visual_prompt") or scene.get("visual_description", "")
            scene_type = scene.get("scene_type", "product_hero")
            scene_num = scene.get("scene_number", i + 1)

            if not raw_prompt:
                image_paths.append("")
                continue

            output_path = os.path.join(scenes_dir, f"scene_{scene_num:04d}.png")

            try:
                enhanced_prompt = self._enhance_product_prompt(raw_prompt, scene_type)
                await self.generate_scene_image(
                    prompt=enhanced_prompt,
                    output_path=output_path,
                    width=768,
                    height=768,
                    steps=25,
                )
                image_paths.append(output_path)
            except Exception as e:
                print(f"Scene {scene_num} ({scene_type}) image gen failed: {e}")
                image_paths.append("")

        return image_paths

    def _enhance_product_prompt(self, prompt: str, scene_type: str = "product_hero") -> str:
        """Build a professional product photography SD prompt from a scene description.

        Different scene types get different styling for best results.
        """
        style_map = {
            "product_hero": (
                "professional product photography, studio lighting, white seamless background, "
                "soft diffused light, clean minimalist composition, sharp focus, 8k, "
                "commercial advertising, sleek product design, shallow depth of field"
            ),
            "ingredient": (
                "macro photography, scientific visualization, detailed texture, "
                "microscopic detail, sharp focus, studio lighting, clean background, "
                "modern laboratory aesthetic, bio-tech style, high contrast, 8k"
            ),
            "usage": (
                "lifestyle photography, natural lighting, warm atmosphere, authentic moment, "
                "soft focus background, genuine expression, clean composition, "
                "commercial lifestyle, magazine quality, 8k"
            ),
            "comparison": (
                "split composition, clean clinical style, before and after aesthetic, "
                "white background, studio lighting, side by side comparison, "
                "scientific accuracy, clean minimal, 8k"
            ),
            "testimonial": (
                "portrait photography, natural smile, warm lighting, soft focus background, "
                "authentic expression, lifestyle portrait, commercial photography, "
                "genuine emotion, magazine quality, 8k"
            ),
            "cta": (
                "product photography, bold studio lighting, dramatic composition, "
                "clean background, premium product display, commercial advertising, "
                "sharp focus, brand presentation, sleek modern, 8k"
            ),
        }
        style = style_map.get(scene_type, "commercial photography, 8k, sharp focus")
        return f"{prompt}, {style}"

    async def check_connectivity(self) -> bool:
        """Check if ComfyUI API is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/system_stats")
                return resp.status_code == 200
        except Exception:
            return False


# Singleton
image_gen_service = ImageGenerationService()
