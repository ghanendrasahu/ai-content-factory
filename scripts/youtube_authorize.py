"""Obtain a YouTube OAuth refresh token (one-time consent flow).

Google Cloud console -> enable the *YouTube Data API v3* -> create an OAuth
client ID of type *Desktop app* -> download the client secret. Then:

    python scripts/youtube_authorize.py --client-id "<id>" --client-secret "<secret>"

The script opens the consent screen (or prints the URL), captures the redirect
on a temporary local port, exchanges the authorisation code for tokens and
prints the **refresh token** - that is the long-lived credential the publisher
needs. With ``--write-env`` it also stores the three values in ``.env``
(never in git).

``--auth-url`` points the consent screen somewhere else (a local stub in the
test suite); the token endpoint follows ``YOUTUBE_API_BASE_URL`` when set.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import settings  # noqa: E402
from app.services.youtube_publisher import (  # noqa: E402
    token_endpoint,
)

DEFAULT_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
SCOPE = "https://www.googleapis.com/auth/youtube.upload"


class _CallbackHandler(BaseHTTPRequestHandler):
    """Captures ``?code=`` from the OAuth redirect."""

    protocol_version = "HTTP/1.1"
    server: "ThreadingHTTPServer"

    def log_message(self, *args):
        pass

    def do_GET(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        code = (params.get("code") or [""])[0]
        error = (params.get("error") or [""])[0]

        self.server.auth_code = code  # type: ignore[attr-defined]
        self.server.auth_error = error  # type: ignore[attr-defined]

        body = (
            b"<html><body style='font-family:sans-serif;padding:40px'>"
            b"<h2>Authorization complete</h2>"
            b"<p>You can close this tab and return to the terminal.</p>"
            b"</body></html>"
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def build_auth_url(
    client_id: str,
    redirect_uri: str,
    auth_url: str,
) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"{auth_url}?{urllib.parse.urlencode(params)}"


def exchange_code(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    timeout: int = 30,
) -> dict:
    """Trade the authorisation code for access + refresh tokens."""
    payload = urllib.parse.urlencode(
        {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        token_endpoint(),
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def write_env(
    path: Path, client_id: str, client_secret: str, refresh_token: str
) -> None:
    """Store the credentials in ``.env`` (replacing any previous values)."""
    values = {
        "YOUTUBE_CLIENT_ID": client_id,
        "YOUTUBE_CLIENT_SECRET": client_secret,
        "YOUTUBE_REFRESH_TOKEN": refresh_token,
    }
    lines: list[str] = []
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()

    for key, value in values.items():
        replacement = f"{key}={value}"
        for index, line in enumerate(lines):
            if line.strip().startswith(f"{key}="):
                lines[index] = replacement
                break
        else:
            lines.append(replacement)

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_flow(
    client_id: str,
    client_secret: str,
    auth_url: str = DEFAULT_AUTH_URL,
    env_file: str | Path | None = None,
    write: bool = False,
    open_url=None,
    timeout_seconds: int = 300,
) -> str:
    """Run the consent flow and return the refresh token.

    ``open_url`` receives the consent URL - the default opens a browser; the
    test suite injects its own redirect-following opener.
    """
    server = ThreadingHTTPServer(("127.0.0.1", 0), _CallbackHandler)
    server.auth_code = ""  # type: ignore[attr-defined]
    server.auth_error = ""  # type: ignore[attr-defined]
    port = server.server_address[1]
    redirect_uri = f"http://127.0.0.1:{port}/oauth2callback"

    url = build_auth_url(client_id, redirect_uri, auth_url)
    print("Open this URL and approve the request:")
    print(f"  {url}")

    import threading

    threading.Thread(target=server.serve_forever, daemon=True).start()

    opener = open_url or webbrowser.open
    try:
        opener(url)
    except Exception:  # noqa: BLE001 - a headless host simply prints the URL
        pass

    print("Waiting for the OAuth redirect ...")
    waited = 0.0
    while not server.auth_code and not server.auth_error and waited < timeout_seconds:
        threading.Event().wait(0.5)
        waited += 0.5

    server.shutdown()
    server.server_close()

    if server.auth_error:
        raise RuntimeError(f"authorization failed: {server.auth_error}")
    if not server.auth_code:
        raise TimeoutError("timed out waiting for the OAuth redirect")

    tokens = exchange_code(server.auth_code, client_id, client_secret, redirect_uri)
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        raise RuntimeError(
            "no refresh token in the response - revoke the app grant and retry "
            "with access_type=offline and prompt=consent"
        )

    print("\nAuthorization successful")
    print(f"refresh token: {refresh_token}")
    print("\nAdd to your .env:")
    print(f'YOUTUBE_CLIENT_ID="{client_id}"')
    print(f'YOUTUBE_CLIENT_SECRET="{client_secret}"')
    print(f'YOUTUBE_REFRESH_TOKEN="{refresh_token}"')

    if write and env_file:
        write_env(Path(env_file), client_id, client_secret, str(refresh_token))
        print(f"\nwritten to {env_file}")

    return str(refresh_token)


def main() -> int:
    parser = argparse.ArgumentParser(description="Get a YouTube OAuth refresh token.")
    parser.add_argument("--client-id", default="", help="OAuth client id")
    parser.add_argument("--client-secret", default="", help="OAuth client secret")
    parser.add_argument(
        "--auth-url", default=DEFAULT_AUTH_URL, help="Consent screen URL"
    )
    parser.add_argument(
        "--env-file",
        default=str(ROOT_DIR / ".env"),
        help="Where to store the credentials",
    )
    parser.add_argument(
        "--write-env",
        action="store_true",
        help="Write the credentials into the env file after a successful exchange",
    )
    parser.add_argument(
        "--no-browser", action="store_true", help="Print the URL instead of opening it"
    )
    args = parser.parse_args()

    client_id = args.client_id or settings.YOUTUBE_CLIENT_ID
    client_secret = args.client_secret or settings.YOUTUBE_CLIENT_SECRET

    if not (client_id and client_secret):
        print(
            "client id and client secret are required (--client-id/--client-secret)",
            file=sys.stderr,
        )
        return 1

    opener = None if args.no_browser else webbrowser.open
    try:
        run_flow(
            client_id,
            client_secret,
            auth_url=args.auth_url,
            env_file=args.env_file,
            write=args.write_env,
            open_url=opener,
        )
    except (RuntimeError, TimeoutError, OSError) as exc:
        print(f"authorization failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
