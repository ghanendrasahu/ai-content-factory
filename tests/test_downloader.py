from pathlib import Path

from app.services.download_service import DownloadService


class FakeYoutubeDL:
    def __init__(self, options, output_file: Path):
        self.options = options
        self.output_file = output_file

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def extract_info(self, url, download):
        self.output_file.write_bytes(b"video")
        return {
            "title": "sample",
            "requested_downloads": [{"filepath": str(self.output_file)}],
        }


def test_download_returns_existing_file(monkeypatch, tmp_path):
    output_file = tmp_path / "sample.mp4"

    monkeypatch.setattr(
        "app.services.download_service.yt_dlp.YoutubeDL",
        lambda options: FakeYoutubeDL(options, output_file),
    )

    title, path = DownloadService.download("https://www.youtube.com/watch?v=test")

    assert title == "sample"
    assert Path(path).is_file()
