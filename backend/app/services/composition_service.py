"""Video composition service — combines all assets into final video."""
from typing import List, Dict


class CompositionService:
    async def compose(
        self,
        video_path: str,
        audio_path: str,
        subtitles: List[Dict],
        output_path: str,
    ) -> str:
        """Combine video, audio, and subtitles into the final video."""
        # TODO: implement FFmpeg-based composition
        return output_path
