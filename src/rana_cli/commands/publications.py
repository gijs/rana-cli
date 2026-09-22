import json

from ._shared import (add_env_tenant_args, add_pagination_args, emit, get_client,
                       id_completer, pagination_query)

_publication_completer = id_completer("/tenants/{tenant_id}/publications")


def register(subparsers):
    p = subparsers.add_parser("publications", help="manage publications")
    sub = p.add_subparsers(dest="publications_command", required=True)

    p_list = sub.add_parser("list", help="list publications")
    add_env_tenant_args(p_list)
    add_pagination_args(p_list)
    p_list.set_defaults(func=cmd_list)

    p_get = sub.add_parser("get", help="show a publication")
    add_env_tenant_args(p_get)
    p_get.add_argument("publication_id").completer = _publication_completer
    p_get.set_defaults(func=cmd_get)

    p_create = sub.add_parser("create", help="create a publication")
    add_env_tenant_args(p_create)
    p_create.add_argument("--project-id", required=True, dest="project_id")
    p_create.add_argument("--name", required=True)
    p_create.add_argument("--description", default=None)
    p_create.set_defaults(func=cmd_create)

    p_update = sub.add_parser("update", help="update a publication")
    add_env_tenant_args(p_update)
    p_update.add_argument("publication_id").completer = _publication_completer
    p_update.add_argument("--name", default=None)
    p_update.add_argument("--description", default=None)
    p_update.add_argument("--published-version", type=int, default=None, dest="published_version")
    p_update.set_defaults(func=cmd_update)

    p_delete = sub.add_parser("delete", help="delete a publication")
    add_env_tenant_args(p_delete)
    p_delete.add_argument("publication_id").completer = _publication_completer
    p_delete.set_defaults(func=cmd_delete)

    p_versions = sub.add_parser("versions", help="list/show publication versions")
    versions_sub = p_versions.add_subparsers(dest="versions_command", required=True)

    p_v_list = versions_sub.add_parser("list")
    add_env_tenant_args(p_v_list)
    p_v_list.add_argument("publication_id").completer = _publication_completer
    p_v_list.set_defaults(func=cmd_versions_list)

    p_v_get = versions_sub.add_parser("get")
    add_env_tenant_args(p_v_get)
    p_v_get.add_argument("publication_id").completer = _publication_completer
    p_v_get.add_argument("version")
    p_v_get.set_defaults(func=cmd_versions_get)

    p_v_create = versions_sub.add_parser(
        "create",
        description="`--file` may be repeated: path[:name[:ref]] (name defaults to the path's "
                     "last segment, ref defaults to 'main'). Maps are a nested layer tree that "
                     "doesn't fit into flags — pass them with --maps-json/--maps-file, a JSON "
                     "list assigned to the 'maps' key (see the API docs for MapCreate's shape).",
    )
    add_env_tenant_args(p_v_create)
    p_v_create.add_argument("publication_id").completer = _publication_completer
    p_v_create.add_argument("--version", type=int, required=True)
    p_v_create.add_argument("--file", dest="files", action="append", default=[],
                             help="path[:name[:ref]], repeatable")
    maps_group = p_v_create.add_mutually_exclusive_group()
    maps_group.add_argument("--maps-json", help="raw JSON list for the 'maps' field")
    maps_group.add_argument("--maps-file", help="path to a JSON file containing the 'maps' list")
    p_v_create.set_defaults(func=cmd_versions_create)

    p_v_files = versions_sub.add_parser("files", help="list files in a publication version")
    add_env_tenant_args(p_v_files)
    p_v_files.add_argument("publication_id").completer = _publication_completer
    p_v_files.add_argument("version")
    p_v_files.set_defaults(func=cmd_versions_files)

    p_comments = sub.add_parser("comments", help="manage publication comments")
    comments_sub = p_comments.add_subparsers(dest="comments_command", required=True)

    p_c_list = comments_sub.add_parser("list")
    add_env_tenant_args(p_c_list)
    p_c_list.add_argument("publication_id").completer = _publication_completer
    resolved_group = p_c_list.add_mutually_exclusive_group()
    resolved_group.add_argument("--unresolved", action="store_true", help="only show unresolved threads")
    resolved_group.add_argument("--resolved", action="store_true", help="only show resolved threads")
    p_c_list.set_defaults(func=cmd_comments_list)

    p_c_get = comments_sub.add_parser("get")
    add_env_tenant_args(p_c_get)
    p_c_get.add_argument("publication_id").completer = _publication_completer
    p_c_get.add_argument("comment_id")
    p_c_get.set_defaults(func=cmd_comments_get)

    p_c_create = comments_sub.add_parser("create", help="create a comment (with its first message)")
    add_env_tenant_args(p_c_create)
    p_c_create.add_argument("publication_id").completer = _publication_completer
    p_c_create.add_argument("--body", required=True, help="the comment message body")
    p_c_create.add_argument("--lon", type=float, required=True)
    p_c_create.add_argument("--lat", type=float, required=True)
    p_c_create.add_argument("--map-id", type=int, default=None, dest="map_id")
    p_c_create.set_defaults(func=cmd_comments_create)

    p_c_delete = comments_sub.add_parser("delete")
    add_env_tenant_args(p_c_delete)
    p_c_delete.add_argument("publication_id").completer = _publication_completer
    p_c_delete.add_argument("comment_id")
    p_c_delete.set_defaults(func=cmd_comments_delete)

    for verb, help_text in [("add-message", "add a message to an existing comment thread"),
                             ("reply", "alias for add-message")]:
        p_c_msg = comments_sub.add_parser(verb, help=help_text)
        add_env_tenant_args(p_c_msg)
        p_c_msg.add_argument("publication_id").completer = _publication_completer
        p_c_msg.add_argument("comment_id")
        p_c_msg.add_argument("--body", required=True)
        p_c_msg.set_defaults(func=cmd_comments_add_message)

    p_c_resolve = comments_sub.add_parser("resolve")
    add_env_tenant_args(p_c_resolve)
    p_c_resolve.add_argument("publication_id").completer = _publication_completer
    p_c_resolve.add_argument("comment_id")
    p_c_resolve.set_defaults(func=cmd_comments_resolve)

    p_c_unresolve = comments_sub.add_parser("unresolve")
    add_env_tenant_args(p_c_unresolve)
    p_c_unresolve.add_argument("publication_id").completer = _publication_completer
    p_c_unresolve.add_argument("comment_id")
    p_c_unresolve.set_defaults(func=cmd_comments_unresolve)


