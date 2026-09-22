from ._shared import add_env_tenant_args, emit, get_client


def register(subparsers):
    p = subparsers.add_parser("users", help="manage tenant users")
    sub = p.add_subparsers(dest="users_command", required=True)

    p_list = sub.add_parser("list", help="list users in the tenant")
    add_env_tenant_args(p_list)
    p_list.set_defaults(func=cmd_list)

    p_get = sub.add_parser("get", help="show a user")
    add_env_tenant_args(p_get)
    p_get.add_argument("user_id")
    p_get.set_defaults(func=cmd_get)

    p_update = sub.add_parser("update", help="update a user's role/active status")
    add_env_tenant_args(p_update)
    p_update.add_argument("user_id")
    p_update.add_argument("--role", default=None)
    p_update.add_argument("--active", dest="active", action="store_true", default=None)
    p_update.add_argument("--inactive", dest="active", action="store_false")
    p_update.set_defaults(func=cmd_update)

    p_delete = sub.add_parser("delete", help="remove a user from the tenant")
    add_env_tenant_args(p_delete)
    p_delete.add_argument("user_id")
    p_delete.set_defaults(func=cmd_delete)


def cmd_list(args):
    client = get_client(args)
    emit(client.get("/tenants/{tenant_id}/users"))


def cmd_get(args):
    client = get_client(args)
    emit(client.get(f"/tenants/{{tenant_id}}/users/{args.user_id}"))


def cmd_update(args):
    client = get_client(args)
    body = {"role": args.role, "active": args.active}
    emit(client.patch(f"/tenants/{{tenant_id}}/users/{args.user_id}", json_body=body))


def cmd_delete(args):
    client = get_client(args)
    emit(client.delete(f"/tenants/{{tenant_id}}/users/{args.user_id}"))
