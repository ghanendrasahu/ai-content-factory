from pathlib import Path

import ffmpeg

from app.config import settings
from app.core.paths import OUTPUT_DIR, ensure_directories
from app.logger import logger


class SubtitleService:
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
