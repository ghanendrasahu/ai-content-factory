from pathlib import Path

import ffmpeg

from app.config import settings
from app.core.paths import OUTPUT_DIR, ensure_directories
from app.logger import logger


class SubtitleService:
    """Subtitle generation (SRT / WebVTT / styled ASS) and burn-in."""

    @staticmethod
    def generate(
        transcript: list, output_path: str | Path, fmt: str | None = None
    ) -> str:
        """Generate subtitles in the requested format (default from settings)."""
        resolved = (fmt or getattr(settings, "SUBTITLE_FORMAT", "srt")).lower()
        if resolved == "vtt":
            return SubtitleService.generate_vtt(transcript, output_path)
        if resolved == "ass":
            return SubtitleService.generate_ass(transcript, output_path)
        return SubtitleService.generate_srt(transcript, output_path)

    @staticmethod
    def generate_srt(transcript: list, output_path: str | Path) -> str:
        ensure_directories()
        path = Path(output_path)
        if path.parent == Path("."):
            path = OUTPUT_DIR / path
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as handle:
            for index, item in enumerate(transcript or [], start=1):
                text = str(item.get("text", "")).strip()
                if not text:
                    continue
                start = SubtitleService._format_time(float(item.get("start", 0)))
                end = SubtitleService._format_time(float(item.get("end", 0)))
                handle.write(f"{index}\n{start} --> {end}\n{text}\n\n")

        logger.info("subtitles.srt_created path=%s", path)
        return str(path)

    @staticmethod
    def generate_vtt(transcript: list, output_path: str | Path) -> str:
        """WebVTT captions (broadest browser/player support)."""
        ensure_directories()
        path = Path(output_path)
        if path.parent == Path("."):
            path = OUTPUT_DIR / path
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as handle:
            handle.write("WEBVTT\n\n")
            for item in transcript or []:
                text = str(item.get("text", "")).strip()
                if not text:
                    continue
                start = SubtitleService._format_time(
                    float(item.get("start", 0))
                ).replace(",", ".")
                end = SubtitleService._format_time(float(item.get("end", 0))).replace(
                    ",", "."
                )
                handle.write(f"{start} --> {end}\n{text}\n\n")

        logger.info("subtitles.vtt_created path=%s", path)
        return str(path)

    @staticmethod
    def generate_ass(transcript: list, output_path: str | Path) -> str:
        """Styled Advanced SubStation captions (karaoke-ready styling)."""
        ensure_directories()
        path = Path(output_path)
        if path.parent == Path("."):
            path = OUTPUT_DIR / path
        path.parent.mkdir(parents=True, exist_ok=True)

        font_size = int(getattr(settings, "SUBTITLE_FONT_SIZE", 42))
        outline = int(getattr(settings, "SUBTITLE_STYLE_OUTLINE", 2))
        primary = getattr(settings, "SUBTITLE_STYLE_PRIMARY_COLOR", "&H00FFFFFF")
        back = getattr(settings, "SUBTITLE_STYLE_BACKGROUND", "&H80000000")
        margin_v = int(getattr(settings, "SUBTITLE_POSITION_MARGIN", 180))

        header = [
            "[Script Info]",
            "ScriptType: v4.00+",
            "WrapStyle: 2",
            "ScaledBorderAndShadow: yes",
            "YCbCr Matrix: TV.709",
            "",
            "[V4+ Styles]",
            (
                "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
                "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
                "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
                "Alignment, MarginL, MarginR, MarginV, Encoding"
            ),
            (
                f"Style: Default,{getattr(settings, 'SUBTITLE_STYLE_FONT', 'Arial')},{font_size},"
                f"{primary},{primary},&H00000000,{back},-1,0,0,0,100,100,0,0,3,"
                f"{outline},1,2,60,60,{margin_v},1"
            ),
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        ]

        with path.open("w", encoding="utf-8") as handle:
            handle.write("\n".join(header) + "\n")
            for item in transcript or []:
                text = str(item.get("text", "")).strip()
                if not text:
                    continue
                start = SubtitleService._format_time_ass(float(item.get("start", 0)))
                end = SubtitleService._format_time_ass(float(item.get("end", 0)))
                handle.write(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n")

        logger.info("subtitles.ass_created path=%s", path)
        return str(path)

    @staticmethod
    def burn(input_path: str, srt_path: str, output_path: str) -> str:
        input_file = Path(input_path)
        srt_file = Path(srt_path)
        output_file = Path(output_path)

        if not input_file.is_file():
            raise FileNotFoundError(f"Subtitle input video not found: {input_file}")
        if not srt_file.is_file():
            raise FileNotFoundError(f"SRT file not found: {srt_file}")

        output_file.parent.mkdir(parents=True, exist_ok=True)
        style = (
            f"Fontsize={settings.SUBTITLE_FONT_SIZE},"
            "PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,"
            "BackColour=&H99000000,"
            "BorderStyle=4,"
            "Alignment=2,"
            f"MarginV={settings.SUBTITLE_POSITION_MARGIN}"
        )
        escaped_srt = str(srt_file).replace("\\", "/").replace(":", "\\:")

        stream = (
            ffmpeg.input(str(input_file))
            .output(
                str(output_file),
                vf=f"subtitles='{escaped_srt}':force_style='{style}'",
                vcodec=settings.CPU_ENCODER,
                acodec="aac",
                audio_bitrate=settings.AUDIO_BITRATE,
                pix_fmt="yuv420p",
                movflags="+faststart",
            )
            .overwrite_output()
        )
        ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
        logger.info("subtitles.burn_complete output=%s", output_file)
        return str(output_file)

    @staticmethod
    def _format_time(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

    @staticmethod
    def _format_time_ass(seconds: float) -> str:
        """ASS timestamps use ``H:MM:SS.cc`` (centiseconds)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centis = int(round((seconds - int(seconds)) * 100))
        return f"{hours:d}:{minutes:02d}:{secs:02d}.{centis:02d}"
