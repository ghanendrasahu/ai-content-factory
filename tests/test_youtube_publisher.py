"""YouTube publishing: token refresh, resumable upload, error mapping, dry-run.

Everything runs offline - the HTTP transport is faked, so no network and no
credentials are required.
"""

import json

import pytest

from app.services.youtube_publisher import (
    AuthError,
    HttpResponse,
    InvalidRequestError,
    QuotaError,
    UploadError,
    VideoMetadata,
    build_metadata,
    create_upload_session,
    publish_video,
    refresh_access_token,
    upload_media,
)


class FakeHttpClient:
    """Scripted HTTP transport recording every call."""

    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.calls = []

    def request(self, method, url, *, headers=None, data=None):
        self.calls.append(
            {"method": method, "url": url, "headers": headers or {}, "data": data}
        )
        if not self.responses:
            return HttpResponse(status=200, headers={}, body=b"{}")
        response = self.responses.pop(0)
        if callable(response):
            return response(method, url, headers or {}, data)
        return response


def _token_response(token="ya29.test-token"):
    return HttpResponse(
        status=200,
        headers={"Content-Type": "application/json"},
        body=json.dumps({"access_token": token, "expires_in": 3600}).encode(),
    )


def _session_response(location="https://upload.example/session/abc"):
    return HttpResponse(status=200, headers={"Location": location}, body=b"")


def _video_file(tmp_path, size=10):
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"x" * size)
    return path


# =========================
# TOKEN REFRESH
# =========================
def test_refresh_access_token_returns_token():
    http = FakeHttpClient([_token_response("ya29.abc")])

    token = refresh_access_token("cid", "secret", "refresh", http=http)

    assert token == "ya29.abc"
    call = http.calls[0]
    assert call["method"] == "POST"
    assert "grant_type=refresh_token" in call["data"].decode()
    assert "refresh_token=refresh" in call["data"].decode()


def test_refresh_access_token_invalid_grant_raises_auth_error():
    http = FakeHttpClient(
        [HttpResponse(status=400, headers={}, body=b'{"error": "invalid_grant"}')]
    )

    with pytest.raises(AuthError) as excinfo:
        refresh_access_token("cid", "secret", "stale", http=http)

    assert "re-authorise" in str(excinfo.value)


def test_refresh_access_token_requires_credentials():
    with pytest.raises(AuthError):
        refresh_access_token("", "", "", http=FakeHttpClient())


# =========================
# UPLOAD SESSION
# =========================
def test_create_upload_session_sends_metadata():
    http = FakeHttpClient([_session_response()])
    metadata = VideoMetadata(title="Hello", tags=["ai"], privacy_status="unlisted")

    location = create_upload_session("token", metadata, 1234, http=http)

    assert location == "https://upload.example/session/abc"
    call = http.calls[0]
    assert "uploadType=resumable" in call["url"]
    assert "part=snippet,status" in call["url"]
    assert call["headers"]["X-Upload-Content-Length"] == "1234"
    body = json.loads(call["data"].decode())
    assert body["snippet"]["title"] == "Hello"
    assert body["snippet"]["tags"] == ["ai"]
    assert body["status"]["privacyStatus"] == "unlisted"


def test_create_upload_session_without_location_is_an_error():
    http = FakeHttpClient([HttpResponse(status=200, headers={}, body=b"")])

    with pytest.raises(UploadError):
        create_upload_session("token", VideoMetadata(title="x"), 10, http=http)


# =========================
# MEDIA UPLOAD
# =========================
def test_upload_media_sends_chunked_content_ranges(tmp_path):
    video = _video_file(tmp_path, size=10)
    http = FakeHttpClient(
        [
            HttpResponse(status=308, headers={"Range": "bytes=0-3"}, body=b""),
            HttpResponse(status=308, headers={"Range": "bytes=0-7"}, body=b""),
            HttpResponse(
                status=200,
                headers={},
                body=json.dumps({"id": "vid123"}).encode(),
            ),
        ]
    )

    response = upload_media(
        "https://upload.example/session/abc", "token", video, chunk_size=4, http=http
    )

    assert response["id"] == "vid123"
    ranges = [call["headers"]["Content-Range"] for call in http.calls]
    assert ranges == ["bytes 0-3/10", "bytes 4-7/10", "bytes 8-9/10"]


