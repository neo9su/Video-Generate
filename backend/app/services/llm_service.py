"""LLM service for script generation."""
from ..config import settings


class LLMService:
    def __init__(self):
        self.api_key = settings.llm_api_key
        self.api_url = settings.llm_api_url
        self.model = settings.llm_model

    async def generate_script(self, prompt: str) -> str:
        """Generate a video script from a text prompt using LLM."""
        # TODO: implement actual LLM API call
        return f"Generated script for: {prompt}"
