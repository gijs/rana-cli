"""OAuth2 authorizationCode + PKCE login against the Rana identity provider.

Why this is a two-step, human-in-the-loop flow
------------------------------------------------
For the built-in "test" environment, the registered OAuth2 client's
redirect_uri points at the Rana API's Swagger docs page, not at a localhost
port this CLI controls — so there's no way to silently capture the
authorization code. Login is a manual handoff: this CLI prints a URL, a
human opens it, logs in, and pastes back the URL they land on.

If you register your own OAuth2 client (e.g. for a custom/prod environment)
with a `redirect_uri` of `http://localhost:<port>/...`, `rana auth login`
will detect that and capture the code automatically instead.
"""
import base64
import hashlib
import http.server
import json
import secrets
import time
import urllib.parse
import webbrowser

import requests

from . import config as config_mod

TOKEN_EXPIRY_SAFETY_MARGIN_SECONDS = 30
LOCAL_CAPTURE_TIMEOUT_SECONDS = 180


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def generate_pkce_pair():
    verifier = _b64url(secrets.token_bytes(40))  # 43-128 chars, this gives ~54
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


def _load_json(path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _pending_all():
    return _load_json(config_mod.PENDING_PATH)


def _tokens_all():
    return _load_json(config_mod.TOKENS_PATH)


def build_authorize_url(cfg: dict, scopes=None):
    """Returns (url, verifier, state). Does not persist anything."""
    verifier, challenge = generate_pkce_pair()
    state = _b64url(secrets.token_bytes(16))

    params = {
        "response_type": "code",
        "client_id": cfg["client_id"],
        "redirect_uri": cfg["redirect_uri"],
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    # NOTE: the built-in "test" client rejects any explicit `scope` value
    # with invalid_scope (verified against every individual scope in the
    # OpenAPI spec, plus "openid"). Omitting it works and the server grants
    # a domain-scoped token. Only pass scopes for environments/clients
    # you've confirmed accept them.
    if scopes:
        params["scope"] = " ".join(scopes)

    url = cfg["authorization_url"] + "?" + urllib.parse.urlencode(params)
    return url, verifier, state


def _save_pending(env: str, verifier: str, state: str):
    config_mod.ensure_state_dir()
    pending = _pending_all()
    pending[env] = {"verifier": verifier, "state": state, "created_at": time.time()}
    config_mod.PENDING_PATH.write_text(json.dumps(pending, indent=2))


def _clear_pending(env: str):
    pending = _pending_all()
    pending.pop(env, None)
    config_mod.PENDING_PATH.write_text(json.dumps(pending, indent=2))


def _extract_code_and_state(url_or_code: str):
    """Accept either a bare authorization code or the full redirected URL."""
    if "code=" not in url_or_code and "://" not in url_or_code:
        return url_or_code, None
    parsed = urllib.parse.urlparse(url_or_code)
    qs = urllib.parse.parse_qs(parsed.query)
    if not qs.get("code") and parsed.fragment:
        qs = urllib.parse.parse_qs(parsed.fragment)
    code = qs.get("code", [None])[0]
    state = qs.get("state", [None])[0]
    if not code:
        raise SystemExit(f"Could not find `code=` in: {url_or_code!r}")
    return code, state


def _local_redirect_target(redirect_uri: str):
    """If redirect_uri is localhost, return (host, port) to listen on, else None."""
    parsed = urllib.parse.urlparse(redirect_uri)
    if parsed.hostname in ("localhost", "127.0.0.1") and parsed.port:
        return parsed.hostname, parsed.port
    return None


def _capture_code_locally(host: str, port: int, timeout: int = LOCAL_CAPTURE_TIMEOUT_SECONDS):
    result = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            result["code"] = qs.get("code", [None])[0]
            result["state"] = qs.get("state", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body>Login complete, you can close this tab.</body></html>")

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer((host, port), Handler)
    server.timeout = timeout
    server.handle_request()
    server.server_close()
    return result.get("code"), result.get("state")


def exchange_code(cfg: dict, code: str, verifier: str) -> dict:
    resp = requests.post(
        cfg["token_url"],
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": cfg["redirect_uri"],
            "client_id": cfg["client_id"],
            "code_verifier": verifier,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    if not resp.ok:
        raise SystemExit(f"Token exchange failed: {resp.status_code} {resp.text}")
    return resp.json()


def save_token_response(env: str, payload: dict):
    config_mod.ensure_state_dir()
    expires_in = payload.get("expires_in", 3600)
    record = {
        "access_token": payload["access_token"],
        "refresh_token": payload.get("refresh_token"),
        "token_type": payload.get("token_type", "Bearer"),
        "scope": payload.get("scope", ""),
        "obtained_at": time.time(),
        "expires_at": time.time() + expires_in - TOKEN_EXPIRY_SAFETY_MARGIN_SECONDS,
    }
    tokens = _tokens_all()
    tokens[env] = record
    config_mod.TOKENS_PATH.write_text(json.dumps(tokens, indent=2))
    return record


def login(cfg: dict, scopes=None, no_browser: bool = False, print_fn=print):
    """Run the full login flow for one environment. Blocks on user input."""
    env = cfg["env"]
    url, verifier, state = build_authorize_url(cfg, scopes=scopes)
    local_target = _local_redirect_target(cfg["redirect_uri"])

    if not local_target:
        _save_pending(env, verifier, state)

    print_fn(f"Open this URL in a browser and log in ({env}):\n")
    print_fn(url)
    print_fn("")
    if not no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    if local_target:
        host, port = local_target
        print_fn(f"Waiting for the redirect on http://{host}:{port} ...")
        code, returned_state = _capture_code_locally(host, port)
        if not code:
            raise SystemExit("Timed out waiting for the OAuth2 redirect.")
        if returned_state != state:
            raise SystemExit("State mismatch on local redirect capture — login aborted.")
        payload = exchange_code(cfg, code, verifier)
        save_token_response(env, payload)
        print_fn(f"Authenticated. Tokens cached at {config_mod.TOKENS_PATH}")
        return

    print_fn("After logging in, copy the FULL resulting URL from the address bar")
    print_fn("(it contains `code=` and `state=`) and run:\n")
    print_fn(f"  rana auth exchange --url '<pasted-url>' --env {env}")


def do_exchange(cfg: dict, url_or_code: str):
    env = cfg["env"]
    pending = _pending_all().get(env)
    if not pending:
        raise SystemExit(f"No pending login for environment {env!r} — run `rana auth login` first.")

    code, state = _extract_code_and_state(url_or_code)
    if state and state != pending["state"]:
        raise SystemExit(
            f"State mismatch (got {state!r}, expected {pending['state']!r}). "
            "The login may be stale — try `rana auth login` again."
        )
    payload = exchange_code(cfg, code, pending["verifier"])
    save_token_response(env, payload)
    _clear_pending(env)
    return config_mod.TOKENS_PATH


def _refresh(cfg: dict, tokens: dict) -> dict:
    if not tokens.get("refresh_token"):
        raise SystemExit(
            "Access token expired and no refresh_token is available — "
            "run `rana auth login` again to log in."
        )
    resp = requests.post(
        cfg["token_url"],
        data={
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
            "client_id": cfg["client_id"],
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    if not resp.ok:
        raise SystemExit(
            f"Refresh failed: {resp.status_code} {resp.text}\n"
            "Run `rana auth login` again to log in fresh."
        )
    payload = resp.json()
    # some servers omit refresh_token on refresh responses, meaning "reuse the old one"
    if "refresh_token" not in payload:
        payload["refresh_token"] = tokens["refresh_token"]
    return save_token_response(cfg["env"], payload)


def get_valid_access_token(cfg: dict, force_refresh: bool = False) -> str:
    env = cfg["env"]
    tokens = _tokens_all().get(env)
    if not tokens:
        raise SystemExit(f"Not authenticated for environment {env!r} — run `rana auth login` first.")
    if force_refresh or time.time() >= tokens["expires_at"]:
        tokens = _refresh(cfg, tokens)
    return tokens["access_token"]


def logout(env: str):
    tokens = _tokens_all()
    had_token = tokens.pop(env, None) is not None
    config_mod.TOKENS_PATH.write_text(json.dumps(tokens, indent=2))
    _clear_pending(env)
    return had_token


def token_status(env: str):
    tokens = _tokens_all().get(env)
    if not tokens:
        return None
    return {
        "authenticated": True,
        "token_type": tokens.get("token_type"),
        "has_refresh_token": bool(tokens.get("refresh_token")),
        "expires_at": tokens["expires_at"],
        "expired": time.time() >= tokens["expires_at"],
        "scope": tokens.get("scope"),
    }
