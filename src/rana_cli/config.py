"""Environment/config resolution for rana-cli.

Precedence (highest wins): CLI flags > environment variables > user config
file (~/.config/rana-cli/config.json) > built-in preset for the selected
environment name.

An "environment" is just a named bundle of API base URL + OAuth2 client
settings, e.g. "test" (the default, pointed at
test.ranawaterintelligence.com / tenant nenstest). Add more environments
(e.g. "prod") to the user config file once you have a registered client_id
for them.
"""
import json
import os
from pathlib import Path

BUILTIN_PRESETS = {
    "test": {
        "api_base_url": "https://test.ranawaterintelligence.com/v1-alpha",
        "default_tenant_id": "nenstest",
        "client_id": "rs93kg69kleebmqv3tr14kao9",
        "authorization_url": "https://auth.lizard.net/oauth2/authorize",
        "token_url": "https://auth.lizard.net/oauth2/token",
        "redirect_uri": "https://test.ranawaterintelligence.com/v1-alpha/docs/oauth2-redirect",
    },
}

REQUIRED_KEYS = [
    "api_base_url",
    "default_tenant_id",
    "client_id",
    "authorization_url",
    "token_url",
    "redirect_uri",
]

STATE_DIR = Path(os.environ.get("RANA_CLI_STATE_DIR", Path.home() / ".config" / "rana-cli"))
CONFIG_PATH = STATE_DIR / "config.json"
TOKENS_PATH = STATE_DIR / "tokens.json"
PENDING_PATH = STATE_DIR / "pending_auth.json"

ENV_VAR_OVERRIDES = {
    "api_base_url": "RANA_API_BASE_URL",
    "default_tenant_id": "RANA_TENANT_ID",
    "client_id": "RANA_CLIENT_ID",
    "authorization_url": "RANA_AUTH_URL",
    "token_url": "RANA_TOKEN_URL",
    "redirect_uri": "RANA_REDIRECT_URI",
}


def ensure_state_dir():
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def _load_user_config_file() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"Could not read {CONFIG_PATH}: {exc}")


def list_environments() -> list:
    envs = set(BUILTIN_PRESETS)
    envs.update(_load_user_config_file().keys())
    return sorted(envs)


def load_config(env: str = None, tenant_override: str = None) -> dict:
    """Resolve the full config for one environment.

    `env` defaults to $RANA_ENV or "test". The user config file may define
    per-environment blocks, keyed the same way as BUILTIN_PRESETS, e.g.:

        {"prod": {"api_base_url": "...", "client_id": "...", ...}}
    """
    env = env or os.environ.get("RANA_ENV", "test")

    cfg = dict(BUILTIN_PRESETS.get(env, {}))
    cfg.update(_load_user_config_file().get(env, {}))

    for key, var in ENV_VAR_OVERRIDES.items():
        value = os.environ.get(var)
        if value:
            cfg[key] = value

    if tenant_override:
        cfg["default_tenant_id"] = tenant_override

    missing = [k for k in REQUIRED_KEYS if not cfg.get(k)]
    if missing:
        raise SystemExit(
            f"Incomplete config for environment {env!r} — missing: {', '.join(missing)}.\n"
            f"Known environments: {', '.join(list_environments())}.\n"
            f"Add the missing keys to {CONFIG_PATH} under a {env!r} block, "
            f"or set the matching env var ({', '.join(ENV_VAR_OVERRIDES[k] for k in missing)})."
        )

    cfg["env"] = env
    return cfg
