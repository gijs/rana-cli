from ._shared import (add_body_args, add_env_tenant_args, add_pagination_args,
                       emit, get_client, pagination_query, resolve_body)


def register(subparsers):
    p = subparsers.add_parser("projects", help="manage projects")
    sub = p.add_subparsers(dest="projects_command", required=True)

    p_list = sub.add_parser("list", help="list projects")
    add_env_tenant_args(p_list)
    add_pagination_args(p_list)
    p_list.add_argument("--order-by", choices=["code", "-code", "name", "-name",
                                                "created_at", "-created_at",
                                                "updated_at", "-updated_at"])
    p_list.set_defaults(func=cmd_list)

    p_get = sub.add_parser("get", help="show a project")
    add_env_tenant_args(p_get)
    p_get.add_argument("project_id")
    p_get.set_defaults(func=cmd_get)

    p_create = sub.add_parser("create", help="create a project")
    add_env_tenant_args(p_create)
    p_create.add_argument("--code", required=True, help="short project code (max 32 chars)")
    p_create.add_argument("--name", required=True, help="project name (max 80 chars)")
    p_create.add_argument("--description", default=None)
    p_create.add_argument("--client-name", dest="client_name", default=None)
    add_body_args(p_create, "extra fields (merged with the flags above)")
    p_create.set_defaults(func=cmd_create)

    p_update = sub.add_parser("update", help="update a project")
    add_env_tenant_args(p_update)
    p_update.add_argument("project_id")
    p_update.add_argument("--code", default=None)
    p_update.add_argument("--name", default=None)
    p_update.add_argument("--description", default=None)
    p_update.add_argument("--status")
    add_body_args(p_update, "extra fields (merged with the flags above)")
    p_update.set_defaults(func=cmd_update)

    p_delete = sub.add_parser("delete", help="delete a project")
    add_env_tenant_args(p_delete)
    p_delete.add_argument("project_id")
    p_delete.set_defaults(func=cmd_delete)

    p_users = sub.add_parser("users", help="list users in a project")
    add_env_tenant_args(p_users)
    p_users.add_argument("project_id")
    p_users.set_defaults(func=cmd_users)

    p_set_role = sub.add_parser("set-role", help="set/update a user's role in a project")
    add_env_tenant_args(p_set_role)
    p_set_role.add_argument("project_id")
    p_set_role.add_argument("user_id")
    p_set_role.add_argument("--role", required=True, help="e.g. owner, editor, viewer")
    p_set_role.set_defaults(func=cmd_set_role)

    p_remove_user = sub.add_parser("remove-user", help="remove a user from a project")
    add_env_tenant_args(p_remove_user)
    p_remove_user.add_argument("project_id")
    p_remove_user.add_argument("user_id")
    p_remove_user.set_defaults(func=cmd_remove_user)


def cmd_list(args):
    client = get_client(args)
    query = pagination_query(args)
    if args.order_by:
        query["order_by"] = args.order_by
    emit(client.get("/tenants/{tenant_id}/projects", query=query))


def cmd_get(args):
    client = get_client(args)
    emit(client.get(f"/tenants/{{tenant_id}}/projects/{args.project_id}"))


def cmd_create(args):
    client = get_client(args)
    body = resolve_body(args, {
        "code": args.code, "name": args.name,
        "description": args.description, "client_name": args.client_name,
    })
    emit(client.post("/tenants/{tenant_id}/projects", json_body=body))


def cmd_update(args):
    client = get_client(args)
    body = resolve_body(args, {
        "code": args.code, "name": args.name,
        "description": args.description, "status": args.status,
    })
    emit(client.patch(f"/tenants/{{tenant_id}}/projects/{args.project_id}", json_body=body))


def cmd_delete(args):
    client = get_client(args)
    emit(client.delete(f"/tenants/{{tenant_id}}/projects/{args.project_id}"))


def cmd_users(args):
    client = get_client(args)
    emit(client.get(f"/tenants/{{tenant_id}}/projects/{args.project_id}/users"))


def cmd_set_role(args):
    client = get_client(args)
    emit(client.put(
        f"/tenants/{{tenant_id}}/projects/{args.project_id}/users/{args.user_id}",
        json_body={"role": args.role},
    ))


def cmd_remove_user(args):
    client = get_client(args)
    emit(client.delete(f"/tenants/{{tenant_id}}/projects/{args.project_id}/users/{args.user_id}"))
