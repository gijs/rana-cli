"""Project and dataset file operations.

Every subcommand takes exactly one of --project/--dataset to pick which
resource's file tree to operate on (the two APIs are near-identical, but not
every operation exists on both — e.g. `download` is project-only).
"""
import hashlib
import os
import sys

import requests

from ..output import print_response
from ._shared import add_env_tenant_args, die, emit, get_client, id_completer

_project_completer = id_completer("/tenants/{tenant_id}/projects")
_dataset_completer = id_completer("/tenants/{tenant_id}/datasets")


class UploadFailed(Exception):
    pass


def _add_scope_args(parser):
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--project", dest="project_id", help="project id").completer = _project_completer
    scope.add_argument("--dataset", dest="dataset_id", help="dataset id").completer = _dataset_completer


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

    p_upt = sub.add_parser("upload-tree", help="upload every file under a local directory")
    add_env_tenant_args(p_upt)
    _add_scope_args(p_upt)
    p_upt.add_argument("local_dir")
    p_upt.add_argument("--dest", default="", help="destination root path in the file tree")
    p_upt.add_argument("--branch", default="main")
    p_upt.add_argument("--description", default="")
    p_upt.add_argument("--data-type", default=None, dest="data_type")
    p_upt.add_argument("--continue-on-error", action="store_true",
                        help="keep going after a failed file instead of stopping")
    p_upt.set_defaults(func=cmd_upload_tree)

    p_sync = sub.add_parser("sync", help="mirror a local directory to a project/dataset's file tree")
    add_env_tenant_args(p_sync)
    _add_scope_args(p_sync)
    p_sync.add_argument("local_dir")
    p_sync.add_argument("--dest", default="", help="remote root path to sync to")
    p_sync.add_argument("--branch", default="main")
    p_sync.add_argument("--delete", action="store_true",
                         help="also delete remote files that have no local counterpart")
    p_sync.add_argument("--dry-run", action="store_true",
                         help="show what would change without changing anything")
    p_sync.add_argument("-y", "--yes", action="store_true", help="don't prompt before deleting")
    p_sync.set_defaults(func=cmd_sync)


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


def _upload_one(client, scope, resource_id, branch, local_path, dest_path, data_type, description, message):
    """Upload one local file to `dest_path` in the remote tree. Raises UploadFailed on any failure."""
    base = f"/tenants/{{tenant_id}}/{scope}/{resource_id}/files/upload"

    start_resp = client.post(base, query={"path": dest_path, "branch": branch})
    if not start_resp.ok:
        raise UploadFailed(f"HTTP {start_resp.status_code} starting upload: {start_resp.text}")
    upload = start_resp.json()

    try:
        with open(local_path, "rb") as f:
            file_bytes = f.read()
    except OSError as exc:
        raise UploadFailed(f"could not read {local_path}: {exc}")

    for put_url in upload.get("urls", []):
        put_resp = requests.put(put_url, data=file_bytes, timeout=300)
        if not put_resp.ok:
            raise UploadFailed(f"PUT to storage failed: HTTP {put_resp.status_code}\n{put_resp.text}")

    complete_body = {
        "id": upload["id"],
        "branch": upload["branch"],
        "transaction_id": upload["transaction_id"],
        "address": upload["address"],
        "descriptor": {"data_type": data_type, "description": description},
        "message": message,
    }
    complete_resp = client.put(base, json_body=complete_body)
    if not complete_resp.ok:
        raise UploadFailed(f"HTTP {complete_resp.status_code} completing upload: {complete_resp.text}")
    return complete_resp


def cmd_upload(args):
    client = get_client(args)
    scope, resource_id = _scope(args)
    try:
        resp = _upload_one(client, scope, resource_id, args.branch, args.local_path, args.dest,
                            args.data_type, args.description, args.message)
    except UploadFailed as exc:
        die(str(exc))
    else:
        emit(resp)


def _iter_local_files(local_dir):
    """Yield (absolute_path, posix_relative_path) for every file under local_dir."""
    for root, _dirs, filenames in os.walk(local_dir):
        for name in filenames:
            abs_path = os.path.join(root, name)
            rel_path = os.path.relpath(abs_path, local_dir).replace(os.sep, "/")
            yield abs_path, rel_path


def _remote_path(dest_root, rel_path):
    return "/".join(part for part in (dest_root.strip("/"), rel_path) if part)


