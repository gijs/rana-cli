from ._shared import add_env_tenant_args, emit, get_client


def register(subparsers):
    p = subparsers.add_parser("tenants", help="list/inspect tenants")
    sub = p.add_subparsers(dest="tenants_command", required=True)

    p_list = sub.add_parser("list", help="list tenants available to the current user")
    add_env_tenant_args(p_list)
    p_list.set_defaults(func=cmd_list)

    p_get = sub.add_parser("get", help="show a tenant")
    add_env_tenant_args(p_get)
    p_get.add_argument("tenant_id_arg", metavar="tenant_id")
    p_get.set_defaults(func=cmd_get)


def cmd_list(args):
    client = get_client(args)
    emit(client.get("/tenants"))


def cmd_get(args):
    client = get_client(args)
    emit(client.get(f"/tenants/{args.tenant_id_arg}"))
