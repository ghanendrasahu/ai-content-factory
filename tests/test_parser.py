import pytest

from app.ai.parser import JsonParser


def test_parse_array_from_fenced_json():
    parsed = JsonParser.parse('```json\n[{"start": 1, "end": 2}]\n```')

    assert parsed == [{"start": 1, "end": 2}]


def test_parse_object_from_extra_text():
    parsed = JsonParser.parse_object('prefix {"title": "ok"} suffix')

    assert parsed == {"title": "ok"}


def test_parse_rejects_wrong_shape():
    with pytest.raises(ValueError):
        JsonParser.parse('{"not": "array"}')

    with pytest.raises(ValueError):
        JsonParser.parse_object('[{"not": "object"}]')
