from ._shared import add_env_tenant_args, emit, get_client


def register(subparsers):
    p = subparsers.add_parser(
        "call", help="make a raw authenticated API call to any endpoint (escape hatch)",
        description="For endpoints not covered by a dedicated subcommand. "
                     "See README.md's endpoint reference, or the live docs at "
                     "<api_base_url>/docs for exact paths and bodies.",
    )
    add_env_tenant_args(p)
    p.add_argument("method", choices=["GET", "POST", "PUT", "PATCH", "DELETE",
                                       "get", "post", "put", "patch", "delete"])
    p.add_argument("path", help="e.g. /tenants/{tenant_id}/datasets (any other {placeholder} must "
                                 "already be filled in)")
    p.add_argument("--query", action="append", default=[], help="key=value, repeatable")
    p.add_argument("--json", dest="json_body", help="raw JSON request body")
    p.set_defaults(func=cmd_call)


def cmd_call(args):
    import json as json_mod

    query = dict(kv.split("=", 1) for kv in args.query) if args.query else None
    body = json_mod.loads(args.json_body) if args.json_body else None
    client = get_client(args)
    resp = client.request(args.method, args.path, query=query, json_body=body)
    emit(resp)
