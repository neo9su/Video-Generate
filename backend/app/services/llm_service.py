"""LLM service for marketing copy, storyboard, and product analysis."""
from typing import Optional
import httpx
from ..config import settings


class LLMService:
    """Service that calls the external LLM API at 10.190.0.214:8080/v1."""

    def __init__(self):
        self.api_key = settings.llm_api_key
        self.api_url = settings.llm_api_url.rstrip("/")
        self.model = settings.llm_model
        self.complex_model = "claude-sonnet-4-6"
        self.timeout = 120.0

    async def _call(self, messages: list[dict], model: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 4096) -> str:
        """Make a chat completion call to the external LLM API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.api_url}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()

    async def generate_marketing_copy(self, product_description: str, style: str = "professional", platform: str = "tiktok") -> str:
        """Generate marketing copy for a product given a description, style, and target platform."""
        system_prompt = (
            "You are an expert advertising copywriter. Generate compelling marketing copy "
            "for a video advertisement based on the product description, desired style, and target platform. "
            "Return only the marketing copy text, no extra commentary."
        )
        user_prompt = (
            f"Product Description: {product_description}\n"
            f"Style: {style}\n"
            f"Platform: {platform}\n\n"
            "Write a concise, engaging marketing copy suitable for a short video ad."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return await self._call(messages, temperature=0.8, max_tokens=2048)

    async def generate_storyboard(self, marketing_copy: str) -> list[dict]:
        """Generate a storyboard (list of scenes) from marketing copy."""
        system_prompt = (
            "You are a video storyboard director. Based on the provided marketing copy, "
            "generate a structured storyboard as a JSON list of scene objects. "
            "Each scene object must have these keys:\n"
            '  - "scene_number": int,\n'
            '  - "visual_description": str (describe the imagery),\n'
            '  - "duration_seconds": float (2.0 to 8.0),\n'
            '  - "narration": str (voiceover text for this scene),\n'
            '  - "transition": str (e.g., "cut", "fade", "dissolve")\n\n'
            "Return ONLY the JSON array, no markdown formatting or extra text."
        )
        user_prompt = f"Marketing Copy:\n{marketing_copy}\n\nGenerate a 4-6 scene storyboard in JSON array format."
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        result = await self._call(messages, model=self.complex_model, temperature=0.6, max_tokens=4096)
        # Strip any markdown code fences if present
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1] if "\n" in result else result[3:]
            if result.endswith("```"):
                result = result[:-3]
            result = result.strip()
        import json
        try:
            scenes = json.loads(result)
            if isinstance(scenes, dict):
                # Some models wrap in {"scenes": [...]}
                scenes = scenes.get("scenes", scenes.get("storyboard", []))
            return scenes
        except json.JSONDecodeError:
            # Fallback: return a single scene with the raw text
            return [{
                "scene_number": 1,
                "visual_description": result,
                "duration_seconds": 5.0,
                "narration": marketing_copy,
                "transition": "cut",
            }]

    async def analyze_product_images(self, image_urls: list[str]) -> dict:
        """Analyze product images and extract descriptive information."""
        if not image_urls:
            return {"description": "", "key_features": [], "visual_style": "unknown"}
        system_prompt = (
            "You are a product analyst. Analyze the provided product images and return "
            "a JSON object with:\n"
            '  - "description": str (detailed product description),\n'
            '  - "key_features": list[str] (list of visual features),\n'
            '  - "visual_style": str (e.g., "modern", "vintage", "minimalist"),\n'
            '  - "colors": list[str] (dominant colors)\n\n'
            "Return ONLY the JSON object, no extra text."
        )
        image_content = [{"type": "image_url", "image_url": {"url": url}} for url in image_urls]
        user_content = [{"type": "text", "text": "Analyze these product images."}]
        user_content.extend(image_content)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        result = await self._call(messages, model=self.complex_model, temperature=0.3, max_tokens=2048)
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1] if "\n" in result else result[3:]
            if result.endswith("```"):
                result = result[:-3]
            result = result.strip()
        import json
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"description": result, "key_features": [], "visual_style": "unknown"}

    async def check_connectivity(self) -> bool:
        """Check if the LLM API is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.api_url}/models", headers={"Authorization": f"Bearer {self.api_key}"})
                return resp.status_code < 500
        except Exception:
            return False


# Singleton
llm_service = LLMService()
