import sys

from ..picker import pick
from ._shared import (add_body_args, add_env_tenant_args, add_pagination_args, emit,
                       get_client, id_completer, paginate_all, pagination_query, resolve_body)

_dataset_completer = id_completer("/tenants/{tenant_id}/datasets")


def register(subparsers):
    p = subparsers.add_parser("datasets", help="manage datasets")
    sub = p.add_subparsers(dest="datasets_command", required=True)

    p_list = sub.add_parser("list", help="search/list datasets")
    add_env_tenant_args(p_list)
    add_pagination_args(p_list)
    p_list.add_argument("-q", "--query", dest="q", help="full-text search query")
    p_list.set_defaults(func=cmd_list)

    p_get = sub.add_parser("get", help="show a dataset (metadata document)")
    add_env_tenant_args(p_get)
    p_get.add_argument("dataset_id").completer = _dataset_completer
    p_get.set_defaults(func=cmd_get)

    p_create = sub.add_parser(
        "create", help="create a dataset",
        description="Dataset metadata follows the ISO19115 schema, which is too large to "
                     "flatten into flags — pass it with --json/--file.",
    )
    add_env_tenant_args(p_create)
    add_body_args(p_create, "ISO19115Dataset body")
    p_create.set_defaults(func=cmd_create)

    p_update = sub.add_parser("update", help="update a dataset's metadata document")
    add_env_tenant_args(p_update)
    p_update.add_argument("dataset_id").completer = _dataset_completer
    add_body_args(p_update, "partial ISO19115Dataset body")
    p_update.set_defaults(func=cmd_update)

    p_delete = sub.add_parser("delete", help="delete a dataset")
    add_env_tenant_args(p_delete)
    p_delete.add_argument("dataset_id").completer = _dataset_completer
    p_delete.set_defaults(func=cmd_delete)

    p_links = sub.add_parser("data-links", help="show dataset data links")
    add_env_tenant_args(p_links)
    p_links.add_argument("dataset_id").completer = _dataset_completer
    p_links.set_defaults(func=cmd_data_links)

    p_wms = sub.add_parser("wms-links", help="show dataset WMS links")
    add_env_tenant_args(p_wms)
    p_wms.add_argument("dataset_id").completer = _dataset_completer
    p_wms.set_defaults(func=cmd_wms_links)

    p_versions = sub.add_parser("versions", help="manage dataset versions")
    versions_sub = p_versions.add_subparsers(dest="versions_command", required=True)

    p_v_list = versions_sub.add_parser("list", help="list versions of a dataset")
    add_env_tenant_args(p_v_list)
    p_v_list.add_argument("dataset_id").completer = _dataset_completer
    p_v_list.set_defaults(func=cmd_versions_list)

    p_v_get = versions_sub.add_parser("get", help="show a dataset version")
    add_env_tenant_args(p_v_get)
    p_v_get.add_argument("dataset_id").completer = _dataset_completer
    p_v_get.add_argument("version_number", type=int)
    p_v_get.set_defaults(func=cmd_versions_get)

    p_v_create = versions_sub.add_parser("create", help="create a new dataset version")
    add_env_tenant_args(p_v_create)
    p_v_create.add_argument("dataset_id").completer = _dataset_completer
    p_v_create.add_argument("--store-ref", required=True, dest="store_ref")
    p_v_create.add_argument("--description", default=None)
    p_v_create.set_defaults(func=cmd_versions_create)

    p_v_delete = versions_sub.add_parser("delete", help="delete a dataset version")
    add_env_tenant_args(p_v_delete)
    p_v_delete.add_argument("dataset_id").completer = _dataset_completer
    p_v_delete.add_argument("version_number", type=int)
    p_v_delete.set_defaults(func=cmd_versions_delete)

    p_pick = sub.add_parser(
        "pick", help="interactively fuzzy-pick a dataset, printing its id",
        description="Launches a Textual fuzzy-filter picker and prints only the "
                     "chosen dataset id to stdout, for use like: "
                     "--dataset $(rana datasets pick)",
    )
    add_env_tenant_args(p_pick)
    p_pick.add_argument("-q", "--query", dest="q", default=None,
                         help="server-side full-text search to narrow the list before picking")
    p_pick.set_defaults(func=cmd_pick)


def cmd_list(args):
    client = get_client(args)
    query = pagination_query(args)
    if args.q:
        query["q"] = args.q
    emit(client.get("/tenants/{tenant_id}/datasets", query=query))


def cmd_get(args):
    client = get_client(args)
    emit(client.get(f"/tenants/{{tenant_id}}/datasets/{args.dataset_id}/document"))


def cmd_create(args):
    client = get_client(args)
    body = resolve_body(args)
    emit(client.post("/tenants/{tenant_id}/datasets", json_body=body))


def cmd_update(args):
    client = get_client(args)
    body = resolve_body(args)
    emit(client.patch(f"/tenants/{{tenant_id}}/datasets/{args.dataset_id}/document", json_body=body))


def cmd_delete(args):
    client = get_client(args)
    emit(client.delete(f"/tenants/{{tenant_id}}/datasets/{args.dataset_id}"))


def cmd_data_links(args):
    client = get_client(args)
    emit(client.get(f"/tenants/{{tenant_id}}/datasets/{args.dataset_id}/data-links"))


def cmd_wms_links(args):
    client = get_client(args)
    emit(client.get(f"/tenants/{{tenant_id}}/datasets/{args.dataset_id}/wms-links"))


def cmd_versions_list(args):
    client = get_client(args)
    emit(client.get(f"/tenants/{{tenant_id}}/datasets/{args.dataset_id}/versions"))


def cmd_versions_get(args):
    client = get_client(args)
    emit(client.get(f"/tenants/{{tenant_id}}/datasets/{args.dataset_id}/versions/{args.version_number}"))


def cmd_versions_create(args):
    client = get_client(args)
    body = {"store_ref": args.store_ref, "description": args.description}
    emit(client.post(f"/tenants/{{tenant_id}}/datasets/{args.dataset_id}/versions", json_body=body))


def cmd_versions_delete(args):
    client = get_client(args)
    emit(client.delete(f"/tenants/{{tenant_id}}/datasets/{args.dataset_id}/versions/{args.version_number}"))


def cmd_pick(args):
    client = get_client(args)
    query = {"q": args.q} if args.q else None
    items = list(paginate_all(client, "/tenants/{tenant_id}/datasets", query))
    chosen = pick(items, label_fn=lambda d: d.get("title") or d.get("identifier") or d.get("id", ""),
                  id_fn=lambda d: d.get("id"))
    if chosen is None:
        sys.exit(1)
    print(chosen)
