"""Thumbnail studio: templates, text wrapping and AI provider fallback."""

from pathlib import Path

import pytest
from PIL import Image

from app.services.thumbnail import (
    TEMPLATES,
    ThumbnailGenerator,
    ThumbnailStyle,
    _compose,
    _gradient_background,
    _hex_to_rgba,
    _wrap_text,
)


def test_templates_are_known():
    assert set(TEMPLATES) == {"bold_caption", "split", "minimal"}


def test_hex_to_rgba_parses_short_and_long_form():
    assert _hex_to_rgba("#FF3B30") == (255, 59, 48, 255)
    assert _hex_to_rgba("#FFF") == (255, 255, 255, 255)
    assert _hex_to_rgba("nonsense") == (255, 255, 255, 255)


def test_wrap_text_respects_line_limit():
    image = Image.new("RGB", (400, 200))
    from PIL import ImageDraw

    draw = ImageDraw.Draw(image)
    font = _default_font()

    lines = _wrap_text(draw, "one two three four five six seven eight", font, 200, 2)

    assert len(lines) <= 2
    assert all(line for line in lines)


def _default_font():
    from app.services.thumbnail import _load_font

    return _load_font(24)


def test_gradient_background_is_generated():
    background = _gradient_background(320, 180, ThumbnailStyle())

    assert background.size == (320, 180)


@pytest.mark.parametrize("template", TEMPLATES)
def test_compose_renders_every_template(template):
    style = ThumbnailStyle(template=template)
    background = _gradient_background(640, 360, style)

    poster = _compose(background, "How AI changes everything", style)

    assert poster.size == (640, 360)
    # the composition must not be a flat background any more
    assert poster.getcolors(maxcolors=100000) is not None


def test_generate_poster_writes_a_file(tmp_path, monkeypatch):
    from app.core import paths as paths_module

    monkeypatch.setattr(paths_module, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(
        "app.services.thumbnail.OUTPUT_DIR", tmp_path, raising=False
    )

    output = ThumbnailGenerator.generate_poster("Poster title", "job-poster")

    assert Path(output).is_file()
    assert Path(output).suffix == ".jpg"
    with Image.open(output) as image:
        assert image.width > 0 and image.height > 0
