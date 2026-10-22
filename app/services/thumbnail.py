"""Thumbnail studio - poster frames composed with Pillow.

The poster is built from a frame of the rendered video (or an AI-generated
background when a provider is configured) and a layout template:

- ``bold_caption`` big centred headline with a translucent band
- ``split``        left aligned block with an accent bar
- ``minimal``      small caption in the corner

Text is wrapped to the safe zone of a vertical Shorts frame so platform UI
never covers the headline.
"""

from __future__ import annotations

import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import ffmpeg
from PIL import Image, ImageDraw, ImageFont

from app.config import settings
from app.core.paths import OUTPUT_DIR, ensure_directories
from app.logger import logger

TEMPLATES = ("bold_caption", "split", "minimal")


@dataclass(frozen=True)
class ThumbnailStyle:
    """Layout + palette of a thumbnail."""

    template: str = "bold_caption"
    accent_color: str = "#FF3B30"
    text_color: str = "#FFFFFF"
    band_opacity: int = 150
    font_scale: float = 1.0
    max_lines: int = 3
    safe_margin_ratio: float = 0.07

    @classmethod
    def from_settings(cls) -> "ThumbnailStyle":
        return cls(
            template=getattr(settings, "THUMBNAIL_TEMPLATE", "bold_caption"),
            accent_color=getattr(settings, "THUMBNAIL_ACCENT_COLOR", "#FF3B30"),
            text_color=getattr(settings, "THUMBNAIL_TEXT_COLOR", "#FFFFFF"),
            font_scale=float(getattr(settings, "THUMBNAIL_FONT_SCALE", 1.0)),
            max_lines=int(getattr(settings, "THUMBNAIL_MAX_LINES", 3)),
        )


def _hex_to_rgba(color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    value = color.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(char * 2 for char in value)
    try:
        red, green, blue = (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))
    except (ValueError, IndexError):
        red, green, blue = 255, 255, 255
    return red, green, blue, alpha


def _load_font(size: int, bold: bool = True) -> Any:
    """Best-effort system font lookup with a safe fallback."""
    candidates: list[Path] = []
    if os.name == "nt":
        candidates = [
            Path("C:/Windows/Fonts/arialbd.ttf"),
            Path("C:/Windows/Fonts/arial.ttf"),
        ]
    else:
        candidates = [
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ]
    for candidate in candidates:
        if candidate.is_file():
            try:
                return ImageFont.truetype(str(candidate), size)
            except OSError:  # pragma: no cover - depends on the host fonts
                continue
    return ImageFont.load_default()


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: Any,
    max_width: int,
    max_lines: int,
) -> list[str]:
    """Wrap text to a pixel width, capped at ``max_lines``."""
    words = str(text or "AI Content Factory").split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if not current or draw.textlength(candidate, font=font) <= max_width:
            current = candidate
            continue
        lines.append(current)
        current = word
        if len(lines) == max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)

    if len(lines) == max_lines and words:
        last = lines[-1]
        while last and draw.textlength(f"{last}...", font=font) > max_width:
            last = last.rsplit(" ", 1)[0] if " " in last else ""
        lines[-1] = f"{last}..." if last else lines[-1]
    return lines or ["AI Content Factory"]


def _gradient_background(width: int, height: int, style: ThumbnailStyle) -> Image.Image:
    """Fallback artwork when no frame (and no AI provider) is available."""
    accent = _hex_to_rgba(style.accent_color)
    base = Image.new("RGB", (width, height), (18, 18, 24))
    draw = ImageDraw.Draw(base)
    for row in range(height):
        ratio = row / max(height - 1, 1)
        draw.line(
            [(0, row), (width, row)],
            fill=(
                int(18 + accent[0] * ratio * 0.55),
                int(18 + accent[1] * ratio * 0.55),
                int(24 + accent[2] * ratio * 0.55),
            ),
        )
    return base


