"""Video composition service."""
from ..config import settings


class VideoService:
    def __init__(self):
        self.comfyui_url = settings.comfyui_url

    async def generate_video(self, image_path: str, prompt: str) -> str:
        """Generate a video from images using ComfyUI."""
        # TODO: implement video generation
        return f"/data/output/generated_video_{id(self)}.mp4"
