"""Image generation service (ComfyUI integration)."""
from ..config import settings


class ImageService:
    def __init__(self):
        self.comfyui_url = settings.comfyui_url

    async def generate_image(self, prompt: str) -> str:
        """Generate an image using ComfyUI."""
        # TODO: implement ComfyUI API call
        return f"/data/uploads/generated_image_{id(self)}.png"