def cmd_upload_tree(args):
    client = get_client(args)
    scope, resource_id = _scope(args)
    if not os.path.isdir(args.local_dir):
        die(f"{args.local_dir} is not a directory")

    uploaded, failed = 0, 0
    for abs_path, rel_path in _iter_local_files(args.local_dir):
        dest_path = _remote_path(args.dest, rel_path)
        try:
            _upload_one(client, scope, resource_id, args.branch, abs_path, dest_path,
                        args.data_type, args.description, None)
        except UploadFailed as exc:
            failed += 1
            print(f"failed: {dest_path}: {exc}", file=sys.stderr)
            if not args.continue_on_error:
                die(f"Stopping after failure ({uploaded} uploaded, {failed} failed so far). "
                    f"Pass --continue-on-error to keep going after failures.")
        else:
            uploaded += 1
            print(f"uploaded: {dest_path}")

    print(f"{uploaded} uploaded, {failed} failed")
    if failed:
        sys.exit(1)


def _list_remote_tree(client, scope, resource_id, ref, root):
    """Recursively list every file under `root`. Returns {path_relative_to_root: FileRead dict}."""
    base = f"/tenants/{{tenant_id}}/{scope}/{resource_id}/files/ls"
    root_prefix = root.strip("/")
    files = {}
    stack = [root]
    while stack:
        path = stack.pop()
        cursor = None
        while True:
            query = {"path": path, "ref": ref, "limit": 1000}
            if cursor:
                query["cursor"] = cursor
            resp = client.get(base, query=query)
            if not resp.ok:
                die(f"HTTP {resp.status_code} listing {path!r}: {resp.text}")
            page = resp.json()
            for item in page.get("items", []):
                item_id = item["id"]
                if item.get("type") == "directory":
                    stack.append(item_id)
                    continue
                rel = item_id.strip("/")
                if root_prefix and rel.startswith(root_prefix):
                    rel = rel[len(root_prefix):].lstrip("/")
                files[rel] = item
            cursor = page.get("next")
            if not cursor:
                break
    return files


def _local_md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _needs_upload(remote_file, local_abs_path):
    etag = (remote_file.get("etag") or "").strip('"')
    if "-" in etag:
        # ETag with a `-<part-count>` suffix means a multipart upload; it isn't a
        # plain MD5 of the file body, so fall back to a size-only comparison.
        return remote_file.get("size") != os.path.getsize(local_abs_path)
    return etag != _local_md5(local_abs_path)


def cmd_sync(args):
    client = get_client(args)
    scope, resource_id = _scope(args)
    if not os.path.isdir(args.local_dir):
        die(f"{args.local_dir} is not a directory")

    remote = _list_remote_tree(client, scope, resource_id, args.branch, args.dest)
    local = dict((rel, abs_path) for abs_path, rel in _iter_local_files(args.local_dir))

    to_upload = [rel for rel in local if rel not in remote or _needs_upload(remote[rel], local[rel])]
    remote_only = sorted(set(remote) - set(local))

    print(f"{len(to_upload)} to upload, {len(local) - len(to_upload)} unchanged, "
          f"{len(remote_only)} remote-only" + (f" (deleting {len(remote_only)})" if args.delete else ""))

    if args.dry_run:
        for rel in to_upload:
            print(f"  upload: {rel}")
        for rel in remote_only:
            print(f"  remote-only{' (would delete)' if args.delete else ''}: {rel}")
        return

    failed = 0
    for rel in to_upload:
        dest_path = _remote_path(args.dest, rel)
        try:
            _upload_one(client, scope, resource_id, args.branch, local[rel], dest_path, None, "", None)
        except UploadFailed as exc:
            failed += 1
            print(f"failed: {rel}: {exc}", file=sys.stderr)
        else:
            print(f"uploaded: {rel}")

    if args.delete and remote_only:
        if not args.yes:
            answer = input(f"Delete {len(remote_only)} remote file(s)? [y/N] ")
            if answer.strip().lower() != "y":
                print("Skipping delete.")
                if failed:
                    sys.exit(1)
                return
        delete_base = f"/tenants/{{tenant_id}}/{scope}/{resource_id}/files/delete"
        for rel in remote_only:
            resp = client.delete(delete_base, query={"path": _remote_path(args.dest, rel), "branch": args.branch})
            if not resp.ok:
                failed += 1
                print(f"failed to delete {rel}: HTTP {resp.status_code}", file=sys.stderr)
            else:
                print(f"deleted: {rel}")

    if failed:
        sys.exit(1)
