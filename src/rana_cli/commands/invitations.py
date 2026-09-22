from ._shared import add_env_tenant_args, emit, get_client


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