def cmd_list(args):
    client = get_client(args)
    emit(client.get("/tenants/{tenant_id}/publications", query=pagination_query(args)))


def cmd_get(args):
    client = get_client(args)
    emit(client.get(f"/tenants/{{tenant_id}}/publications/{args.publication_id}"))


def cmd_create(args):
    client = get_client(args)
    body = {"project_id": args.project_id, "name": args.name, "description": args.description}
    emit(client.post("/tenants/{tenant_id}/publications", json_body=body))


def cmd_update(args):
    client = get_client(args)
    body = {"name": args.name, "description": args.description, "published_version": args.published_version}
    emit(client.patch(f"/tenants/{{tenant_id}}/publications/{args.publication_id}", json_body=body))


def cmd_delete(args):
    client = get_client(args)
    emit(client.delete(f"/tenants/{{tenant_id}}/publications/{args.publication_id}"))


def cmd_versions_list(args):
    client = get_client(args)
    emit(client.get(f"/tenants/{{tenant_id}}/publications/{args.publication_id}/versions"))


def cmd_versions_get(args):
    client = get_client(args)
    emit(client.get(f"/tenants/{{tenant_id}}/publications/{args.publication_id}/versions/{args.version}"))


def _parse_file_ref(spec):
    parts = spec.split(":")
    path = parts[0]
    name = parts[1] if len(parts) > 1 and parts[1] else None
    ref = parts[2] if len(parts) > 2 and parts[2] else "main"
    return {"name": name or path.rsplit("/", 1)[-1], "path": path, "ref": ref}


def cmd_versions_create(args):
    client = get_client(args)
    maps = []
    if args.maps_file:
        with open(args.maps_file) as f:
            maps = json.load(f)
    elif args.maps_json:
        maps = json.loads(args.maps_json)

    body = {
        "version": args.version,
        "files": [_parse_file_ref(spec) for spec in args.files],
        "maps": maps,
    }
    emit(client.post(f"/tenants/{{tenant_id}}/publications/{args.publication_id}/versions", json_body=body))


def cmd_versions_files(args):
    client = get_client(args)
    emit(client.get(f"/tenants/{{tenant_id}}/publications/{args.publication_id}/versions/{args.version}/files"))


def cmd_comments_list(args):
    client = get_client(args)
    query = {}
    if args.unresolved:
        query["resolved"] = "false"
    elif args.resolved:
        query["resolved"] = "true"
    emit(client.get(f"/tenants/{{tenant_id}}/publications/{args.publication_id}/comments", query=query))


def cmd_comments_get(args):
    client = get_client(args)
    emit(client.get(f"/tenants/{{tenant_id}}/publications/{args.publication_id}/comments/{args.comment_id}"))


def cmd_comments_create(args):
    client = get_client(args)
    body = {
        "messages": [{"body": args.body}],
        "location": {"type": "Point", "coordinates": [args.lon, args.lat]},
        "map_id": args.map_id,
    }
    emit(client.post(f"/tenants/{{tenant_id}}/publications/{args.publication_id}/comments", json_body=body))


def cmd_comments_delete(args):
    client = get_client(args)
    emit(client.delete(f"/tenants/{{tenant_id}}/publications/{args.publication_id}/comments/{args.comment_id}"))


def cmd_comments_add_message(args):
    client = get_client(args)
    emit(client.post(
        f"/tenants/{{tenant_id}}/publications/{args.publication_id}/comments/{args.comment_id}/messages",
        json_body={"body": args.body},
    ))


def cmd_comments_resolve(args):
    client = get_client(args)
    emit(client.post(f"/tenants/{{tenant_id}}/publications/{args.publication_id}/comments/{args.comment_id}/resolve"))


def cmd_comments_unresolve(args):
    client = get_client(args)
    emit(client.post(f"/tenants/{{tenant_id}}/publications/{args.publication_id}/comments/{args.comment_id}/unresolve"))
