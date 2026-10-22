"""Publish rendered videos to YouTube via the Data API.

Implements the real resumable-upload flow with the standard library only (no
heavy Google SDK, nothing to pin):

1. refresh an OAuth2 access token from a refresh token
2. create a resumable upload session for ``snippet,status``
3. PUT the video in chunks, honouring ``308 Resume Incomplete`` responses

The HTTP transport is injectable, so the whole flow is testable offline.
Credentials come from the environment only - never from code.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

from app.config import settings
from app.logger import logger

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
WATCH_URL = "https://youtu.be/{video_id}"


def token_endpoint() -> str:
    """OAuth token endpoint (overridable for tests and proxies)."""
    base = str(getattr(settings, "YOUTUBE_API_BASE_URL", "") or "").strip().rstrip("/")
    return f"{base}/token" if base else TOKEN_URL


def upload_endpoint() -> str:
    """Resumable upload endpoint (overridable for tests and proxies)."""
    base = str(getattr(settings, "YOUTUBE_API_BASE_URL", "") or "").strip().rstrip("/")
    return f"{base}/upload/youtube/v3/videos" if base else UPLOAD_URL


# =========================
# ERRORS
# =========================
class PublishError(RuntimeError):
    """Base class for publishing failures."""


class AuthError(PublishError):
    """Credentials are missing, expired or rejected."""


class QuotaError(PublishError):
    """YouTube refused the request because of quota / rate limits."""


class InvalidRequestError(PublishError):
    """YouTube considered the request malformed (metadata, file, scope)."""


class UploadError(PublishError):
    """Transport or server-side failure while uploading media."""


# =========================
# HTTP TRANSPORT
# =========================
@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: dict[str, str]
    body: bytes

    def json(self) -> Any:
        if not self.body:
            return {}
        try:
            return json.loads(self.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {"raw": self.body.decode("utf-8", errors="replace")}

    def header(self, name: str) -> str | None:
        lowered = name.lower()
        for key, value in self.headers.items():
            if key.lower() == lowered:
                return value
        return None


class HttpClient(Protocol):
    """Minimal HTTP surface used by the publisher (easy to fake in tests)."""

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        data: bytes | None = None,
    ) -> HttpResponse: ...


class UrllibHttpClient:
    """Default transport built on ``urllib`` (stdlib only)."""

    def __init__(self, timeout: int = 60) -> None:
        self.timeout = timeout

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        data: bytes | None = None,
    ) -> HttpResponse:
        request = urllib.request.Request(
            url, data=data, method=method, headers=headers or {}
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return HttpResponse(
                    status=response.status,
                    headers=dict(response.headers.items()),
                    body=response.read(),
                )
        except urllib.error.HTTPError as exc:
            return HttpResponse(
                status=exc.code, headers=dict(exc.headers.items()), body=exc.read()
            )
        except urllib.error.URLError as exc:
            raise UploadError(f"Network error calling {url}: {exc.reason}") from exc
        except TimeoutError as exc:
            raise UploadError(f"Timeout calling {url}") from exc


# =========================
# MODELS
# =========================
@dataclass(frozen=True)
class VideoMetadata:
    """Metadata sent as ``snippet`` + ``status`` with the upload request."""

    title: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    category_id: str = "27"
    privacy_status: str = "private"
    made_for_kids: bool = False
    embeddable: bool = True

    def to_snippet(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "tags": list(self.tags),
            "categoryId": self.category_id,
        }

    def to_status(self) -> dict[str, Any]:
        return {
            "privacyStatus": self.privacy_status,
            "madeForKids": self.made_for_kids,
            "selfDeclaredMadeForKids": self.made_for_kids,
            "embeddable": self.embeddable,
        }


@dataclass(frozen=True)
class PublishedVideo:
    """Outcome of a successful (or simulated) publish."""

    video_id: str
    title: str
    privacy_status: str
    url: str
    bytes_uploaded: int
    dry_run: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "video_id": self.video_id,
            "title": self.title,
            "privacy_status": self.privacy_status,
            "url": self.url,
            "bytes_uploaded": self.bytes_uploaded,
            "dry_run": self.dry_run,
        }


ProgressCallback = Callable[[int, int], None]


# =========================
# HELPERS
# =========================
def _error_text(response: HttpResponse) -> str:
    payload = response.json()
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if message:
                return str(message)
        if payload.get("raw"):
            return str(payload["raw"])[:500]
        if payload:
            return json.dumps(payload)[:500]
    return response.body.decode("utf-8", errors="replace")[:500]


def _raise_for_status(response: HttpResponse, context: str) -> None:
    """Translate an HTTP status into the matching typed error."""
    detail = _error_text(response)
    status = response.status

    if status == 401:
        raise AuthError(
            f"YouTube rejected the credentials during {context} (401): {detail}. "
            "Refresh the OAuth refresh token."
        )
    if status == 403:
        lowered = detail.lower()
        if "quota" in lowered or "ratelimit" in lowered or "daily limit" in lowered:
            raise QuotaError(
                f"YouTube quota exceeded during {context} (403): {detail}. "
                "Daily upload quota is exhausted - retry tomorrow."
            )
        raise AuthError(
            f"YouTube denied the request during {context} (403): {detail}. "
            "Check the OAuth scope (youtube.upload) and channel permissions."
        )
    if status == 400:
        raise InvalidRequestError(
            f"YouTube considered the request invalid during {context} (400): {detail}"
        )
    if status == 404:
        raise InvalidRequestError(
            f"YouTube could not find the resource during {context} (404): {detail}"
        )
    if status >= 500:
        raise UploadError(f"YouTube server error during {context} ({status}): {detail}")
    raise PublishError(f"{context} failed ({status}): {detail}")


def build_metadata(
    title: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    privacy_status: str | None = None,
    content_pack: dict | None = None,
) -> VideoMetadata:
    """Assemble metadata, falling back to the content pack and settings."""
    pack = content_pack or {}
    resolved_title = title or pack.get("title") or "AI Content Factory"
    resolved_description = description or pack.get("description") or ""
    resolved_tags = (
        tags if tags is not None else list(pack.get("tags") or settings.YOUTUBE_TAGS)
    )
    resolved_privacy = privacy_status or settings.YOUTUBE_DEFAULT_PRIVACY

    if resolved_privacy not in {"private", "unlisted", "public"}:
        raise InvalidRequestError(
            f"Invalid privacy status '{resolved_privacy}'. Use private, unlisted or public."
        )
    if not str(resolved_title).strip():
        raise InvalidRequestError("A video title is required to publish.")

    return VideoMetadata(
        title=str(resolved_title)[:100],
        description=str(resolved_description)[:5000],
        tags=[str(tag)[:30] for tag in resolved_tags][:30],
        category_id=settings.YOUTUBE_CATEGORY_ID,
        privacy_status=resolved_privacy,
        made_for_kids=settings.YOUTUBE_PUBLISH_MADE_FOR_KIDS,
    )


# =========================
# API STEPS
# =========================
def refresh_access_token(
    client_id: str,
    client_secret: str,
    refresh_token: str,
    http: HttpClient | None = None,
) -> str:
    """Exchange a refresh token for a short-lived access token."""
    if not (client_id and client_secret and refresh_token):
        raise AuthError(
            "YouTube credentials are not configured. Set YOUTUBE_CLIENT_ID, "
            "YOUTUBE_CLIENT_SECRET and YOUTUBE_REFRESH_TOKEN (or use dry_run=True)."
        )

    client = http or UrllibHttpClient(settings.YOUTUBE_PUBLISH_TIMEOUT_SECONDS)
    payload = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        }
    ).encode("utf-8")

    response = client.request(
        "POST",
        token_endpoint(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=payload,
    )
    if response.status != 200:
        detail = _error_text(response)
        if response.status in (400, 401) or "invalid_grant" in detail:
            raise AuthError(
                f"YouTube OAuth refresh failed ({response.status}): {detail}. "
                "The refresh token is invalid or revoked - re-authorise the app."
            )
        if response.status == 403:
            raise QuotaError(f"YouTube OAuth refresh quota error (403): {detail}")
        raise PublishError(
            f"YouTube OAuth refresh failed ({response.status}): {detail}"
        )

    token = response.json().get("access_token")
    if not token:
        raise AuthError("YouTube OAuth response contained no access_token.")
    return str(token)


def create_upload_session(
    token: str,
    metadata: VideoMetadata,
    video_size: int,
    http: HttpClient | None = None,
) -> str:
    """Create a resumable upload session and return its URI."""
    client = http or UrllibHttpClient(settings.YOUTUBE_PUBLISH_TIMEOUT_SECONDS)
    body = json.dumps(
        {"snippet": metadata.to_snippet(), "status": metadata.to_status()}
    ).encode("utf-8")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=UTF-8",
        "Content-Length": str(len(body)),
        "X-Upload-Content-Type": "video/mp4",
        "X-Upload-Content-Length": str(video_size),
    }
    response = client.request(
        "POST",
        f"{upload_endpoint()}?uploadType=resumable&part=snippet,status",
        headers=headers,
        data=body,
    )
    if response.status not in (200, 201):
        _raise_for_status(response, "upload session creation")

    location = response.header("Location")
    if not location:
        raise UploadError(
            "YouTube did not return a Location header for the upload session."
        )
    return location


def upload_media(
    session_uri: str,
    token: str,
    video_path: str | Path,
    chunk_size: int = 8 * 1024 * 1024,
    http: HttpClient | None = None,
    progress: ProgressCallback | None = None,
) -> dict[str, Any]:
    """Upload the media in chunks, resuming on ``308`` responses."""
    client = http or UrllibHttpClient(settings.YOUTUBE_PUBLISH_TIMEOUT_SECONDS)
    path = Path(video_path)
    total = path.stat().st_size
    offset = 0

    with path.open("rb") as handle:
        while offset < total:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            end = offset + len(chunk) - 1
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "video/mp4",
                "Content-Length": str(len(chunk)),
                "Content-Range": f"bytes {offset}-{end}/{total}",
            }
            response = client.request("PUT", session_uri, headers=headers, data=chunk)

            if response.status in (200, 201):
                if progress:
                    progress(total, total)
                return response.json()

            if response.status == 308:
                offset = end + 1
                if progress:
                    progress(offset, total)
                continue

            _raise_for_status(response, "media upload")

    raise UploadError("Upload ended without a completion response from YouTube.")


def publish_video(
    video_path: str | Path,
    metadata: VideoMetadata,
    *,
    client_id: str | None = None,
    client_secret: str | None = None,
    refresh_token: str | None = None,
    dry_run: bool = False,
    chunk_size: int | None = None,
    http: HttpClient | None = None,
    progress: ProgressCallback | None = None,
) -> PublishedVideo:
    """Publish a video end to end. ``dry_run`` validates without any network."""
    path = Path(video_path)
    if not path.is_file():
        raise FileNotFoundError(f"Video not found: {path}")

    size = path.stat().st_size
    if size == 0:
        raise InvalidRequestError(f"Video file is empty: {path}")

    if dry_run:
        logger.info("YouTube publish dry-run for %s (%s bytes)", path.name, size)
        return PublishedVideo(
            video_id="dry-run",
            title=metadata.title,
            privacy_status=metadata.privacy_status,
            url="https://youtu.be/dry-run",
            bytes_uploaded=size,
            dry_run=True,
        )

    token = refresh_access_token(
        client_id or settings.YOUTUBE_CLIENT_ID,
        client_secret or settings.YOUTUBE_CLIENT_SECRET,
        refresh_token or settings.YOUTUBE_REFRESH_TOKEN,
        http=http,
    )
    session_uri = create_upload_session(token, metadata, size, http=http)
    response = upload_media(
        session_uri,
        token,
        path,
        chunk_size=chunk_size or settings.YOUTUBE_UPLOAD_CHUNK_BYTES,
        http=http,
        progress=progress,
    )

    video_id = str(response.get("id") or "")
    if not video_id:
        raise UploadError(f"YouTube did not return a video id: {response}")

    published = PublishedVideo(
        video_id=video_id,
        title=metadata.title,
        privacy_status=metadata.privacy_status,
        url=WATCH_URL.format(video_id=video_id),
        bytes_uploaded=size,
    )
    logger.info(
        "Published YouTube video id=%s privacy=%s bytes=%s",
        published.video_id,
        published.privacy_status,
        published.bytes_uploaded,
    )
    return published


class YouTubePublisher:
    """House-style facade over the publishing functions."""

    @staticmethod
    def build_metadata(**kwargs) -> VideoMetadata:
        return build_metadata(**kwargs)

    @staticmethod
    def publish(video_path, metadata, **kwargs) -> PublishedVideo:
        return publish_video(video_path, metadata, **kwargs)

    @staticmethod
    def dry_run(video_path, metadata) -> PublishedVideo:
        return publish_video(video_path, metadata, dry_run=True)


__all__ = [
    "AuthError",
    "HttpClient",
    "HttpResponse",
    "InvalidRequestError",
    "PublishedVideo",
    "PublishError",
    "QuotaError",
    "UploadError",
    "UrllibHttpClient",
    "VideoMetadata",
    "YouTubePublisher",
    "build_metadata",
    "create_upload_session",
    "publish_video",
    "refresh_access_token",
    "upload_media",
]
