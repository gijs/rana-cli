import json
import sys
import time

from .. import config as config_mod
from ..client import RanaClient
from ..output import print_response

COMPLETION_CACHE_DIR = config_mod.STATE_DIR / "completion_cache"
COMPLETION_CACHE_TTL = 60  # seconds
COMPLETION_TIMEOUT = 2  # seconds — completion must never hang the user's shell


def get_client(args) -> RanaClient:
    cfg = config_mod.load_config(env=getattr(args, "env", None), tenant_override=getattr(args, "tenant", None))
    return RanaClient(cfg)


def add_env_tenant_args(parser):
    parser.add_argument("--env", help="environment to use (default: $RANA_ENV or 'test')")
    parser.add_argument("--tenant", help="override the default tenant_id")


def add_pagination_args(parser, default_limit=50):
    parser.add_argument("--limit", type=int, default=default_limit)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--cursor", help="opaque pagination cursor from a previous response's 'next'")


def pagination_query(args):
    query = {}
    if getattr(args, "limit", None) is not None:
        query["limit"] = args.limit
    if getattr(args, "offset", None):
        query["offset"] = args.offset
    if getattr(args, "cursor", None):
        query["cursor"] = args.cursor
    return query


def add_body_args(parser, help_suffix="request body"):
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--json", dest="json_body", help=f"raw JSON {help_suffix}")
    group.add_argument("--file", dest="json_file", help=f"path to a JSON file with the {help_suffix}")


def resolve_body(args, extra: dict = None):
    """Combine --json/--file (if given) with any extra flag-derived fields.
    `extra` fields win only when the same key wasn't already set by --json/--file
    explicitly to a non-None value... in practice: extra is layered on top."""
    body = {}
    if getattr(args, "json_file", None):
        with open(args.json_file) as f:
            body = json.load(f)
    elif getattr(args, "json_body", None):
        body = json.loads(args.json_body)
    if extra:
        body.update({k: v for k, v in extra.items() if v is not None})
    return body


def emit(resp):
    print_response(resp)


def die(message: str):
    print(message, file=sys.stderr)
    sys.exit(1)


def id_completer(list_path):
    """Build an argcomplete `.completer` for a resource-id argument: calls
    `list_path` (e.g. "/tenants/{tenant_id}/projects") with a short timeout and
    a brief on-disk cache, and NEVER raises — a bad/unreachable API must fail
    silently (no completions) rather than hang or error out the user's shell.
    """

    def completer(prefix, parsed_args, **kwargs):
        try:
            cfg = config_mod.load_config(env=getattr(parsed_args, "env", None),
                                          tenant_override=getattr(parsed_args, "tenant", None))
            cache_key = list_path.strip("/").replace("/", "_") + f"_{cfg['env']}_{cfg['default_tenant_id']}"
            cache_file = COMPLETION_CACHE_DIR / f"{cache_key}.json"

            items = None
            if cache_file.exists() and time.time() - cache_file.stat().st_mtime < COMPLETION_CACHE_TTL:
                items = json.loads(cache_file.read_text()).get("items")

            if items is None:
                resp = RanaClient(cfg).get(list_path, query={"limit": 100}, timeout=COMPLETION_TIMEOUT)
                if not resp.ok:
                    return []
                items = resp.json().get("items", [])
                COMPLETION_CACHE_DIR.mkdir(parents=True, exist_ok=True)
                cache_file.write_text(json.dumps({"items": items}))

            return [item["id"] for item in items if item.get("id", "").startswith(prefix)]
        except (Exception, SystemExit):
            # Completion must never hang or error out the user's shell — a bad
            # env/tenant, unreachable API, or expired auth all just mean "no
            # completions" (note load_config raises SystemExit, not Exception,
            # on incomplete config).
            return []

    return completer


def paginate_all(client, path, query=None, page_size=100, max_pages=50):
    """Page through an offset/limit list endpoint ({total, items, limit, offset}
    envelope), yielding items across as many pages as `max_pages` allows.
    Prints a warning to stderr and stops on the first non-2xx response."""
    query = dict(query or {})
    offset = 0
    for _ in range(max_pages):
        query["limit"] = page_size
        query["offset"] = offset
        resp = client.get(path, query=query)
        if not resp.ok:
            print(f"warning: HTTP {resp.status_code} fetching {path}: {resp.text[:200]}", file=sys.stderr)
            return
        page = resp.json()
        items = page.get("items", [])
        if not items:
            return
        yield from items
        offset += page_size
        if offset >= page.get("total", offset):
            return
