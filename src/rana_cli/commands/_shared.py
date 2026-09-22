import json
import sys

from .. import config as config_mod
from ..client import RanaClient
from ..output import print_response


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