def _fetch_ai_background(prompt: str, style: ThumbnailStyle) -> Image.Image | None:
    """Fetch a generated background from the configured provider (optional)."""
    endpoint = getattr(settings, "THUMBNAIL_AI_ENDPOINT", "")
    if not endpoint:
        return None

    api_key = getattr(settings, "THUMBNAIL_AI_API_KEY", "")
    payload = f'{{"prompt": "{prompt}", "width": {settings.THUMBNAIL_WIDTH}, "height": {settings.THUMBNAIL_HEIGHT}}}'
    request = urllib.request.Request(
        endpoint,
        data=payload.encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {api_key}"} if api_key else {}),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001 - a failed provider must not break rendering
        logger.warning("thumbnail.ai_background_failed error=%s", exc)
        return None

    image_url = body.strip().strip('"')
    if not image_url.startswith("http"):
        logger.warning("thumbnail.ai_background_unexpected_payload")
        return None

    try:
        with urllib.request.urlopen(image_url, timeout=60) as response:
            raw = response.read()
        import io

        return Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        logger.warning("thumbnail.ai_background_download_failed error=%s", exc)
        return None


def _extract_frame(video_path: Path, output_file: Path) -> Path | None:
    """Grab a representative frame with ffmpeg (best effort)."""
    try:
        stream = (
            ffmpeg.input(str(video_path), ss=0.5)
            .filter("scale", settings.THUMBNAIL_WIDTH, settings.THUMBNAIL_HEIGHT)
            .output(str(output_file), vframes=1, format="image2", vcodec="mjpeg")
            .overwrite_output()
        )
        ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
    except Exception as exc:  # noqa: BLE001 - fall back to generated artwork
        logger.warning("thumbnail.frame_extraction_failed error=%s", exc)
        return None
    return output_file if output_file.is_file() else None


def _compose(image: Image.Image, title: str, style: ThumbnailStyle) -> Image.Image:
    """Draw the template (text, band, accent) onto the background."""
    width, height = image.size
    draw = ImageDraw.Draw(image, "RGBA")
    margin = int(width * style.safe_margin_ratio)
    max_width = width - 2 * margin

    base_size = int(height * 0.11 * style.font_scale)
    font = _load_font(base_size, bold=True)
    lines = _wrap_text(draw, title, font, max_width, style.max_lines)
    line_height = int(base_size * 1.18)
    text_block_height = line_height * len(lines)
    text_color = _hex_to_rgba(style.text_color)
    accent = _hex_to_rgba(style.accent_color)

    if style.template == "split":
        bar_width = max(int(width * 0.012), 6)
        draw.rectangle([margin, height // 2 - text_block_height // 2, margin + bar_width,
                        height // 2 + text_block_height // 2], fill=accent)
        x = margin + bar_width + int(width * 0.03)
        y = height // 2 - text_block_height // 2
        for line in lines:
            draw.text((x, y), line, font=font, fill=text_color,
                      stroke_width=max(int(base_size * 0.06), 2), stroke_fill=(0, 0, 0, 220))
            y += line_height
        return image

    if style.template == "minimal":
        y = height - margin - text_block_height
        for line in lines:
            draw.text((margin, y), line, font=font, fill=text_color,
                      stroke_width=max(int(base_size * 0.05), 2), stroke_fill=(0, 0, 0, 200))
            y += line_height
        return image

    # bold_caption (default)
    band_top = height - margin - text_block_height - int(base_size * 0.5)
    band_bottom = height - margin + int(base_size * 0.2)
    draw.rectangle([0, band_top, width, band_bottom], fill=(0, 0, 0, style.band_opacity))
    y = band_top + int(base_size * 0.22)
    for line in lines:
        width_used = draw.textlength(line, font=font)
        x = (width - width_used) / 2
        draw.text((x, y), line, font=font, fill=text_color,
                  stroke_width=max(int(base_size * 0.07), 3), stroke_fill=(0, 0, 0, 235))
        y += line_height

    accent_height = max(int(height * 0.012), 4)
    draw.rectangle(
        [margin, band_bottom, margin + int(width * 0.22), band_bottom + accent_height],
        fill=accent,
    )
    return image


class ThumbnailGenerator:
    """Poster generation for rendered videos."""

    @staticmethod
    def generate(
        video_path: str | None,
        title: str,
        job_id: str,
        style: ThumbnailStyle | None = None,
    ) -> str:
        """Render a thumbnail poster and return its path."""
        ensure_directories()
        resolved_style = style or ThumbnailStyle.from_settings()
        output_file = OUTPUT_DIR / f"{job_id}_thumbnail.jpg"

        background: Image.Image | None = None
        if video_path:
            video_file = Path(video_path)
            if not video_file.is_file():
                raise FileNotFoundError(f"Thumbnail input video not found: {video_file}")
            frame_file = OUTPUT_DIR / f"{job_id}_frame.jpg"
            extracted = _extract_frame(video_file, frame_file)
            if extracted:
                try:
                    background = Image.open(extracted).convert("RGB")
                except OSError as exc:  # pragma: no cover - corrupt frame
                    logger.warning("thumbnail.frame_unreadable error=%s", exc)

        if background is None:
            background = _fetch_ai_background(title, resolved_style)

        if background is None:
            background = _gradient_background(
                settings.THUMBNAIL_WIDTH, settings.THUMBNAIL_HEIGHT, resolved_style
            )

        canvas = background.resize(
            (settings.THUMBNAIL_WIDTH, settings.THUMBNAIL_HEIGHT), Image.LANCZOS
        )
        poster = _compose(canvas, title, resolved_style)
        poster.save(output_file, format="JPEG", quality=92)

        logger.info("thumbnail.generated output=%s template=%s", output_file, resolved_style.template)
        return str(output_file)

    @staticmethod
    def generate_poster(title: str, job_id: str, style: ThumbnailStyle | None = None) -> str:
        """Poster without a source video (AI background or generated artwork)."""
        return ThumbnailGenerator.generate(None, title, job_id, style=style)
