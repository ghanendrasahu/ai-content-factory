"""Publish a rendered video to YouTube from the command line.

Usage:
    python scripts/publish.py --video outputs/<job>_vertical.mp4 \
        --title "5 facts about X" --description "..." --tags ai,shorts \
        --privacy private [--dry-run]

    python scripts/publish.py --check      # credential readiness, no upload

Credentials are read from the environment (YOUTUBE_CLIENT_ID,
YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN) - never from arguments.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import settings  # noqa: E402
from app.services.youtube_publisher import (  # noqa: E402
    PublishError,
    YouTubePublisher,
    refresh_access_token,
)


def check_credentials() -> int:
    """Verify the OAuth credentials are configured and can mint a token."""
    missing = [
        name
        for name, value in (
            ("YOUTUBE_CLIENT_ID", settings.YOUTUBE_CLIENT_ID),
            ("YOUTUBE_CLIENT_SECRET", settings.YOUTUBE_CLIENT_SECRET),
            ("YOUTUBE_REFRESH_TOKEN", settings.YOUTUBE_REFRESH_TOKEN),
        )
        if not value
    ]
    if missing:
        print("credentials incomplete - missing:", ", ".join(missing), file=sys.stderr)
        print(
            "Create a Google Cloud project, enable the YouTube Data API v3 and\n"
            "create an OAuth client, then run the consent flow once to obtain a\n"
            "refresh token. Put the three values in .env (never in git).",
            file=sys.stderr,
        )
        return 1

    try:
        token = refresh_access_token(
            settings.YOUTUBE_CLIENT_ID,
            settings.YOUTUBE_CLIENT_SECRET,
            settings.YOUTUBE_REFRESH_TOKEN,
        )
    except PublishError as exc:
        print(f"credentials rejected by YouTube: {exc}", file=sys.stderr)
        return 1

    print("credentials OK - access token acquired")
    print(f"token prefix: {token[:6]}...")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish a video to YouTube.")
    parser.add_argument("--video", help="Path to the rendered video file")
    parser.add_argument("--title", default=None, help="Video title")
    parser.add_argument("--description", default=None, help="Video description")
    parser.add_argument("--tags", default="", help="Comma-separated tags")
    parser.add_argument(
        "--privacy",
        default=None,
        choices=["private", "unlisted", "public"],
        help="Privacy status (defaults to YOUTUBE_DEFAULT_PRIVACY)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate metadata and the file without touching YouTube",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check that the OAuth credentials are present and usable (no upload)",
    )
    args = parser.parse_args()

    if args.check:
        return check_credentials()

    if not args.video:
        parser.error("--video is required unless --check is used")

    tags = [tag.strip() for tag in args.tags.split(",") if tag.strip()]

    try:
        metadata = YouTubePublisher.build_metadata(
            title=args.title,
            description=args.description,
            tags=tags or None,
            privacy_status=args.privacy,
        )
        published = YouTubePublisher.publish(args.video, metadata, dry_run=args.dry_run)
    except (PublishError, FileNotFoundError, ValueError) as exc:
        print(f"publish failed: {exc}", file=sys.stderr)
        return 1

    print(f"video_id : {published.video_id}")
    print(f"url      : {published.url}")
    print(f"privacy  : {published.privacy_status}")
    print(f"bytes    : {published.bytes_uploaded}")
    if published.dry_run:
        print("dry-run  : nothing was uploaded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
