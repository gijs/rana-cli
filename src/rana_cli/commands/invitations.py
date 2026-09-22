import csv

from ..output import print_table
from ._shared import add_env_tenant_args, die, emit, get_client


def register(subparsers):
    p = subparsers.add_parser("invitations", help="manage tenant/project invitations")
    sub = p.add_subparsers(dest="invitations_command", required=True)

    p_list = sub.add_parser("list", help="list invitations")
    add_env_tenant_args(p_list)
    p_list.set_defaults(func=cmd_list)

    p_create = sub.add_parser("create", help="invite a user by email")
    add_env_tenant_args(p_create)
    p_create.add_argument("--email", required=True)
    p_create.add_argument("--tenant-role", default="guest", dest="tenant_role")
    p_create.add_argument("--project", default=None, help="project id to also grant a project role in")
    p_create.add_argument("--project-role", default=None, dest="project_role")
    p_create.set_defaults(func=cmd_create)

    p_check = sub.add_parser("check", help="check whether an invitation is still valid")
    add_env_tenant_args(p_check)
    p_check.add_argument("invitation_id")
    p_check.set_defaults(func=cmd_check)

    p_accept = sub.add_parser("accept", help="accept an invitation")
    add_env_tenant_args(p_accept)
    p_accept.add_argument("invitation_id")
    p_accept.set_defaults(func=cmd_accept)

    p_revoke = sub.add_parser("revoke", help="revoke an invitation")
    add_env_tenant_args(p_revoke)
    p_revoke.add_argument("invitation_id")
    p_revoke.set_defaults(func=cmd_revoke)

    p_resend = sub.add_parser("send-email", help="(re)send the invitation email")
    add_env_tenant_args(p_resend)
    p_resend.add_argument("invitation_id")
    p_resend.set_defaults(func=cmd_send_email)

    p_bulk = sub.add_parser(
        "bulk-create", help="invite many users at once from a CSV",
        description="CSV columns: email (required), tenant_role (default 'guest'), "
                     "project, project_role (both optional, same meaning as `create`'s flags). "
                     "There's no bulk endpoint server-side, so this sends one request per row "
                     "and reports per-row success/failure.",
    )
    add_env_tenant_args(p_bulk)
    p_bulk.add_argument("csv_path")
    p_bulk.add_argument("--dry-run", action="store_true", help="validate and print the plan, send nothing")
    p_bulk.set_defaults(func=cmd_bulk_create)


def cmd_list(args):
    client = get_client(args)
    emit(client.get("/tenants/{tenant_id}/invitations"))


def cmd_create(args):
    client = get_client(args)
    body = {
        "email": args.email, "tenant_role": args.tenant_role,
        "project": args.project, "project_role": args.project_role,
    }
    emit(client.post("/tenants/{tenant_id}/invitations", json_body=body))


def cmd_check(args):
    client = get_client(args)
    emit(client.get(f"/tenants/{{tenant_id}}/invitations/{args.invitation_id}/check"))


def cmd_accept(args):
    client = get_client(args)
    emit(client.put(f"/tenants/{{tenant_id}}/invitations/{args.invitation_id}/accept"))


def cmd_revoke(args):
    client = get_client(args)
    emit(client.post(f"/tenants/{{tenant_id}}/invitations/{args.invitation_id}/revoke"))


def cmd_send_email(args):
    client = get_client(args)
    emit(client.post(f"/tenants/{{tenant_id}}/invitations/{args.invitation_id}/send-email"))


def _read_invitation_rows(csv_path):
    try:
        with open(csv_path, newline="") as f:
            rows = list(csv.DictReader(f))
    except OSError as exc:
        die(f"Could not read {csv_path}: {exc}")

    errors = []
    for i, row in enumerate(rows, start=2):  # row 1 is the header
        if not row.get("email", "").strip():
            errors.append(f"line {i}: missing email")
    if errors:
        die("Invalid CSV:\n" + "\n".join(errors))
    return rows


def cmd_bulk_create(args):
    rows = _read_invitation_rows(args.csv_path)
    plan = [{
        "email": row["email"].strip(),
        "tenant_role": row.get("tenant_role", "").strip() or "guest",
        "project": row.get("project", "").strip() or None,
        "project_role": row.get("project_role", "").strip() or None,
    } for row in rows]

    if args.dry_run:
        print_table(plan, [("email", "email"), ("tenant_role", "tenant_role"),
                            ("project", "project"), ("project_role", "project_role")])
        return

    client = get_client(args)
    results = []
    for body in plan:
        resp = client.post("/tenants/{tenant_id}/invitations", json_body=body)
        results.append({
            "email": body["email"], "ok": "yes" if resp.ok else "no",
            "detail": "" if resp.ok else f"HTTP {resp.status_code}: {resp.text[:200]}",
        })

    print_table(results, [("email", "email"), ("ok", "ok"), ("detail", "detail")])
    if any(r["ok"] == "no" for r in results):
        raise SystemExit(1)
