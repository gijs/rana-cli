"""Project and dataset file operations.

Every subcommand takes exactly one of --project/--dataset to pick which
resource's file tree to operate on (the two APIs are near-identical, but not
every operation exists on both — e.g. `download` is project-only).
"""
import requests

from ..output import print_response
from ._shared import add_env_tenant_args, die, emit, get_client


def _add_scope_args(parser):
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--project", dest="project_id", help="project id")
    scope.add_argument("--dataset", dest="dataset_id", help="dataset id")


def _scope(args, allow_dataset=True):
    if args.project_id:
        return "projects", args.project_id
    if not allow_dataset:
        die("--dataset is not supported for this operation; use --project.")
    return "datasets", args.dataset_id


def register(subparsers):
    p = subparsers.add_parser("files", help="browse/manage files in a project or dataset")
    sub = p.add_subparsers(dest="files_command", required=True)

    p_ls = sub.add_parser("ls", help="list files in a directory")
    add_env_tenant_args(p_ls)
    _add_scope_args(p_ls)
    p_ls.add_argument("--path", default="", help="directory path (default: root)")
    p_ls.add_argument("--ref", default="main")
    p_ls.add_argument("--limit", type=int, default=100)
    p_ls.add_argument("--cursor")
    p_ls.set_defaults(func=cmd_ls)

    p_stat = sub.add_parser("stat", help="show details of one file")
    add_env_tenant_args(p_stat)
    _add_scope_args(p_stat)
    p_stat.add_argument("path")
    p_stat.add_argument("--ref", default="main")
    p_stat.set_defaults(func=cmd_stat)

    p_hist = sub.add_parser("history", help="show file/directory history")
    add_env_tenant_args(p_hist)
    _add_scope_args(p_hist)
    p_hist.add_argument("--path", default="")
    p_hist.add_argument("--ref", default="main")
    p_hist.set_defaults(func=cmd_history)

    p_dl = sub.add_parser("download", help="get a download URL for a file (project only)")
    add_env_tenant_args(p_dl)
    _add_scope_args(p_dl)
    p_dl.add_argument("path")
    p_dl.add_argument("--ref", default="main")
    p_dl.add_argument("--save-to", help="if given, also download the file to this local path")
    p_dl.set_defaults(func=cmd_download)

    p_rm = sub.add_parser("rm", help="delete a file")
    add_env_tenant_args(p_rm)
    _add_scope_args(p_rm)
    p_rm.add_argument("path")
    p_rm.add_argument("--branch", default="main")
    p_rm.set_defaults(func=cmd_rm)

    p_mv = sub.add_parser("mv", help="move/rename a file")
    add_env_tenant_args(p_mv)
    _add_scope_args(p_mv)
    p_mv.add_argument("source_path")
    p_mv.add_argument("destination_path")
    p_mv.add_argument("--branch", default="main")
    p_mv.set_defaults(func=cmd_mv)

    p_cp = sub.add_parser("cp", help="copy a file")
    add_env_tenant_args(p_cp)
    _add_scope_args(p_cp)
    p_cp.add_argument("source_path")
    p_cp.add_argument("destination_path")
    p_cp.add_argument("--src-ref", default="main", dest="src_ref")
    p_cp.add_argument("--branch", default="main")
    p_cp.set_defaults(func=cmd_cp)

    p_up = sub.add_parser("upload", help="upload a local file")
    add_env_tenant_args(p_up)
    _add_scope_args(p_up)
    p_up.add_argument("local_path")
    p_up.add_argument("--dest", required=True, help="destination path in the file tree")
    p_up.add_argument("--branch", default="main")
    p_up.add_argument("--description", default="")
    p_up.add_argument("--data-type", default=None, dest="data_type")
    p_up.add_argument("--message", default=None)
    p_up.set_defaults(func=cmd_upload)


def cmd_ls(args):
    client = get_client(args)
    scope, resource_id = _scope(args)
    query = {"path": args.path, "ref": args.ref, "limit": args.limit}
    if args.cursor:
        query["cursor"] = args.cursor
    emit(client.get(f"/tenants/{{tenant_id}}/{scope}/{resource_id}/files/ls", query=query))


def cmd_stat(args):
    client = get_client(args)
    scope, resource_id = _scope(args)
    emit(client.get(f"/tenants/{{tenant_id}}/{scope}/{resource_id}/files/stat",
                     query={"path": args.path, "ref": args.ref}))


def cmd_history(args):
    client = get_client(args)
    scope, resource_id = _scope(args)
    emit(client.get(f"/tenants/{{tenant_id}}/{scope}/{resource_id}/files/history",
                     query={"path": args.path, "ref": args.ref}))


def cmd_download(args):
    client = get_client(args)
    scope, resource_id = _scope(args, allow_dataset=False)
    resp = client.get(f"/tenants/{{tenant_id}}/{scope}/{resource_id}/files/download",
                       query={"path": args.path, "ref": args.ref})
    if not resp.ok:
        print_response(resp)
        return
    data = resp.json()
    if not args.save_to:
        emit(resp)
        return
    url = data["url"]
    with requests.get(url, stream=True, timeout=120) as dl:
        dl.raise_for_status()
        with open(args.save_to, "wb") as f:
            for chunk in dl.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)
    print(f"Saved to {args.save_to}")


def cmd_rm(args):
    client = get_client(args)
    scope, resource_id = _scope(args)
    emit(client.delete(f"/tenants/{{tenant_id}}/{scope}/{resource_id}/files/delete",
                        query={"path": args.path, "branch": args.branch}))


def cmd_mv(args):
    client = get_client(args)
    scope, resource_id = _scope(args)
    emit(client.post(f"/tenants/{{tenant_id}}/{scope}/{resource_id}/files/move",
                      query={"source_path": args.source_path,
                             "destination_path": args.destination_path,
                             "branch": args.branch}))


def cmd_cp(args):
    client = get_client(args)
    scope, resource_id = _scope(args)
    emit(client.post(f"/tenants/{{tenant_id}}/{scope}/{resource_id}/files/copy",
                      query={"source_path": args.source_path,
                             "destination_path": args.destination_path,
                             "src_ref": args.src_ref, "branch": args.branch}))


def cmd_upload(args):
    client = get_client(args)
    scope, resource_id = _scope(args)
    base = f"/tenants/{{tenant_id}}/{scope}/{resource_id}/files/upload"

    start_resp = client.post(base, query={"path": args.dest, "branch": args.branch})
    if not start_resp.ok:
        print_response(start_resp)
        return
    upload = start_resp.json()

    try:
        with open(args.local_path, "rb") as f:
            file_bytes = f.read()
    except OSError as exc:
        die(f"Could not read {args.local_path}: {exc}")

    for put_url in upload.get("urls", []):
        put_resp = requests.put(put_url, data=file_bytes, timeout=300)
        if not put_resp.ok:
            die(f"Upload PUT to storage failed: HTTP {put_resp.status_code}\n{put_resp.text}")

    complete_body = {
        "id": upload["id"],
        "branch": upload["branch"],
        "transaction_id": upload["transaction_id"],
        "address": upload["address"],
        "descriptor": {"data_type": args.data_type, "description": args.description},
        "message": args.message,
    }
    emit(client.put(base, json_body=complete_body))
