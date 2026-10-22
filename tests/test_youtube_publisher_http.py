"""End-to-end verification of the YouTube upload path over real HTTP.

A local server implements the YouTube Data API contract (OAuth token
exchange, resumable session creation, chunked upload with ``308 Resume
Incomplete``, the final resource response and the error paths). The publisher
talks to it with the real urllib transport, so socket I/O, header handling,
``Content-Range`` semantics and response parsing are all exercised - only the
googleapis.com host itself is left out.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.config import settings
from app.services.youtube_publisher import (
    AuthError,
    InvalidRequestError,
    QuotaError,
    UploadError,
    VideoMetadata,
    publish_video,
    refresh_access_token,
)


class _Handler(BaseHTTPRequestHandler):
    """Minimal YouTube-compatible API."""

    protocol_version = "HTTP/1.1"
    server_version = "FakeYouTube/1.0"

    def log_message(self, *args):  # noqa: D102 - silence the test server
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

    def do_POST(self):  # noqa: N802 - BaseHTTPRequestHandler API
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)

        if self.path == "/token":
            form = body.decode("utf-8")
            if "grant_type=refresh_token" not in form:
                self._json(400, {"error": "invalid_request"})
                return
            self._json(200, {"access_token": "ya29.local-token", "expires_in": 3600})
            return

        if self.path.startswith("/upload/youtube/v3/videos"):
            payload = json.loads(body.decode("utf-8"))
            self.server.session_payload = payload  # type: ignore[attr-defined]
            self.server.session_size = int(  # type: ignore[attr-defined]
                self.headers.get("X-Upload-Content-Length", "0")
            )
            session_uri = (
                f"http://127.0.0.1:{self.server.server_address[1]}/session/abc"
            )
            self._json(200, {}, headers={"Location": session_uri})
            return

        self._json(404, {"error": {"message": "not found"}})

    def do_PUT(self):  # noqa: N802 - BaseHTTPRequestHandler API
        length = int(self.headers.get("Content-Length", "0"))
        chunk = self.rfile.read(length)
        content_range = self.headers.get("Content-Range", "")
        self.server.received.append(content_range)  # type: ignore[attr-defined]

        mode = getattr(self.server, "mode", "ok")
        if mode == "quota":
            self._json(
                403, {"error": {"message": "quotaExceeded: daily limit reached"}}
            )
            return
        if mode == "invalid":
            self._json(400, {"error": {"message": "invalidRequest: bad snippet"}})
            return
        if mode == "server_error":
            self._json(503, {"error": {"message": "backendError"}})
            return

        total = self.server.session_size  # type: ignore[attr-defined]
        # bytes <start>-<end>/<total>
        end = int(content_range.split("-")[1].split("/")[0])
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
                "id": "vid-local-123",
                "snippet": {"title": "Local upload", "tags": ["ai"]},
                "status": {"privacyStatus": "unlisted"},
            },
        )


@pytest.fixture()
def api_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    server.received = []  # type: ignore[attr-defined]
    server.mode = "ok"  # type: ignore[attr-defined]
    server.uploaded = b""  # type: ignore[attr-defined]
    server.session_payload = {}  # type: ignore[attr-defined]
    server.session_size = 0  # type: ignore[attr-defined]

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    base = f"http://127.0.0.1:{server.server_address[1]}"
    original = settings.YOUTUBE_API_BASE_URL
    settings.YOUTUBE_API_BASE_URL = base
    try:
        yield server
    finally:
        settings.YOUTUBE_API_BASE_URL = original
        server.shutdown()
        server.server_close()


def _video(tmp_path, size: int = 2048):
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"v" * size)
    return path


def test_token_exchange_over_real_http(api_server):
    token = refresh_access_token("cid", "secret", "refresh")

    assert token == "ya29.local-token"


def test_full_upload_over_real_http(api_server, tmp_path):
    video = _video(tmp_path, size=2048)

    published = publish_video(
        video,
        VideoMetadata(title="Local end to end", tags=["ai"], privacy_status="unlisted"),
        client_id="cid",
        client_secret="secret",
        refresh_token="refresh",
        chunk_size=1024,
    )

    assert published.video_id == "vid-local-123"
    assert published.url == "https://youtu.be/vid-local-123"
    assert published.bytes_uploaded == 2048
    # two chunks were sent, the first one answered with 308
    assert api_server.received == ["bytes 0-1023/2048", "bytes 1024-2047/2048"]
    # the session carried the metadata
    assert api_server.session_payload["snippet"]["title"] == "Local end to end"
    assert api_server.session_payload["status"]["privacyStatus"] == "unlisted"


def test_quota_response_maps_to_quota_error(api_server, tmp_path):
    api_server.mode = "quota"

    with pytest.raises(QuotaError):
        publish_video(
            _video(tmp_path),
            VideoMetadata(title="x"),
            client_id="cid",
            client_secret="secret",
            refresh_token="refresh",
        )


def test_invalid_request_maps_to_invalid_request_error(api_server, tmp_path):
    api_server.mode = "invalid"

    with pytest.raises(InvalidRequestError):
        publish_video(
            _video(tmp_path),
            VideoMetadata(title="x"),
            client_id="cid",
            client_secret="secret",
            refresh_token="refresh",
        )


def test_server_error_maps_to_upload_error(api_server, tmp_path):
    api_server.mode = "server_error"

    with pytest.raises(UploadError):
        publish_video(
            _video(tmp_path),
            VideoMetadata(title="x"),
            client_id="cid",
            client_secret="secret",
            refresh_token="refresh",
        )


def test_bad_credentials_map_to_auth_error(api_server, tmp_path):
    # The stub rejects anything that is not a refresh_token grant.
    with pytest.raises(AuthError):
        refresh_access_token("cid", "secret", "", http=None)
