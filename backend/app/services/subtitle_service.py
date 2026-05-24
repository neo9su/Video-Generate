"""Subtitle generation service."""
from typing import List, Dict


class SubtitleService:
    async def generate_subtitles(self, script: str) -> List[Dict]:
        """Generate subtitle entries from a script."""
        # TODO: implement subtitle generation with timestamp alignment
        return [{"start": 0, "end": 5, "text": "Sample subtitle"}]
