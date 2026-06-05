#!/usr/bin/env python3
"""Create OAuth refresh token for AgentCore email and Drive automation."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from common import get_env, load_env_file

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/keep.readonly",
]


class CallbackHandler(BaseHTTPRequestHandler):
    code = ""
    error = ""
    expected_state = ""

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        return

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        state = params.get("state", [""])[0]
        if state != self.expected_state:
            self.__class__.error = "OAuth state mismatch."
        else:
            self.__class__.code = params.get("code", [""])[0]
            self.__class__.error = params.get("error", [""])[0]

        body = (
            "AgentCore authorization received. You can close this tab."
            if self.code and not self.error
            else f"AgentCore authorization failed: {self.error or 'missing code'}"
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate OAuth refresh token setup values.")
    parser.add_argument("--port", type=int, default=8765, help="Local callback port.")
    parser.add_argument("--no-browser", action="store_true", help="Print the auth URL without opening a browser.")
    parser.add_argument(
        "--client-file",
        default="",
        help="Path to Google OAuth client JSON (downloaded desktop app credentials).",
    )
    parser.add_argument(
        "--authorized-user-out",
        default=".secrets/gmail-authorized-user.json",
        help="Path to write authorized-user JSON output.",
    )
    parser.add_argument(
        "--print-secrets",
        action="store_true",
        help="Print full refresh-token values to stdout (default is redacted).",
    )
    return parser.parse_args()


def _client_credentials(args: argparse.Namespace, env_map: dict[str, str]) -> tuple[str, str]:
    client_id = get_env(
        "AGENTCORE_GMAIL_CLIENT_ID",
        fallback_keys=("GOOGLE_OAUTH_CLIENT_ID",),
        env_map=env_map,
    )
    client_secret = get_env(
        "AGENTCORE_GMAIL_CLIENT_SECRET",
        fallback_keys=("GOOGLE_OAUTH_CLIENT_SECRET",),
        env_map=env_map,
    )
    if client_id and client_secret:
        return client_id, client_secret

    file_candidates = [
        args.client_file.strip(),
        get_env("AGENTCORE_GMAIL_CLIENT_SECRET_FILE", env_map=env_map),
        ".secrets/google-oauth-client.json",
    ]
    for candidate in file_candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        installed = payload.get("installed", payload)
        from_file_id = str(installed.get("client_id", ""))
        from_file_secret = str(installed.get("client_secret", ""))
        if from_file_id and from_file_secret:
            return from_file_id, from_file_secret

    raise ValueError(
        "Missing OAuth client credentials. Set AGENTCORE_GMAIL_CLIENT_ID and "
        "AGENTCORE_GMAIL_CLIENT_SECRET, or provide --client-file / "
        "AGENTCORE_GMAIL_CLIENT_SECRET_FILE."
    )


def main() -> int:
    args = parse_args()
    env_map = load_env_file(".env")
    client_id, client_secret = _client_credentials(args, env_map)

    redirect_uri = f"http://127.0.0.1:{args.port}/callback"
    state = secrets.token_urlsafe(24)
    CallbackHandler.expected_state = state
    auth_params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(auth_params)}"
    print("Open this URL to authorize AgentCore email and Drive access:")
    print(auth_url)
    if not args.no_browser:
        webbrowser.open(auth_url)

    server = HTTPServer(("127.0.0.1", args.port), CallbackHandler)
    server.handle_request()
    if CallbackHandler.error or not CallbackHandler.code:
        raise RuntimeError(CallbackHandler.error or "OAuth callback did not include a code.")

    token_payload = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": CallbackHandler.code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        TOKEN_URL,
        data=token_payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        token_response = json.loads(response.read().decode("utf-8"))

    refresh_token = token_response.get("refresh_token")
    if not refresh_token:
        raise RuntimeError("Google did not return a refresh token. Re-run with prompt=consent or revoke prior access.")

    authorized_user = {
        "type": "authorized_user",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }
    out_path = Path(args.authorized_user_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(authorized_user, indent=2) + "\n", encoding="utf-8")
    os.chmod(out_path, 0o600)
    os.chmod(out_path.parent, 0o700)

    masked_token = f"{refresh_token[:10]}...{refresh_token[-6:]}" if len(refresh_token) > 20 else "***"
    print("\nOAuth setup complete.")
    print(f"Authorized-user file written: {out_path}")
    print("Use these env settings:")
    print(f"AGENTCORE_GMAIL_CLIENT_ID={client_id}")
    print("AGENTCORE_GMAIL_CLIENT_SECRET=<same client secret>")
    print("AGENTCORE_EMAIL_TRANSPORT=gmail-api")
    print(f"AGENTCORE_GMAIL_AUTHORIZED_USER_FILE={out_path}")
    print(f"AGENTCORE_GMAIL_REFRESH_TOKEN(masked)={masked_token}")
    if args.print_secrets:
        print("\nFull authorized-user JSON:")
        print(json.dumps(authorized_user, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
