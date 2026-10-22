"""OAuth authorization helper: consent screen, callback capture, token exchange.

Fully offline - a local server plays the consent screen and the token
endpoint, so the whole flow (including the redirect handling) is verified
without touching Google.
"""

from __future__ import annotations

import json
import sys
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from youtube_authorize import (  # noqa: E402
    SCOPE,
    build_auth_url,
    run_flow,
    write_env,
)

from app.config import settings  # noqa: E402


class _GoogleStub(BaseHTTPRequestHandler):
    """Consent screen + token endpoint."""

    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        # The consent screen: redirect back to the app with a code.
        from urllib.parse import parse_qs, urlparse

        params = parse_qs(urlparse(self.path).query)
        redirect_uri = params["redirect_uri"][0]
        target = f"{redirect_uri}?code=test-authorization-code&state=xyz"
        self.send_response(302)
        self.send_header("Location", target)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")

        if "grant_type=authorization_code" not in body:
            self._json(400, {"error": "invalid_request"})
            return

        self._json(
            200,
            {
                "access_token": "ya29.stub-access",
                "refresh_token": "1//stub-refresh-token",
                "expires_in": 3600,
            },
        )


@pytest.fixture()
def google_stub():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _GoogleStub)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    base = f"http://127.0.0.1:{server.server_address[1]}"
    original = settings.YOUTUBE_API_BASE_URL
    settings.YOUTUBE_API_BASE_URL = base
    try:
        yield base
    finally:
        settings.YOUTUBE_API_BASE_URL = original
        server.shutdown()
        server.server_close()


def _follow(url: str) -> None:
    """Stand in for the browser: follow the redirect to the callback."""
    with urllib.request.urlopen(url, timeout=10) as response:
        response.read()


def test_auth_url_carries_the_offline_and_scope_parameters():
    url = build_auth_url("cid", "http://127.0.0.1:1234/cb", "https://auth.test")

    assert "client_id=cid" in url
    assert "access_type=offline" in url
    assert "prompt=consent" in url
    assert SCOPE.replace(":", "%3A").replace("/", "%2F") in url
    assert url.startswith("https://auth.test?")


def test_flow_returns_a_refresh_token(google_stub, tmp_path):
    env_file = tmp_path / ".env"

    token = run_flow(
        "cid",
        "secret",
        auth_url=f"{google_stub}/authorize",
        env_file=env_file,
        write=True,
        open_url=_follow,
        timeout_seconds=20,
    )

    assert token == "1//stub-refresh-token"
    # the credentials landed in the env file
    content = env_file.read_text(encoding="utf-8")
    assert "YOUTUBE_CLIENT_ID=cid" in content
    assert "YOUTUBE_REFRESH_TOKEN=1//stub-refresh-token" in content


def test_write_env_replaces_existing_values(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        'GROQ_API_KEY="abc"\nYOUTUBE_CLIENT_ID="old"\n', encoding="utf-8"
    )

    write_env(env_file, "new-id", "new-secret", "new-token")

    content = env_file.read_text(encoding="utf-8")
    assert 'GROQ_API_KEY="abc"' in content
    assert "YOUTUBE_CLIENT_ID=new-id" in content
    assert "YOUTUBE_CLIENT_SECRET=new-secret" in content
    assert "YOUTUBE_REFRESH_TOKEN=new-token" in content
    assert "old" not in content


def test_flow_times_out_without_a_redirect(google_stub):
    with pytest.raises(TimeoutError):
        run_flow(
            "cid",
            "secret",
            auth_url=f"{google_stub}/authorize",
            open_url=lambda url: None,
            timeout_seconds=1,
        )
