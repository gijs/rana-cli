from .. import auth as auth_mod
from .. import config as config_mod
from ..output import print_json
from ._shared import add_env_tenant_args, get_client


def register(subparsers):
    p = subparsers.add_parser("auth", help="authenticate against the Rana API")
    sub = p.add_subparsers(dest="auth_command", required=True)

    p_login = sub.add_parser("login", help="start the OAuth2/PKCE login flow")
    add_env_tenant_args(p_login)
    p_login.add_argument("--scopes", help="comma-separated scope override (rarely needed/supported)")
    p_login.add_argument("--no-browser", action="store_true", help="don't try to auto-open a browser")
    p_login.set_defaults(func=cmd_login)

    p_exch = sub.add_parser("exchange", help="exchange a pasted redirect URL/code for tokens")
    add_env_tenant_args(p_exch)
    p_exch.add_argument("--url", help="the full redirected URL")
    p_exch.add_argument("--code", help="just the code, if you don't have the full URL")
    p_exch.set_defaults(func=cmd_exchange)

    p_ref = sub.add_parser("refresh", help="force a token refresh")
    add_env_tenant_args(p_ref)
    p_ref.set_defaults(func=cmd_refresh)

    p_logout = sub.add_parser("logout", help="forget cached tokens for an environment")
    add_env_tenant_args(p_logout)
    p_logout.set_defaults(func=cmd_logout)

    p_status = sub.add_parser("status", help="show cached-token status (no API call)")
    add_env_tenant_args(p_status)
    p_status.set_defaults(func=cmd_status)

    p_who = sub.add_parser("whoami", help="sanity check: list a few projects for the current tenant")
    add_env_tenant_args(p_who)
    p_who.set_defaults(func=cmd_whoami)


def cmd_login(args):
    cfg = config_mod.load_config(env=args.env, tenant_override=args.tenant)
    scopes = args.scopes.split(",") if args.scopes else None
    auth_mod.login(cfg, scopes=scopes, no_browser=args.no_browser)


def cmd_exchange(args):
    cfg = config_mod.load_config(env=args.env, tenant_override=args.tenant)
    source = args.url or args.code
    if not source:
        raise SystemExit("Pass --url '<redirected url>' or --code <code>")
    tokens_path = auth_mod.do_exchange(cfg, source)
    print(f"Authenticated. Tokens cached at {tokens_path}")


def cmd_refresh(args):
    cfg = config_mod.load_config(env=args.env, tenant_override=args.tenant)
    auth_mod.get_valid_access_token(cfg, force_refresh=True)
    print(f"Refreshed. Tokens cached at {config_mod.TOKENS_PATH}")


def cmd_logout(args):
    cfg = config_mod.load_config(env=args.env, tenant_override=args.tenant)
    had_token = auth_mod.logout(cfg["env"])
    print(f"Logged out of {cfg['env']!r}." if had_token else f"No cached tokens for {cfg['env']!r}.")


def cmd_status(args):
    cfg = config_mod.load_config(env=args.env, tenant_override=args.tenant)
    status = auth_mod.token_status(cfg["env"])
    print_json({"env": cfg["env"], "tenant": cfg["default_tenant_id"], **(status or {"authenticated": False})})


def cmd_whoami(args):
    client = get_client(args)
    resp = client.get("/tenants/{tenant_id}/projects", query={"limit": 5})
    print(f"HTTP {resp.status_code} — env={client.cfg['env']} tenant={client.cfg['default_tenant_id']}")
    try:
        print_json(resp.json())
    except ValueError:
        print(resp.text)
    if not resp.ok:
        raise SystemExit(1)
