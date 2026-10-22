"""Publish a rendered video to YouTube from the command line.

Usage:
    python scripts/publish.py --video outputs/<job>_vertical.mp4 \
        --title "5 facts about X" --description "..." --tags ai,shorts \
        --privacy private [--dry-run]

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

from app.services.youtube_publisher import (  # noqa: E402
    PublishError,
    YouTubePublisher,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish a video to YouTube.")
    parser.add_argument("--video", required=True, help="Path to the rendered video file")
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
    args = parser.parse_args()

    tags = [tag.strip() for tag in args.tags.split(",") if tag.strip()]

    try:
        metadata = YouTubePublisher.build_metadata(
            title=args.title,
            description=args.description,
            tags=tags or None,
            privacy_status=args.privacy,
        )
        published = YouTubePublisher.publish(
            args.video, metadata, dry_run=args.dry_run
        )
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
