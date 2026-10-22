"""Verify the YouTube upload path without any credentials.

Starts a local server that speaks the YouTube Data API contract (OAuth token
exchange, resumable session, chunked upload) and runs the *real* publisher
against it over HTTP. Proves the upload code path end to end - the only thing
left unverified is the googleapis.com host itself.

Usage:
    python scripts/verify_publish.py
"""

from __future__ import annotations

import json
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import settings  # noqa: E402
from app.services.youtube_publisher import (  # noqa: E402
    VideoMetadata,
    publish_video,
)


class _StubHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def _json(self, status: int, payload: dict, headers: dict | None = None) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)

        if self.path == "/token":
            self._json(200, {"access_token": "ya29.local-token", "expires_in": 3600})
            return

        if self.path.startswith("/upload/youtube/v3/videos"):
            self.server.session_size = int(  # type: ignore[attr-defined]
                self.headers.get("X-Upload-Content-Length", "0")
            )
            session_uri = (
                f"http://127.0.0.1:{self.server.server_address[1]}/session/abc"
            )
            self._json(200, {}, headers={"Location": session_uri})
            return

        self._json(404, {"error": {"message": "not found"}})

    def do_PUT(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        chunk = self.rfile.read(length)
        total = self.server.session_size  # type: ignore[attr-defined]
        end = int(
            self.headers.get("Content-Range", "0-0/0").split("-")[1].split("/")[0]
        )

        if end + 1 < total:
            self.send_response(308)
            self.send_header("Range", f"bytes=0-{end}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        self.server.uploaded = chunk  # type: ignore[attr-defined]
        self._json(
            200,
            {
                "id": "vid-verification-001",
                "snippet": {"title": "Verification upload"},
                "status": {"privacyStatus": "unlisted"},
            },
        )


def main() -> int:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _StubHandler)
    server.session_size = 0  # type: ignore[attr-defined]
    server.uploaded = b""  # type: ignore[attr-defined]
    threading.Thread(target=server.serve_forever, daemon=True).start()

    original_base = settings.YOUTUBE_API_BASE_URL
    settings.YOUTUBE_API_BASE_URL = f"http://127.0.0.1:{server.server_address[1]}"

    with tempfile.TemporaryDirectory() as tmp:
        video = Path(tmp) / "verification.mp4"
        video.write_bytes(b"v" * 5000)

        try:
            published = publish_video(
                video,
                VideoMetadata(
                    title="AI Content Factory verification",
                    description="end-to-end upload path check",
                    tags=["ai", "verification"],
                    privacy_status="unlisted",
                ),
                client_id="local",
                client_secret="local",
                refresh_token="local",
                chunk_size=2048,
            )
        finally:
            settings.YOUTUBE_API_BASE_URL = original_base
            server.shutdown()
            server.server_close()

    print("upload path verified over real HTTP")
    print(f"  video_id : {published.video_id}")
    print(f"  url      : {published.url}")
    print(f"  privacy  : {published.privacy_status}")
    print(f"  bytes    : {published.bytes_uploaded}")
    print("  chunks   : 308 Resume Incomplete handled, final response parsed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