def test_upload_media_reports_progress(tmp_path):
    video = _video_file(tmp_path, size=10)
    http = FakeHttpClient(
        [
            HttpResponse(status=308, headers={}, body=b""),
            HttpResponse(status=200, headers={}, body=b'{"id": "v1"}'),
        ]
    )
    seen = []

    upload_media(
        "https://upload.example/session/abc",
        "token",
        video,
        chunk_size=6,
        http=http,
        progress=lambda done, total: seen.append((done, total)),
    )

    assert seen[0] == (6, 10)
    assert seen[-1] == (10, 10)


def test_upload_quota_error_is_typed(tmp_path):
    video = _video_file(tmp_path)
    http = FakeHttpClient(
        [
            HttpResponse(
                status=403,
                headers={},
                body=b'{"error": {"message": "quotaExceeded: daily limit"}}',
            )
        ]
    )

    with pytest.raises(QuotaError):
        upload_media("https://upload.example/s", "token", video, http=http)


def test_upload_invalid_request_is_typed(tmp_path):
    video = _video_file(tmp_path)
    http = FakeHttpClient(
        [
            HttpResponse(
                status=400, headers={}, body=b'{"error": {"message": "badRequest"}}'
            )
        ]
    )

    with pytest.raises(InvalidRequestError):
        upload_media("https://upload.example/s", "token", video, http=http)


# =========================
# END TO END
# =========================
def test_publish_video_end_to_end(tmp_path):
    video = _video_file(tmp_path, size=8)
    http = FakeHttpClient(
        [
            _token_response("ya29.tok"),
            _session_response(),
            HttpResponse(status=200, headers={}, body=b'{"id": "vid-42"}'),
        ]
    )

    published = publish_video(
        video,
        VideoMetadata(title="My Short", privacy_status="private"),
        client_id="cid",
        client_secret="secret",
        refresh_token="refresh",
        http=http,
    )

    assert published.video_id == "vid-42"
    assert published.url == "https://youtu.be/vid-42"
    assert published.bytes_uploaded == 8
    assert published.dry_run is False


def test_publish_video_dry_run_never_touches_the_network(tmp_path):
    video = _video_file(tmp_path)

    published = publish_video(
        video,
        VideoMetadata(title="Dry"),
        client_id="",
        client_secret="",
        refresh_token="",
        dry_run=True,
    )

    assert published.dry_run is True
    assert published.video_id == "dry-run"


def test_publish_video_requires_existing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        publish_video(tmp_path / "missing.mp4", VideoMetadata(title="x"), dry_run=True)


def test_publish_video_without_credentials_is_actionable(tmp_path):
    video = _video_file(tmp_path)

    with pytest.raises(AuthError) as excinfo:
        publish_video(
            video,
            VideoMetadata(title="x"),
            client_id="",
            client_secret="",
            refresh_token="",
        )

    assert "YOUTUBE_CLIENT_ID" in str(excinfo.value)


# =========================
# METADATA
# =========================
def test_build_metadata_uses_content_pack_and_settings():
    metadata = build_metadata(
        content_pack={"title": "Pack title", "description": "Pack body", "tags": ["x"]}
    )

    assert metadata.title == "Pack title"
    assert metadata.description == "Pack body"
    assert metadata.tags == ["x"]
    assert metadata.privacy_status in {"private", "unlisted", "public"}


def test_build_metadata_rejects_invalid_privacy():
    with pytest.raises(InvalidRequestError):
        build_metadata(title="t", privacy_status="secret")


def test_build_metadata_rejects_empty_title():
    with pytest.raises(InvalidRequestError):
        build_metadata(title="   ")
