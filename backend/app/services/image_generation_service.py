"""Image generation service using the SD API server (http://10.190.0.222:7860)."""
import asyncio
import base64
import json
import os
from typing import Optional
import httpx
from ..config import settings


class ImageGenerationService:
    """Generates images from storyboard descriptions using SD API at port 7860.

    The SD server runs realisticVisionV51 model for photorealistic product images.
    """

    def __init__(self):
        self.base_url = settings.sd_api_url.rstrip("/")
        self.api_timeout = 120.0  # 2 min per image

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
        """Generate a single product photography image from text prompt.

        Uses professional product photography-style prompting.
        Supports img2img from a product reference image if provided.

        Args:
            prompt: SD product photography prompt (from storyboard visual_prompt).
            output_path: Where to save the image.
            negative_prompt: Things to avoid (auto-set for product shots if None).
            width, height: Image dimensions.
            steps: Sampling steps (25=balanced product quality).
            cfg_scale: Classifier-free guidance scale.
            product_image_path: Optional path to product reference image for img2img.

        Returns:
            Path to saved image file, or empty string on failure.
        """
        if negative_prompt is None:
            negative_prompt = (
                "nsfw, ugly, deformed, text, watermark, signature, logo, "
                "low quality, blurry, distorted, bad anatomy, extra limbs, "
                "poorly drawn, mutation, mutated, bad proportions, "
                "disfigured, gross, photography, amateur photo"
            )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # SD API payload: txt2img (or img2img if product image provided)
        if product_image_path and os.path.exists(product_image_path):
            with open(product_image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
            payload = {
                "init_images": [img_b64],
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "denoising_strength": 0.75,
                "steps": steps,
                "width": width,
                "height": height,
                "cfg_scale": cfg_scale,
                "batch_size": 1,
                "sampler_name": "Euler a",
            }
        else:
            payload = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "steps": steps,
                "width": width,
                "height": height,
                "cfg_scale": cfg_scale,
                "batch_size": 1,
                "sampler_name": "Euler a",
            }

        async with httpx.AsyncClient(timeout=self.api_timeout) as client:
            try:
                endpoint = f"{self.base_url}/sdapi/v1/img2img" if product_image_path else f"{self.base_url}/sdapi/v1/txt2img"
                resp = await client.post(endpoint, json=payload)
                resp.raise_for_status()
                data = resp.json()
            except httpx.TimeoutException:
                raise TimeoutError(f"SD API timed out after {self.api_timeout}s")
            except httpx.HTTPStatusError as e:
                raise RuntimeError(f"SD API returned {e.response.status_code}: {e.response.text[:200]}")
            except Exception as e:
                raise RuntimeError(f"SD API error: {e}")

        images = data.get("images", [])
        if not images:
            raise RuntimeError("SD API returned no images")

        # Decode and save the first image
        img_bytes = base64.b64decode(images[0])
        with open(output_path, "wb") as f:
            f.write(img_bytes)

        return output_path

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
            product_images: Optional list of product reference image paths (for img2img).

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
                # Use product image for product_hero and cta scenes (img2img)
                ref_image = ""
                if product_images and scene_type in ("product_hero", "cta"):
                    ref_image = product_images[0]

                await self.generate_scene_image(
                    prompt=enhanced_prompt,
                    output_path=output_path,
                    width=768,
                    height=768,
                    steps=25,
                    product_image_path=ref_image,
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
        """Check if SD API is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/")
                return resp.status_code == 200
        except Exception:
            return False


# Singleton
image_gen_service = ImageGenerationService()
