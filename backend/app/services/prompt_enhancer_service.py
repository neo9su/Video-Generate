"""Prompt enhancer for Sulphur 2 / LTX-Video video generation.

Rewrites short video prompts into detailed scene descriptions that
LTX-Video models understand better. Uses existing LLM API.

The enhancement follows the style used by Sulphur 2's community:
- Detailed visual description (camera, lighting, composition)
- Motion/action description
- Quality/style keywords
"""
from typing import Optional
import httpx
from ..config import settings


SYSTEM_PROMPT = """You are a video prompt enhancer for an AI video generation model (LTX-Video / Sulphur 2).

Your job: transform short product/scene descriptions into detailed cinematic video prompts.

Rules:
1. Describe the scene in ONE continuous paragraph (no bullet points)
2. Include: subject, action/motion, camera movement, lighting, environment details
3. Use present tense ("the camera moves", "water splashes")
4. Add quality keywords at the end: "photorealistic, high quality, cinematic"
5. Keep it under 200 words
6. For product videos: emphasize the product's visual features and subtle motion
7. Do NOT include any meta-instructions or explanations, output ONLY the enhanced prompt

Style examples:
- Input: "washing machine spinning"
  Output: "A modern white front-loading washing machine with its circular glass door showing clothes tumbling inside with soapy water and bubbles. The drum rotates steadily as foam builds up against the glass. Warm natural sunlight filters through a nearby window illuminating the clean laundry room. The camera holds a steady medium shot at eye level with a subtle slow push forward. White tiled walls and wooden shelf with folded towels visible in the background. Photorealistic, commercial photography, high quality, sharp details."

- Input: "pouring detergent into machine"
  Output: "A hand gently pours blue liquid detergent from a branded bottle into the detergent drawer of a front-loading washing machine. The viscous blue liquid flows smoothly creating a small pool in the compartment. The camera captures a close-up angle from slightly above. Soft studio lighting with a clean white background. The machine's control panel with glowing digital display visible in the background. Photorealistic, product advertisement, shallow depth of field, high quality."
"""


class PromptEnhancerService:
    """Enhance short prompts into detailed video generation prompts."""

    def __init__(self):
        self.api_key = settings.llm_api_key
        self.api_url = settings.llm_api_url.rstrip("/")
        self.model = settings.llm_model
        self.timeout = 30.0

    async def enhance(self, short_prompt: str, reference_context: str = "") -> str:
        """Enhance a short prompt into a detailed video prompt.

        Args:
            short_prompt: Brief description (e.g. "washing machine spinning")
            reference_context: Optional context about the product/scene

        Returns:
            Enhanced detailed prompt for video generation.
        """
        user_msg = short_prompt
        if reference_context:
            user_msg = f"Product/context: {reference_context}\nScene: {short_prompt}"

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 512,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.api_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    enhanced = data["choices"][0]["message"]["content"].strip()
                    # Remove any quotes that LLM might add
                    if enhanced.startswith('"') and enhanced.endswith('"'):
                        enhanced = enhanced[1:-1]
                    print(f"[PromptEnhancer] {short_prompt[:50]}... → {len(enhanced)} chars")
                    return enhanced
                else:
                    print(f"[PromptEnhancer] LLM error {resp.status_code}, using original")
                    return short_prompt
        except Exception as e:
            print(f"[PromptEnhancer] Failed: {e}, using original")
            return short_prompt

    async def enhance_for_i2v(self, short_prompt: str, motion_hint: str = "") -> str:
        """Enhance prompt specifically for I2V (image-to-video) mode.

        For I2V, focus on MOTION description since the image provides the visual.
        """
        user_msg = f"""For an image-to-video generation: The reference image already shows the scene.
Write a prompt focused on MOTION and ANIMATION to apply to this still image.

Scene: {short_prompt}
{f"Motion hint: {motion_hint}" if motion_hint else ""}

Focus on: what moves, camera motion, how lighting changes. Keep the prompt under 100 words."""

        messages = [
            {"role": "system", "content": "You write concise motion-focused video prompts for image-to-video AI models. Output ONLY the prompt, no explanations."},
            {"role": "user", "content": user_msg},
        ]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 256,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.api_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    enhanced = data["choices"][0]["message"]["content"].strip()
                    if enhanced.startswith('"') and enhanced.endswith('"'):
                        enhanced = enhanced[1:-1]
                    print(f"[PromptEnhancer I2V] → {len(enhanced)} chars")
                    return enhanced
                else:
                    return short_prompt
        except Exception as e:
            print(f"[PromptEnhancer] Failed: {e}")
            return short_prompt


# Singleton
prompt_enhancer_service = PromptEnhancerService()
