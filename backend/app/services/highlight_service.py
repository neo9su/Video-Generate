"""Advanced subtitle generation with highlight word detection and animated ASS subtitles.

Supports SRT and ASS subtitle formats with TikTok/抖音 style dynamic animations:
- Highlight word detection (marketing keywords, power words, CTAs)
- Scale animations, color changes, glow effects
- Semi-transparent stroke backgrounds
- Dynamic position changes for fast cuts
"""
import os
import re
from typing import Optional


class HighlightService:
    """Service for generating SRT and ASS subtitles with animated highlight effects."""

    # Marketing power words for highlight detection (Chinese + English)
    POWER_WORDS_ZH = [
        "限时", "免费", "独家", "新款", "爆款", "热卖", "特价", "打折",
        "优惠", "赠品", "秒杀", "抢购", "首发", "推荐", "必备", "神器",
        "爆款", "网红", "明星", "同款", "限量", "升级", "全新", "超值",
        "立刻", "马上", "现在", "今日", "最后", "机会", "错过", "绝对",
        "保证", "承诺", "效果", "显著", "明显", "快速", "简单", "轻松",
        "省钱", "赚钱", "划算", "超强", "顶级", "最高", "最佳", "首选",
    ]

    POWER_WORDS_EN = [
        "free", "exclusive", "limited", "new", "hot", "sale", "deal", "save",
        "now", "today", "instant", "guaranteed", "proven", "results", "easy",
        "fast", "simple", "best", "top", "premium", "ultimate", "amazing",
        "incredible", "bonus", "extra", "special", "offer", "discount",
        "bargain", "must-have", "trending", "viral", "popular", "award-winning",
        "buy", "shop", "order", "get", "try", "click", "sign up", "subscribe",
        "don't miss", "hurry", "limited time", "while supplies last",
        "act now", "call now", "learn more", "find out", "discover",
    ]

    # ASS style definitions (dynamic colors for TikTok-style subtitles)
    HIGHLIGHT_COLORS = [
        "&H00FF6B00",  # Bright orange
        "&H00FF2D55",  # Hot pink
        "&H00FFD700",  # Gold
        "&H0000FF00",  # Lime green
        "&H0000BFFF",  # Deep sky blue
        "&H00FF1493",  # Deep pink
        "&H00FF4500",  # Orange red
        "&H00ADFF2F",  # Green yellow
    ]

    def __init__(self):
        self._check_connectivity()

    def _check_connectivity(self):
        """Ensure required Python modules are available (no external deps needed)."""
        pass

    def detect_highlight_words(self, text: str, language: str = "zh") -> list[dict]:
        """Detect marketing power words, CTAs, and key selling points in text.

        Args:
            text: The text to analyze (narration or marketing copy).
            language: 'zh' for Chinese, 'en' for English.

        Returns:
            List of dicts: [{word, start_pos, end_pos, importance}]
        """
        if not text:
            return []

        power_words = self.POWER_WORDS_ZH if language == "zh" else self.POWER_WORDS_EN
        text_lower = text.lower() if language == "en" else text
        highlights = []

        for word in power_words:
            search_text = text_lower
            search_word = word.lower() if language == "en" else word

            # Find all occurrences
            start = 0
            while True:
                pos = search_text.find(search_word, start)
                if pos == -1:
                    break
                # Determine importance based on word length and type
                importance = self._calculate_importance(word, language)
                highlights.append({
                    "word": text[pos:pos + len(word)],
                    "start_pos": pos,
                    "end_pos": pos + len(word),
                    "importance": importance,
                })
                start = pos + 1

        # Deduplicate overlapping highlights (keep the longer/more important one)
        if not highlights:
            return []

        # Sort by start position
        highlights.sort(key=lambda h: (h["start_pos"], -h["end_pos"]))

        merged = [highlights[0]]
        for h in highlights[1:]:
            prev = merged[-1]
            if h["start_pos"] < prev["end_pos"]:
                # Overlapping — keep the one with higher importance
                if h["importance"] > prev["importance"]:
                    merged[-1] = h
                elif h["importance"] == prev["importance"] and (h["end_pos"] - h["start_pos"]) > (prev["end_pos"] - prev["start_pos"]):
                    merged[-1] = h
            else:
                merged.append(h)

        return merged

    @staticmethod
    def _calculate_importance(word: str, language: str) -> float:
        """Calculate importance score for a highlight word (0.0 to 1.0)."""
        length_factor = min(len(word) / 6, 1.0) * 0.3

        # Short but punchy words get bonus
        punchy_words = {"free", "new", "hot", "now", "top", "best", "buy",
                        "免费", "新", "送", "省", "抢", "秒"}
        punchy_bonus = 0.2 if word.lower() in punchy_words else 0.0

        # CTA words get extra bonus
        cta_words = {"buy", "shop", "order", "get", "try", "click", "act now", "call now",
                     "购买", "下单", "抢购", "立即", "马上", "立刻"}
        cta_bonus = 0.3 if word.lower() in cta_words else 0.0

        return min(1.0, 0.4 + length_factor + punchy_bonus + cta_bonus)

    def generate_srt(self, scenes: list[dict], language: str = "zh") -> str:
        """Generate SRT subtitle file from storyboard scenes.

        Args:
            scenes: List of scene dicts with 'duration_seconds' and 'narration'.
            language: 'zh' or 'en'.

        Returns:
            SRT format string.
        """
        if not scenes:
            return ""

        srt_lines = []
        subtitle_index = 1
        current_time = 0.0  # running time offset in seconds

        for scene in scenes:
            duration = float(scene.get("duration_seconds", 5.0))
            narration = scene.get("narration", "").strip()
            if not narration:
                current_time += duration
                continue

            # Split long narration into multiple subtitle chunks
            chunks = self._split_narration(narration, duration, language)

            for chunk_text, chunk_duration in chunks:
                start_srt = self._seconds_to_srt(current_time)
                end_srt = self._seconds_to_srt(current_time + chunk_duration)
                srt_lines.append(str(subtitle_index))
                srt_lines.append(f"{start_srt} --> {end_srt}")
                srt_lines.append(chunk_text)
                srt_lines.append("")
                subtitle_index += 1
                current_time += chunk_duration

            # Add a small gap after each scene
            current_time += 0.1

        return "\n".join(srt_lines)

    @staticmethod
    def _split_narration(narration: str, total_duration: float, language: str) -> list[tuple[str, float]]:
        """Split narration into subtitle-sized chunks based on duration.

        Returns:
            List of (text_chunk, duration) tuples.
        """
        if not narration:
            return []

        # Rough estimate: ~5 chars/sec for Chinese, ~12 chars/sec for English
        chars_per_sec = 5 if language == "zh" else 12
        max_chars_per_chunk = int(total_duration * chars_per_sec)

        if len(narration) <= max_chars_per_chunk:
            return [(narration, total_duration)]

        # Split by sentences or commas
        delimiters = re.compile(r'([。！？，、；：.!?,;:\n])')
        parts = delimiters.split(narration)
        chunks = []
        current_chunk = ""
        current_chunk_len = 0

        for part in parts:
            if not part:
                continue
            part_len = len(part)
            if current_chunk_len + part_len > max_chars_per_chunk and current_chunk:
                chunks.append(current_chunk)
                current_chunk = part
                current_chunk_len = part_len
            else:
                current_chunk += part
                current_chunk_len += part_len

        if current_chunk:
            chunks.append(current_chunk)

        # Distribute duration evenly among chunks
        chunk_duration = total_duration / len(chunks)
        return [(chunk.strip(), chunk_duration) for chunk in chunks if chunk.strip()]

    @staticmethod
    def _seconds_to_srt(seconds: float) -> str:
        """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        millisecs = int((secs - int(secs)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{int(secs):02d},{millisecs:03d}"

    def generate_ass_with_highlights(
        self,
        scenes: list[dict],
        highlights: Optional[list[dict]] = None,
        language: str = "zh",
    ) -> str:
        """Generate ASS subtitle file with highlight word animations.

        Features:
        - Highlight word scale-up and color change animation
        - Semi-transparent stroke/background effects
        - Dynamic position changes
        - TikTok-style timing (fast cuts emphasized)

        Args:
            scenes: List of scene dicts with 'duration_seconds', 'narration'.
            highlights: Optional pre-detected highlights; auto-detected if None.
            language: 'zh' or 'en'.

        Returns:
            ASS format string.
        """
        if not scenes:
            return self._empty_ass()

        # Auto-detect highlights if not provided
        if highlights is None:
            all_text = " ".join(s.get("narration", "") for s in scenes if s.get("narration"))
            highlights = self.detect_highlight_words(all_text, language)

        ass_lines = []
        ass_lines.append("[Script Info]")
        ass_lines.append("Title: Video-Generate Subtitles")
        ass_lines.append("ScriptType: v4.00+")
        ass_lines.append("Collisions: Normal")
        ass_lines.append("PlayResX: 1080")
        ass_lines.append("PlayResY: 1920")
        ass_lines.append("Timer: 100.0000")
        ass_lines.append("WrapStyle: 0")
        ass_lines.append("ScaledBorderAndShadow: yes")
        ass_lines.append("")

        # Style definitions
        ass_lines.append("[V4+ Styles]")
        ass_lines.append("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
                         "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
                         "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
                         "Alignment, MarginL, MarginR, MarginV, Encoding")

        # Main subtitle style
        ass_lines.append(
            "Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H80000000,&H00000000,"
            "-1,0,0,0,100,100,0,0,1,2,1,2,30,30,70,1"
        )
        # Highlight style (bright orange/gold)
        ass_lines.append(
            "Style: Highlight,Arial,54,&H00FF6B00,&H00FFD700,&H00000000,&H00000000,"
            "-1,0,0,0,120,120,2,0,1,2,2,2,30,30,70,1"
        )
        # TikTok style (big bold text with stroke)
        ass_lines.append(
            "Style: TikTok,Arial,64,&H00FFFFFF,&H00FF2D55,&H00FF0000,&H00000000,"
            "-1,0,0,0,110,110,1,0,3,3,3,8,20,20,80,1"
        )
        # CTA/buy-now style (large, striking)
        ass_lines.append(
            "Style: CTA,Arial,72,&H00FF4500,&H00FFD700,&H00800000,&H00000000,"
            "-1,0,0,0,130,130,3,0,1,3,3,5,20,20,120,1"
        )

        ass_lines.append("")

        # Events section
        ass_lines.append("[Events]")
        ass_lines.append("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text")

        subtitle_index = 0
        current_time = 0.0

        for scene_index, scene in enumerate(scenes):
            duration = float(scene.get("duration_seconds", 5.0))
            narration = scene.get("narration", "").strip()
            if not narration:
                current_time += duration
                continue

            # Get highlights applicable to this scene's narration
            scene_highlights = [
                h for h in highlights
                if h["word"] in narration
            ] if highlights else []

            # Determine style for this scene
            is_cta = any(h["importance"] > 0.8 for h in scene_highlights)
            base_style = "CTA" if is_cta else ("TikTok" if duration < 3 else "Default")

            # Split narration into chunks
            chunks = self._split_narration(narration, duration, language)
            for chunk_text, chunk_duration in chunks:
                if not chunk_text.strip():
                    current_time += chunk_duration
                    continue

                start_ass = self._seconds_to_ass(current_time)
                end_ass = self._seconds_to_ass(current_time + chunk_duration)

                # Check if this chunk contains highlight words
                chunk_highlights = [h for h in scene_highlights if h["word"] in chunk_text]
                style_name = base_style

                if chunk_highlights:
                    max_imp = max(h["importance"] for h in chunk_highlights)
                    if max_imp > 0.8:
                        style_name = "CTA"
                    elif max_imp > 0.5:
                        style_name = "Highlight"

                    # Create animation events for individual highlight words
                    anim_events = self.create_ass_animation_events(
                        chunk_text, current_time, chunk_duration, style=style_name
                    )
                    for ae in anim_events:
                        ass_lines.append(ae)
                else:
                    # Normal subtitle event
                    layer = 0
                    ass_lines.append(
                        f"Dialogue: {layer},{start_ass},{end_ass},"
                        f"{style_name},,0,0,0,,{self._escape_ass_text(chunk_text)}"
                    )

                subtitle_index += 1
                current_time += chunk_duration

            current_time += 0.1  # small gap between scenes

        return "\n".join(ass_lines)

    def create_tiktok_style_subtitles(self, scenes: list[dict]) -> str:
        """Create TikTok-style subtitle ASS content: big bold text, dynamic colors, emojis.

        Args:
            scenes: List of scene dicts.

        Returns:
            ASS format string with TikTok styling.
        """
        # Reuse the ASS generator with TikTok style forced
        return self.generate_ass_with_highlights(scenes, language="zh")

    def create_ass_animation_events(
        self,
        text: str,
        start_time: float,
        duration: float,
        style: str = "highlight",
    ) -> list[str]:
        """Create ASS animation events for highlight words within a subtitle.

        Generates separate Dialogue events for each highlighted word with
        animated effects (position changes, scale, color transitions).

        Args:
            text: The subtitle text content.
            start_time: Start time in seconds.
            duration: Duration in seconds.
            style: 'highlight', 'tiktok', or 'cta'.

        Returns:
            List of ASS Dialogue event strings.
        """
        events = []
        detected = self.detect_highlight_words(text, language="zh" if any('\u4e00' <= c <= '\u9fff' for c in text) else "en")

        if not detected:
            return events

        words = text.split()
        char_based = any('\u4e00' <= c <= '\u9fff' for c in text)

        for i, hw in enumerate(detected):
            word = hw["word"]
            importance = hw["importance"]

            # Determine style based on importance
            if importance > 0.8:
                color = self.HIGHLIGHT_COLORS[i % len(self.HIGHLIGHT_COLORS)]
                font_size = 64 + int(importance * 20)
                style_name = "CTA"
                layer = 3
            elif importance > 0.5:
                color = self.HIGHLIGHT_COLORS[(i + 2) % len(self.HIGHLIGHT_COLORS)]
                font_size = 54 + int(importance * 14)
                style_name = "Highlight"
                layer = 2
            else:
                color = self.HIGHLIGHT_COLORS[(i + 4) % len(self.HIGHLIGHT_COLORS)]
                font_size = 48 + int(importance * 10)
                style_name = "Highlight"
                layer = 1

            # Calculate position offset so multiple highlights don't overlap
            total_words = len(words) if not char_based else len(text)
            pos_y = max(500 - (i * 60), 200)

            start_ass = self._seconds_to_ass(start_time)
            end_ass = self._seconds_to_ass(start_time + duration)

            # For very short durations (fast cuts), add a bounce/tremble effect
            if duration < 2.0:
                effect_text = (
                    f"{{\\an2\\pos(540,{pos_y})\\fs{font_size}\\c{color}\\b1}}"
                    f"{{\\t(0,{int(duration * 500)},\\fs{font_size + 10}\\c{self.HIGHLIGHT_COLORS[(i + 3) % len(self.HIGHLIGHT_COLORS)]})}}"
                    f"{self._escape_ass_text(word)}"
                )
            else:
                # Normal animation: scale in and color shift
                effect_text = (
                    f"{{\\an2\\pos(540,{pos_y})\\fs{font_size}\\c{color}\\b1}}"
                    f"{{\\t(50,250,\\fs{font_size + 15}\\c{self.HIGHLIGHT_COLORS[(i + 5) % len(self.HIGHLIGHT_COLORS)]})}}"
                    f"{{\\t(300,{int(duration * 700)},\\c{color})}}"
                    f"{self._escape_ass_text(word)}"
                )

            events.append(
                f"Dialogue: {layer},{start_ass},{end_ass},"
                f"{style_name},,0,0,0,,{effect_text}"
            )

        return events

    @staticmethod
    def _seconds_to_ass(seconds: float) -> str:
        """Convert seconds to ASS timestamp format (H:MM:SS.cc)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        centisecs = int((secs - int(secs)) * 100)
        return f"{hours}:{minutes:02d}:{int(secs):02d}.{centisecs:02d}"

    @staticmethod
    def _escape_ass_text(text: str) -> str:
        """Escape special characters for ASS format."""
        # ASS uses curly braces for override tags, so we need to escape literal ones
        escaped = text.replace("\\", "\\\\")
        escaped = escaped.replace("{", "\\{")
        escaped = escaped.replace("}", "\\}")
        escaped = escaped.replace("|", "\\N")  # newline in ASS
        return escaped

    @staticmethod
    def _empty_ass() -> str:
        """Return a minimal valid ASS file."""
        return (
            "[Script Info]\n"
            "Title: Empty Subtitles\n"
            "ScriptType: v4.00+\n"
            "Collisions: Normal\n"
            "PlayResX: 1080\n"
            "PlayResY: 1920\n"
            "\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding\n"
            "Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H80000000,&H00000000,"
            "-1,0,0,0,100,100,0,0,1,2,1,2,30,30,70,1\n"
            "\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        )

    def check_connectivity(self) -> bool:
        """Check if the service is available (always True — no external deps)."""
        return True


# Singleton
highlight_service = HighlightService()
